#!/usr/bin/env python3
"""Run holdout judges on selected EXP-01 prompts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from core.audit import aggregate_audits, run_single_audit
from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from core.llm_client import ProviderError, provider_available
from core.models import DEFAULT_HOLDOUT_JUDGES, parse_model_ref
from core.prompts import ConditionPrompt


def parse_refs(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def filter_available(refs: list[str], strict: bool) -> list[str]:
    available = []
    missing = []
    for ref in refs:
        provider, _ = parse_model_ref(ref)
        if provider_available(provider):
            available.append(ref)
        else:
            missing.append(ref)
    if missing and strict:
        raise SystemExit(f"Missing API keys for judges: {', '.join(missing)}")
    if missing:
        print(f"Skipping judges with missing keys: {', '.join(missing)}", file=sys.stderr)
    return available


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", required=True, help="Path to selected_prompts.json.")
    parser.add_argument("--out", default=None)
    parser.add_argument("--holdout-judges", default=",".join(DEFAULT_HOLDOUT_JUDGES))
    parser.add_argument("--strict-keys", action="store_true")
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-01/holdout_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    judges = filter_available(parse_refs(args.holdout_judges), args.strict_keys)
    if not judges:
        raise SystemExit("No holdout judges available")

    selected = json.loads(Path(args.selected).read_text(encoding="utf-8"))
    all_audits = []
    aggregates = []
    frozen = {}

    write_json(
        out_dir / "config.json",
        {
            "experiment": "EXP-01-selected-holdout",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "selected": args.selected,
            "holdout_judges": judges,
        },
    )

    for condition_name, item in selected.items():
        condition = ConditionPrompt(
            condition=condition_name,
            target_label=item["target_label"],
            text=item["prompt"],
            is_primary_emotional=item["is_primary_emotional"],
        )
        audits = []
        for judge in judges:
            try:
                audits.append(run_single_audit(condition, item["prompt"], judge, 0))
            except ProviderError as exc:
                print(f"[warn] {condition_name} judge {judge} failed: {exc}", file=sys.stderr)
        if not audits:
            raise SystemExit(f"No successful holdout calls for {condition_name}")
        aggregate = aggregate_audits(condition, item["prompt"], 0, audits)
        all_audits.extend(asdict(row) for row in audits)
        aggregates.append(asdict(aggregate))
        frozen[condition_name] = {
            **item,
            "holdout_passed": aggregate.passed,
            "holdout_summary": asdict(aggregate),
        }
        print(
            f"{condition_name}: holdout_passed={aggregate.passed} "
            f"cap={aggregate.mean_capability_assertion} rel={aggregate.mean_reliability_assertion} "
            f"task={aggregate.mean_task_directive_contamination}"
        )

    primary_failures = [
        name
        for name, item in frozen.items()
        if item["is_primary_emotional"] and not item["holdout_passed"]
    ]

    write_jsonl(out_dir / "judge_outputs.jsonl", all_audits)
    write_jsonl(out_dir / "holdout_aggregates.jsonl", aggregates)
    write_json(out_dir / "frozen_prompts.json", frozen)
    write_json(
        out_dir / "metrics.json",
        {
            "primary_failures": primary_failures,
            "all_primary_passed": not primary_failures,
            "output_dir": str(out_dir),
        },
    )

    if primary_failures:
        print(f"primary failures: {', '.join(primary_failures)}", file=sys.stderr)
        return 2
    print(f"holdout complete: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
