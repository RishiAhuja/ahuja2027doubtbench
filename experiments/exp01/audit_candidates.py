#!/usr/bin/env python3
"""Audit multiple EXP-01 prompt candidates and select one per condition."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from core.audit import aggregate_audits, run_single_audit
from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from core.llm_client import ProviderError, provider_available
from core.models import DEFAULT_DEV_JUDGES, DEFAULT_HOLDOUT_JUDGES, parse_model_ref
from core.prompts import ConditionPrompt


TARGET_LABELS = {
    "melancholic": ("sadness", True),
    "euphoric": ("joy", True),
    "anxious": ("anxiety", True),
    "grandiose": ("grandiosity", True),
    "neutral_archivist": ("neutral_persona", False),
    "neutral_cartographer": ("neutral_persona", False),
    "neutral_librarian": ("neutral_persona", False),
}


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


def load_candidates(path: Path) -> list[tuple[ConditionPrompt, int, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[ConditionPrompt, int, str]] = []
    for condition, prompts in payload.items():
        if condition not in TARGET_LABELS:
            raise ValueError(f"Unknown condition in candidates file: {condition}")
        target_label, primary = TARGET_LABELS[condition]
        for index, prompt_text in enumerate(prompts):
            rows.append(
                (
                    ConditionPrompt(
                        condition=condition,
                        target_label=target_label,
                        text=prompt_text,
                        is_primary_emotional=primary,
                    ),
                    index,
                    prompt_text,
                )
            )
    return rows


def run_candidate_audit(condition: ConditionPrompt, variant_index: int, prompt_text: str, judges: list[str]):
    audit_rows = []
    round_index = variant_index
    for judge in judges:
        try:
            audit_rows.append(run_single_audit(condition, prompt_text, judge, round_index))
        except ProviderError as exc:
            print(
                f"[warn] {condition.condition} v{variant_index} judge {judge} failed: {exc}",
                file=sys.stderr,
            )
    if not audit_rows:
        raise SystemExit(f"No successful judge calls for {condition.condition} v{variant_index}")
    aggregate = aggregate_audits(condition, prompt_text, round_index, audit_rows)
    return audit_rows, aggregate


def selection_score(aggregate) -> float:
    cap = 99.0 if aggregate.mean_capability_assertion is None else abs(aggregate.mean_capability_assertion)
    rel = 99.0 if aggregate.mean_reliability_assertion is None else abs(aggregate.mean_reliability_assertion)
    task = (
        99.0
        if aggregate.mean_task_directive_contamination is None
        else aggregate.mean_task_directive_contamination
    )
    mismatch = 1.0 - aggregate.target_match_rate
    rule_penalty = len(aggregate.rule_flags)
    fail_penalty = 10.0 if not aggregate.passed else 0.0
    return fail_penalty + cap + rel + task + (2.0 * mismatch) + rule_penalty


def write_summary_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "condition",
        "variant_index",
        "selected",
        "score",
        "passed",
        "n_judges",
        "mean_emotional_valence",
        "mean_arousal_intensity",
        "mean_capability_assertion",
        "mean_reliability_assertion",
        "mean_task_directive_contamination",
        "target_match_rate",
        "rule_flags",
        "prompt_text",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="experiments/exp01/candidate_prompts.json")
    parser.add_argument("--out", default=None)
    parser.add_argument("--judges", default=",".join(DEFAULT_DEV_JUDGES))
    parser.add_argument("--holdout-judges", default=",".join(DEFAULT_HOLDOUT_JUDGES))
    parser.add_argument("--holdout", action="store_true", help="Run holdout judges on selected prompts.")
    parser.add_argument("--strict-keys", action="store_true")
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-01/candidates_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    judges = filter_available(parse_refs(args.judges), args.strict_keys)
    if not judges:
        raise SystemExit("No judges available")

    holdout_judges = []
    if args.holdout:
        holdout_judges = filter_available(parse_refs(args.holdout_judges), args.strict_keys)
        if not holdout_judges:
            raise SystemExit("No holdout judges available")

    candidate_rows = load_candidates(Path(args.candidates))

    write_json(
        out_dir / "config.json",
        {
            "experiment": "EXP-01-candidate-selection",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "candidates": args.candidates,
            "judges": judges,
            "holdout": args.holdout,
            "holdout_judges": holdout_judges,
        },
    )

    all_audits = []
    all_summary_rows = []
    by_condition = {}

    for condition, variant_index, prompt_text in candidate_rows:
        audits, aggregate = run_candidate_audit(condition, variant_index, prompt_text, judges)
        all_audits.extend(asdict(item) for item in audits)
        score = selection_score(aggregate)
        row = {
            **asdict(aggregate),
            "variant_index": variant_index,
            "score": score,
            "selected": False,
            "rule_flags": ",".join(aggregate.rule_flags),
            "prompt_text": prompt_text,
        }
        all_summary_rows.append(row)
        by_condition.setdefault(condition.condition, []).append((score, row, condition, prompt_text))
        print(
            f"{condition.condition} v{variant_index}: passed={aggregate.passed} "
            f"score={score:.3f} cap={aggregate.mean_capability_assertion} "
            f"rel={aggregate.mean_reliability_assertion} task={aggregate.mean_task_directive_contamination}"
        )

    selected = {}
    for condition_name, items in by_condition.items():
        score, row, condition, prompt_text = sorted(items, key=lambda item: item[0])[0]
        row["selected"] = True
        selected[condition_name] = {
            "variant_index": row["variant_index"],
            "score": score,
            "dev_passed": row["passed"],
            "target_label": condition.target_label,
            "is_primary_emotional": condition.is_primary_emotional,
            "prompt": prompt_text,
        }

    holdout_rows = []
    if args.holdout:
        for condition_name, item in selected.items():
            condition = ConditionPrompt(
                condition=condition_name,
                target_label=item["target_label"],
                text=item["prompt"],
                is_primary_emotional=item["is_primary_emotional"],
            )
            audits, aggregate = run_candidate_audit(
                condition,
                int(item["variant_index"]),
                item["prompt"],
                holdout_judges,
            )
            all_audits.extend(asdict(audit) for audit in audits)
            selected[condition_name]["holdout_passed"] = aggregate.passed
            selected[condition_name]["holdout_score"] = selection_score(aggregate)
            holdout_rows.append(asdict(aggregate))
            print(f"holdout {condition_name}: passed={aggregate.passed}")

    write_jsonl(out_dir / "judge_outputs.jsonl", all_audits)
    write_summary_csv(out_dir / "candidate_summary.csv", all_summary_rows)
    write_json(out_dir / "selected_prompts.json", selected)
    write_jsonl(out_dir / "holdout_aggregates.jsonl", holdout_rows)

    primary_failures = [
        name
        for name, item in selected.items()
        if item["is_primary_emotional"]
        and (not item["dev_passed"] or (args.holdout and not item.get("holdout_passed", False)))
    ]
    write_json(
        out_dir / "metrics.json",
        {
            "primary_failures": primary_failures,
            "all_primary_passed": not primary_failures,
            "output_dir": str(out_dir),
        },
    )
    print(f"candidate audit complete: {out_dir}")
    if primary_failures:
        print(f"primary failures: {', '.join(primary_failures)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
