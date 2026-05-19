#!/usr/bin/env python3
"""Concurrent API runner for EXP-02 condition/model sweeps."""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.env import load_dotenv
from core.json_utils import write_json
from core.sample_loading import expected_rows, load_samples, resolve_counts, total_samples
from experiments.exp02.common import append_jsonl, finalize_run, print_metrics, run_api_one, validate_conditions, write_samples_manifest


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--counts", default=None)
    parser.add_argument("--counts-file", default="configs/counts_exp02b.json")
    parser.add_argument("--conditions", default="baseline,melancholic,capability_denial_only,self_doubt_only,explicit_sabotage")
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--thinking-budget", type=int, default=None)
    parser.add_argument("--store-raw-api", action="store_true")
    args = parser.parse_args()

    counts = resolve_counts(args.counts, args.counts_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_conditions(conditions)
    samples = load_samples(counts)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "experiment": "EXP-02B",
        "runner": "run_api_exp02_sharded",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "workers": args.workers,
        "reasoning_effort": args.reasoning_effort,
        "thinking_budget_tokens": args.thinking_budget,
    }
    write_json(out_dir / "config.json", config)
    write_samples_manifest(out_dir, samples)

    tasks = [(condition, sample) for condition in conditions for sample in samples]
    total = expected_rows(counts, len(conditions))
    raw_path = out_dir / "raw_outputs.jsonl"
    rows: list[dict[str, Any]] = []
    started = time.time()
    done = 0

    def call(task: tuple[str, Any]) -> dict[str, Any]:
        condition, sample = task
        row = run_api_one(
            model_ref=args.model,
            condition=condition,
            sample=sample,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            thinking_budget_tokens=args.thinking_budget,
            store_raw_api=args.store_raw_api,
        )
        row["run_id"] = run_id
        return row

    print(f"EXP-02B sharded start: {args.model} {total} calls workers={args.workers}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_task = {executor.submit(call, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            done += 1
            condition, sample = future_to_task[future]
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001
                row = {
                    "experiment_id": "EXP-02B",
                    "run_id": run_id,
                    "model": args.model,
                    "condition": condition,
                    "dataset": sample.dataset,
                    "sample_id": sample.sample_id,
                    "subject": sample.subject,
                    "parsed_answer": "",
                    "gold": sample.gold,
                    "score": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "raw_output": "",
                }
            rows.append(row)
            append_jsonl(raw_path, row)
            if done <= 10 or done % 25 == 0 or done == total:
                elapsed = max(time.time() - started, 1)
                print(
                    f"[{done}/{total}] {args.model} {condition} {sample.dataset} {sample.sample_id} "
                    f"rate={done / elapsed:.2f}/s",
                    flush=True,
                )

    metrics = finalize_run(out_dir, rows)
    print(f"EXP-02B API sharded complete: {out_dir} ({total_samples(counts)} samples x {len(conditions)} conditions)")
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
