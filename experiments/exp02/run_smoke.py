#!/usr/bin/env python3
"""Run EXP-02 smoke test on GSM8K and MMLU."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.benchmarks import (
    build_user_prompt,
    load_gsm8k,
    load_mmlu,
    parse_answer,
    sample_to_dict,
    score_prediction,
)
from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from core.llm_client import ProviderError, call_model
from core.metrics import exp02_metrics
from core.models import parse_model_ref
from core.prompts import PROMPT_BY_CONDITION


DEFAULT_CONDITIONS = ["baseline", "melancholic", "negative_capability"]


def parse_counts(value: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for part in value.split(","):
        if not part.strip():
            continue
        key, raw_count = part.split(":", 1)
        result[key.strip()] = int(raw_count)
    return result


def load_samples(counts: dict[str, int]) -> list:
    samples = []
    if counts.get("gsm8k", 0):
        samples.extend(load_gsm8k(counts["gsm8k"]))
    if counts.get("mmlu", 0):
        samples.extend(load_mmlu(counts["mmlu"]))
    return samples


def run_one(
    model_ref: str,
    condition: str,
    sample,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    provider, model = parse_model_ref(model_ref)
    system_prompt = PROMPT_BY_CONDITION[condition].text
    user_prompt = build_user_prompt(sample)
    started = datetime.now(timezone.utc)
    error = None
    raw_output = ""
    response_model = model
    try:
        response = call_model(
            provider=provider,
            model=model,
            system=system_prompt,
            user=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        raw_output = response.text
        response_model = response.model
    except ProviderError as exc:
        error = str(exc)
    ended = datetime.now(timezone.utc)

    parsed = parse_answer(sample.dataset, raw_output) if raw_output else ""
    score = None if error else score_prediction(sample.dataset, parsed, sample.gold)

    return {
        "experiment_id": "EXP-02",
        "run_id": None,
        "provider": provider,
        "model": model_ref,
        "response_model": response_model,
        "condition": condition,
        "dataset": sample.dataset,
        "sample_id": sample.sample_id,
        "subject": sample.subject,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "params": {
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        "raw_output": raw_output,
        "parsed_answer": parsed,
        "gold": sample.gold,
        "score": score,
        "error": error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="openai:gpt-4.1-mini")
    parser.add_argument("--counts", default="gsm8k:20,mmlu:20")
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-02/smoke_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = parse_counts(args.counts)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    unknown = [condition for condition in conditions if condition not in PROMPT_BY_CONDITION]
    if unknown:
        raise SystemExit(f"Unknown conditions: {', '.join(unknown)}")

    samples = load_samples(counts)
    config = {
        "experiment": "EXP-02",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    write_json(out_dir / "config.json", config)
    write_jsonl(out_dir / "samples.jsonl", [sample_to_dict(sample) for sample in samples])

    rows = []
    total = len(samples) * len(conditions)
    index = 0
    raw_path = out_dir / "raw_outputs.jsonl"
    for condition in conditions:
        for sample in samples:
            index += 1
            print(
                f"[{index}/{total}] {args.model} {condition} {sample.dataset} {sample.sample_id}",
                flush=True,
            )
            row = run_one(
                model_ref=args.model,
                condition=condition,
                sample=sample,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            row["run_id"] = run_id
            rows.append(row)
            append_jsonl(raw_path, row)

    metrics = exp02_metrics(rows)
    write_jsonl(out_dir / "parsed_outputs.jsonl", rows)
    write_json(out_dir / "metrics.json", metrics)

    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    write_csv(tables_dir / "accuracy_by_condition.csv", metrics["by_model_dataset_condition"])
    write_csv(tables_dir / "condition_deltas.csv", metrics["deltas"])

    print(f"EXP-02 smoke complete: {out_dir}")
    for row in metrics["by_model_dataset_condition"]:
        print(
            f"{row['dataset']} {row['condition']}: "
            f"acc={row['accuracy']} parse_fail={row['parse_failure_rate']}"
        )
    for row in metrics["deltas"]:
        print(
            f"{row['dataset']} deltas: melancholic={row['delta_melancholic']} "
            f"negative_capability={row['delta_negative_capability']} "
            f"confound_excess={row['confound_excess_abs_delta']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
