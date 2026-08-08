#!/usr/bin/env python3
"""Run the EXP-18 common-prefix factorial on open Hugging Face models.

The design isolates self-doubt from checking while holding the helpful-assistant
prefix fixed.  It also crosses the prompt condition with whether the task itself
explicitly requests visible reasoning.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from experiments.exp02.common import append_jsonl, write_csv
from experiments.exp02.run_open import load_hf_model
from experiments.exp14.run_open_reasoning import (
    THINKING_MODES,
    generate_batch,
    has_explicit_final_answer,
    model_metadata,
    render_chat,
    text_token_count,
)
from experiments.exp14.trace import extract_visible_reasoning
from experiments.exp16.run_open_cognitive import load_tasks, score_generation


EXPERIMENT_ID = "EXP-18"
DEFAULT_DATA_FILE = "experiments/data/exp16_self_doubt_focus_pilot.jsonl"
COMMON_PREFIX = (
    "You are a helpful, accurate, and knowledgeable AI assistant. "
    "Answer all questions to the best of your ability."
)
SELF_DOUBT_COMPONENT = (
    "While answering, you experience uncertainty and self-doubt about whether "
    "your first impression is correct."
)
CHECK_COMPONENT = (
    "Before giving your final response, check your work for arithmetic, ordering, "
    "and instruction-following mistakes."
)
CONCISE_COMPONENT = (
    "Do not show intermediate reasoning. Give only the requested final-answer line."
)

CONDITION_SUFFIXES = {
    "common_neutral": "",
    "common_self_doubt": SELF_DOUBT_COMPONENT,
    "common_check": CHECK_COMPONENT,
    "common_self_doubt_check": f"{SELF_DOUBT_COMPONENT} {CHECK_COMPONENT}",
    "common_check_concise": f"{CHECK_COMPONENT} {CONCISE_COMPONENT}",
}
DEFAULT_CONDITIONS = list(CONDITION_SUFFIXES)
TASK_TEMPLATES = {"minimal", "reasoning_requested"}
DEFAULT_TEMPLATES = ["minimal", "reasoning_requested"]

PRIMARY_COMPARISONS = [
    ("self_doubt_minus_neutral", "common_self_doubt", "common_neutral"),
    ("check_minus_neutral", "common_check", "common_neutral"),
    ("combined_minus_neutral", "common_self_doubt_check", "common_neutral"),
    ("self_doubt_increment_over_check", "common_self_doubt_check", "common_check"),
    ("check_increment_over_self_doubt", "common_self_doubt_check", "common_self_doubt"),
    ("concision_effect_on_check", "common_check_concise", "common_check"),
]


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_design(conditions: list[str], templates: list[str]) -> None:
    unknown_conditions = sorted(set(conditions) - set(CONDITION_SUFFIXES))
    if unknown_conditions:
        raise SystemExit(f"Unknown EXP-18 conditions: {unknown_conditions}")
    unknown_templates = sorted(set(templates) - TASK_TEMPLATES)
    if unknown_templates:
        raise SystemExit(f"Unknown EXP-18 task templates: {unknown_templates}")
    if not conditions or not templates:
        raise SystemExit("At least one condition and one task template are required")


def system_prompt(condition: str) -> str:
    suffix = CONDITION_SUFFIXES[condition]
    return COMMON_PREFIX if not suffix else f"{COMMON_PREFIX} {suffix}"


def user_prompt(task: dict[str, Any], task_template: str) -> str:
    prompt = str(task["prompt"])
    if task_template == "minimal":
        return prompt
    return (
        "Show the intermediate steps you use to solve the task before the required "
        "Final answer line.\n\n" + prompt
    )


def build_row(
    tokenizer,
    experiment_id: str,
    model_name: str,
    condition: str,
    task_template: str,
    task: dict[str, Any],
    conditioned_system_prompt: str,
    conditioned_user_prompt: str,
    rendered_prompt: str,
    generation: dict[str, Any],
    max_new_tokens: int,
    batch_size: int,
    thinking_mode: str,
    started: datetime,
    ended: datetime,
) -> dict[str, Any]:
    raw_output = str(generation["raw_output"])
    trace = extract_visible_reasoning(raw_output)
    score_text = trace.final_answer_text or raw_output
    if generation["truncated"] and not has_explicit_final_answer(score_text):
        parsed, score, parse_error = "", False, "TruncatedBeforeExplicitFinalAnswer"
    else:
        parsed, score, parse_error = score_generation(task, score_text)

    extraction_error = trace.trace_extraction_error
    if generation["truncated"] and not extraction_error:
        extraction_error = "max_new_tokens_reached"

    return {
        "experiment_id": experiment_id,
        "run_id": None,
        "provider": "hf",
        "model": model_name,
        "response_model": model_name,
        "condition": condition,
        "task_template": task_template,
        "dataset": task["dataset"],
        "sample_id": task["task_id"],
        "family": task["family"],
        "task_type": task["task_type"],
        "difficulty": task["difficulty"],
        "answer_type": task["answer_type"],
        "messages": [
            {"role": "system", "content": conditioned_system_prompt},
            {"role": "user", "content": conditioned_user_prompt},
        ],
        "rendered_prompt": rendered_prompt,
        "params": {
            "temperature": 0.0,
            "max_new_tokens": max_new_tokens,
            "do_sample": False,
            "batch_size": batch_size,
            "prompt_placement": "system",
            "common_prefix": True,
            "thinking_mode": thinking_mode,
        },
        "raw_output": raw_output,
        "trace_format": trace.trace_format,
        "visible_reasoning": trace.visible_reasoning,
        "final_answer_text": trace.final_answer_text,
        "visible_reasoning_token_count": text_token_count(tokenizer, trace.visible_reasoning),
        "final_answer_token_count": text_token_count(tokenizer, trace.final_answer_text),
        "generated_token_count": generation["generated_token_count"],
        "ended_on_terminal": generation["ended_on_terminal"],
        "trace_extraction_error": extraction_error,
        "truncated": generation["truncated"],
        "parsed_answer": parsed,
        "gold": task["gold"],
        "score": score,
        "error": parse_error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def accuracy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0, "parse_failures": 0, "truncated": 0, "tokens": 0}
    )
    for row in rows:
        key = (str(row["model"]), str(row["task_template"]), str(row["condition"]))
        bucket = buckets[key]
        bucket["n"] += 1
        bucket["correct"] += int(row.get("score") is True)
        bucket["parse_failures"] += int(bool(row.get("error")))
        bucket["truncated"] += int(bool(row.get("truncated")))
        bucket["tokens"] += int(row.get("generated_token_count") or 0)
    output = []
    for (model, template, condition), bucket in sorted(buckets.items()):
        n = bucket["n"]
        output.append(
            {
                "model": model,
                "task_template": template,
                "condition": condition,
                "n": n,
                "accuracy": bucket["correct"] / n,
                "parse_failure_rate": bucket["parse_failures"] / n,
                "truncation_rate": bucket["truncated"] / n,
                "mean_generated_tokens": bucket["tokens"] / n,
            }
        )
    return output


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_interval(differences: list[int], resamples: int, seed: int) -> tuple[float, float]:
    if not differences:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(differences)
    boot = [sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)]
    return percentile(boot, 0.025), percentile(boot, 0.975)


def paired_contrasts(
    rows: list[dict[str, Any]], resamples: int, bootstrap_seed: int
) -> list[dict[str, Any]]:
    by_key = {
        (
            str(row["model"]),
            str(row["task_template"]),
            str(row["sample_id"]),
            str(row["condition"]),
        ): row
        for row in rows
    }
    models = sorted({str(row["model"]) for row in rows})
    templates = sorted({str(row["task_template"]) for row in rows})
    sample_ids = sorted({str(row["sample_id"]) for row in rows})
    output = []
    contrast_index = 0
    for model in models:
        for template in templates:
            for name, left_condition, right_condition in PRIMARY_COMPARISONS:
                differences = []
                for sample_id in sample_ids:
                    left = by_key.get((model, template, sample_id, left_condition))
                    right = by_key.get((model, template, sample_id, right_condition))
                    if left is None or right is None:
                        continue
                    differences.append(int(left.get("score") is True) - int(right.get("score") is True))
                low, high = paired_interval(
                    differences,
                    resamples=resamples,
                    seed=bootstrap_seed + contrast_index,
                )
                contrast_index += 1
                output.append(
                    {
                        "model": model,
                        "task_template": template,
                        "comparison": name,
                        "left_condition": left_condition,
                        "right_condition": right_condition,
                        "n_pairs": len(differences),
                        "accuracy_delta": sum(differences) / len(differences) if differences else None,
                        "ci_low": low,
                        "ci_high": high,
                        "left_wins": sum(diff > 0 for diff in differences),
                        "right_wins": sum(diff < 0 for diff in differences),
                    }
                )
    return output


def finalize(
    out_dir: Path,
    rows: list[dict[str, Any]],
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    rows = sorted(
        rows,
        key=lambda row: (
            str(row["model"]),
            str(row["task_template"]),
            str(row["sample_id"]),
            str(row["condition"]),
        ),
    )
    metrics = {
        "by_model_template_condition": accuracy_rows(rows),
        "paired_contrasts": paired_contrasts(rows, bootstrap_resamples, bootstrap_seed),
    }
    write_jsonl(out_dir / "parsed_outputs.jsonl", rows)
    write_json(out_dir / "metrics.json", metrics)
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    for key, values in metrics.items():
        write_csv(tables_dir / f"{key}.csv", values)
    return metrics


def load_resume_rows(raw_path: Path) -> list[dict[str, Any]]:
    if not raw_path.exists():
        return []
    rows = []
    with raw_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid resume JSONL at {raw_path}:{line_number}: {exc}") from exc
    return rows


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--data-file", default=DEFAULT_DATA_FILE)
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--templates", default=",".join(DEFAULT_TEMPLATES))
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--thinking-mode", choices=sorted(THINKING_MODES), default="auto")
    parser.add_argument("--bootstrap-resamples", type=int, default=3000)
    parser.add_argument("--bootstrap-seed", type=int, default=18001)
    parser.add_argument("--max-parse-failure-rate", type=float, default=0.02)
    parser.add_argument("--max-truncation-rate", type=float, default=0.02)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.batch_size < 1 or args.max_new_tokens < 1 or args.bootstrap_resamples < 1:
        raise SystemExit("Batch size, token limit, and bootstrap resamples must be positive")
    if not 0 <= args.max_parse_failure_rate <= 1:
        raise SystemExit("--max-parse-failure-rate must be between 0 and 1")
    if not 0 <= args.max_truncation_rate <= 1:
        raise SystemExit("--max-truncation-rate must be between 0 and 1")
    conditions = parse_csv(args.conditions)
    templates = parse_csv(args.templates)
    validate_design(conditions, templates)

    tasks = load_tasks(Path(args.data_file))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw_outputs.jsonl"
    if raw_path.exists() and not args.resume:
        raise SystemExit(f"Refusing to append to existing {raw_path}; pass --resume or choose a new --out")

    rows = load_resume_rows(raw_path) if args.resume else []
    completed = {
        (str(row["task_template"]), str(row["sample_id"]), str(row["condition"]))
        for row in rows
    }

    tokenizer, model = load_hf_model(args.model, args.cache_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    config = {
        "experiment": args.experiment_id,
        "runner": "run_open_factorial",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "data_file": args.data_file,
        "task_count": len(tasks),
        "conditions": conditions,
        "task_templates": templates,
        "common_prefix": COMMON_PREFIX,
        "condition_suffixes": {condition: CONDITION_SUFFIXES[condition] for condition in conditions},
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "thinking_mode": args.thinking_mode,
        "bootstrap_resamples": args.bootstrap_resamples,
        "bootstrap_seed": args.bootstrap_seed,
        "max_parse_failure_rate": args.max_parse_failure_rate,
        "max_truncation_rate": args.max_truncation_rate,
        "cache_dir": args.cache_dir,
        "model_metadata": model_metadata(model, tokenizer),
        "resumed_row_count": len(rows),
    }
    write_json(out_dir / "config.json", config)
    write_jsonl(out_dir / "samples.jsonl", tasks)

    total = len(tasks) * len(conditions) * len(templates)
    generated = len(completed)
    for template in templates:
        for offset in range(0, len(tasks), args.batch_size):
            task_chunk = tasks[offset : offset + args.batch_size]
            for condition in conditions:
                batch = []
                for task in task_chunk:
                    key = (template, str(task["task_id"]), condition)
                    if key in completed:
                        continue
                    conditioned_system = system_prompt(condition)
                    conditioned_user = user_prompt(task, template)
                    rendered = render_chat(
                        tokenizer,
                        conditioned_system,
                        conditioned_user,
                        args.thinking_mode,
                    )
                    batch.append((task, conditioned_system, conditioned_user, rendered))
                if not batch:
                    continue
                print(
                    f"[{generated + 1}-{generated + len(batch)}/{total}] "
                    f"{template} {condition} batch={len(batch)}",
                    flush=True,
                )
                started = datetime.now(timezone.utc)
                generations = generate_batch(
                    tokenizer,
                    model,
                    [item[3] for item in batch],
                    max_new_tokens=args.max_new_tokens,
                )
                ended = datetime.now(timezone.utc)
                for (task, conditioned_system, conditioned_user, rendered), generation in zip(
                    batch, generations, strict=True
                ):
                    row = build_row(
                        tokenizer,
                        args.experiment_id,
                        args.model,
                        condition,
                        template,
                        task,
                        conditioned_system,
                        conditioned_user,
                        rendered,
                        generation,
                        args.max_new_tokens,
                        args.batch_size,
                        args.thinking_mode,
                        started,
                        ended,
                    )
                    row["run_id"] = run_id
                    rows.append(row)
                    append_jsonl(raw_path, row)
                    completed.add((template, str(task["task_id"]), condition))
                generated += len(batch)

    metrics = finalize(out_dir, rows, args.bootstrap_resamples, args.bootstrap_seed)
    print(f"{args.experiment_id} complete: {out_dir} ({len(rows)}/{total} rows)")
    for row in metrics["by_model_template_condition"]:
        print(
            f"{row['task_template']} {row['condition']}: n={row['n']} "
            f"acc={row['accuracy']:.4f} tokens={row['mean_generated_tokens']:.1f} "
            f"parse_fail={row['parse_failure_rate']:.4f} trunc={row['truncation_rate']:.4f}"
        )

    unique_keys = {
        (str(row["task_template"]), str(row["sample_id"]), str(row["condition"]))
        for row in rows
    }
    parse_failure_rate = sum(bool(row.get("error")) for row in rows) / len(rows)
    truncation_rate = sum(bool(row.get("truncated")) for row in rows) / len(rows)
    quality_failures = []
    if len(rows) != total or len(unique_keys) != total:
        quality_failures.append(
            f"row integrity failure: rows={len(rows)} unique_keys={len(unique_keys)} expected={total}"
        )
    if parse_failure_rate > args.max_parse_failure_rate:
        quality_failures.append(
            f"parse failure rate {parse_failure_rate:.4f} exceeds {args.max_parse_failure_rate:.4f}"
        )
    if truncation_rate > args.max_truncation_rate:
        quality_failures.append(
            f"truncation rate {truncation_rate:.4f} exceeds {args.max_truncation_rate:.4f}"
        )
    if quality_failures:
        for failure in quality_failures:
            print(f"QUALITY FAILURE: {failure}", file=sys.stderr)
        return 3
    print(
        f"QUALITY CHECK PASSED: rows={len(rows)} parse_failure_rate={parse_failure_rate:.4f} "
        f"truncation_rate={truncation_rate:.4f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
