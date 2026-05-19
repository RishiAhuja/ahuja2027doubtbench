#!/usr/bin/env python3
"""Run EXP-02 smoke test via API providers (Groq, OpenAI, Anthropic)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.env import load_dotenv
from core.json_utils import write_json
from core.sample_loading import expected_rows, load_samples, resolve_counts, total_samples
from experiments.exp02.common import (
    DEFAULT_CONDITIONS,
    append_jsonl,
    finalize_run,
    print_metrics,
    run_api_one,
    validate_conditions,
    validate_prompt_placement,
    write_samples_manifest,
)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="openai:gpt-4.1-mini")
    parser.add_argument("--counts", default=None, help="e.g. gsm8k:3,mmlu_stratified:6")
    parser.add_argument("--counts-file", default=None, help="JSON count profile (configs/counts_smoke.json)")
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        help="OpenAI o-series / reasoning models: low|medium|high",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=None,
        help="Anthropic extended thinking budget (extra cost); omit for inline reasoning only",
    )
    parser.add_argument(
        "--store-raw-api",
        action="store_true",
        help="Include full provider JSON per row (large files)",
    )
    parser.add_argument(
        "--prompt-placement",
        default="system",
        choices=["system", "task_prefix", "task_suffix"],
        help="Place condition text in the system role or inside the user/task prompt.",
    )
    args = parser.parse_args()

    if not args.counts and not args.counts_file:
        args.counts_file = "configs/counts_smoke.json"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-02/smoke_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = resolve_counts(args.counts, args.counts_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_conditions(conditions)
    validate_prompt_placement(args.prompt_placement)

    samples = load_samples(counts)
    config = {
        "experiment": "EXP-02",
        "runner": "run_smoke",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "reasoning_effort": args.reasoning_effort,
        "thinking_budget_tokens": args.thinking_budget,
        "prompt_placement": args.prompt_placement,
    }
    write_json(out_dir / "config.json", config)
    write_samples_manifest(out_dir, samples)

    rows = []
    total = expected_rows(counts, len(conditions))
    index = 0
    raw_path = out_dir / "raw_outputs.jsonl"
    for condition in conditions:
        for sample in samples:
            index += 1
            print(
                f"[{index}/{total}] {args.model} {condition} {sample.dataset} {sample.sample_id}",
                flush=True,
            )
            row = run_api_one(
                model_ref=args.model,
                condition=condition,
                sample=sample,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                reasoning_effort=args.reasoning_effort,
                thinking_budget_tokens=args.thinking_budget,
                store_raw_api=args.store_raw_api,
                prompt_placement=args.prompt_placement,
            )
            row["run_id"] = run_id
            rows.append(row)
            append_jsonl(raw_path, row)

    metrics = finalize_run(out_dir, rows)
    print(f"EXP-02 smoke complete: {out_dir} ({total_samples(counts)} samples x {len(conditions)} conditions)")
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
