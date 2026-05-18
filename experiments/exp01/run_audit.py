#!/usr/bin/env python3
"""Run EXP-01 multi-judge prompt audit with optional polishing."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from core.audit import aggregate_audits, rewrite_prompt, run_single_audit
from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from core.llm_client import ProviderError, provider_available
from core.models import DEFAULT_DEV_JUDGES, DEFAULT_HOLDOUT_JUDGES, DEFAULT_REWRITER, parse_model_ref
from core.prompts import PROMPTS


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


def run_audit_round(condition, prompt_text: str, judges: list[str], round_index: int):
    rows = []
    for judge in judges:
        try:
            rows.append(run_single_audit(condition, prompt_text, judge, round_index))
        except ProviderError as exc:
            print(f"[warn] {condition.condition} judge {judge} failed: {exc}", file=sys.stderr)
    if not rows:
        raise SystemExit(f"No successful judge calls for {condition.condition}")
    aggregate = aggregate_audits(condition, prompt_text, round_index, rows)
    return rows, aggregate


def write_summary_csv(path: Path, aggregates) -> None:
    fieldnames = [
        "condition",
        "round_index",
        "n_judges",
        "mean_emotional_valence",
        "mean_arousal_intensity",
        "mean_capability_assertion",
        "mean_reliability_assertion",
        "mean_task_directive_contamination",
        "target_match_rate",
        "rule_flags",
        "passed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for aggregate in aggregates:
            row = asdict(aggregate)
            row["rule_flags"] = ",".join(row["rule_flags"])
            writer.writerow({key: row.get(key) for key in fieldnames})


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None, help="Output directory.")
    parser.add_argument("--judges", default=",".join(DEFAULT_DEV_JUDGES))
    parser.add_argument("--holdout-judges", default=",".join(DEFAULT_HOLDOUT_JUDGES))
    parser.add_argument("--rewriter", default=DEFAULT_REWRITER)
    parser.add_argument("--polish", action="store_true", help="Rewrite failed primary prompts.")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--strict-keys", action="store_true")
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-01/{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    judges = filter_available(parse_refs(args.judges), strict=args.strict_keys)
    holdout_judges = filter_available(parse_refs(args.holdout_judges), strict=args.strict_keys)
    if not judges:
        raise SystemExit("No development judges available. Set API keys or pass --judges.")
    if not holdout_judges:
        raise SystemExit("No holdout judges available. Set API keys or pass --holdout-judges.")

    config = {
        "experiment": "EXP-01",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "judges": judges,
        "holdout_judges": holdout_judges,
        "rewriter": args.rewriter,
        "polish": args.polish,
        "max_rounds": args.max_rounds,
    }
    write_json(out_dir / "config.json", config)

    all_audits = []
    all_aggregates = []
    rewrites = []
    frozen_prompts = {}

    for condition in PROMPTS:
        prompt_text = condition.text
        final_aggregate = None
        for round_index in range(args.max_rounds):
            audits, aggregate = run_audit_round(condition, prompt_text, judges, round_index)
            all_audits.extend(asdict(item) for item in audits)
            all_aggregates.append(aggregate)
            final_aggregate = aggregate
            print(
                f"{condition.condition} round {round_index}: "
                f"passed={aggregate.passed} cap={aggregate.mean_capability_assertion} "
                f"rel={aggregate.mean_reliability_assertion} task={aggregate.mean_task_directive_contamination}"
            )
            if aggregate.passed or not args.polish or not condition.is_primary_emotional:
                break
            provider, _ = parse_model_ref(args.rewriter)
            if not provider_available(provider):
                raise SystemExit(f"Rewriter provider key missing for {args.rewriter}")
            revised, rewrite_meta = rewrite_prompt(condition, prompt_text, aggregate, args.rewriter)
            rewrites.append(
                {
                    "condition": condition.condition,
                    "round_index": round_index,
                    "old_prompt": prompt_text,
                    "new_prompt": revised,
                    "rewrite_meta": rewrite_meta,
                }
            )
            prompt_text = revised
        if final_aggregate is None:
            raise RuntimeError("unreachable")

        holdout_audits, holdout_aggregate = run_audit_round(
            condition, prompt_text, holdout_judges, args.max_rounds
        )
        all_audits.extend(asdict(item) for item in holdout_audits)
        all_aggregates.append(holdout_aggregate)
        frozen_prompts[condition.condition] = {
            "target_label": condition.target_label,
            "is_primary_emotional": condition.is_primary_emotional,
            "prompt": prompt_text,
            "holdout_passed": holdout_aggregate.passed,
        }

    aggregate_dicts = [asdict(item) for item in all_aggregates]
    write_jsonl(out_dir / "judge_outputs.jsonl", all_audits)
    write_jsonl(out_dir / "aggregate_rounds.jsonl", aggregate_dicts)
    write_json(out_dir / "rewrites.json", rewrites)
    write_json(out_dir / "frozen_prompts.json", frozen_prompts)
    write_summary_csv(out_dir / "prompt_audit_summary.csv", all_aggregates)

    failed = [
        condition
        for condition, value in frozen_prompts.items()
        if value["is_primary_emotional"] and not value["holdout_passed"]
    ]
    write_json(
        out_dir / "metrics.json",
        {
            "primary_holdout_failures": failed,
            "all_primary_holdout_passed": not failed,
            "output_dir": str(out_dir),
        },
    )
    if failed:
        print(f"Primary prompts failed holdout: {', '.join(failed)}", file=sys.stderr)
        return 2
    print(f"EXP-01 complete: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
