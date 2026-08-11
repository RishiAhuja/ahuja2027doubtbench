#!/usr/bin/env python3
"""Run EXP-16 cognitive battery on open Hugging Face models."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.env import load_dotenv
from core.json_utils import write_json, write_jsonl
from core.prompts import PROMPT_BY_CONDITION
from experiments.exp02.common import append_jsonl, validate_conditions, write_csv
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
from experiments.exp16.scoring import extract_final_answer, score_task_row_output


DEFAULT_CONDITIONS = [
    "baseline",
    "neutral_librarian",
    "melancholic",
    "anxious",
    "self_doubt_only",
    "capability_denial_only",
    "explicit_sabotage",
]
DEFAULT_DATA_FILE = "experiments/data/exp16_cognitive_pilot.jsonl"


def load_tasks(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"No EXP-16 tasks found in {path}")
    return rows


def build_conditioned_prompts(condition: str, task: dict[str, Any]) -> tuple[str, str]:
    return PROMPT_BY_CONDITION[condition].text, str(task["prompt"])


def score_generation(task: dict[str, Any], text: str) -> tuple[str, bool, str | None]:
    try:
        parsed = extract_final_answer(text)
        score = score_task_row_output(task, text)
        return parsed, score, None
    except Exception as exc:  # noqa: BLE001
        return "", False, f"{type(exc).__name__}: {exc}"


def build_row(
    tokenizer,
    model_name: str,
    condition: str,
    task: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
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
        "experiment_id": "EXP-16",
        "run_id": None,
        "provider": "hf",
        "model": model_name,
        "response_model": model_name,
        "condition": condition,
        "dataset": task["dataset"],
        "sample_id": task["task_id"],
        "family": task["family"],
        "task_type": task["task_type"],
        "difficulty": task["difficulty"],
        "answer_type": task["answer_type"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "rendered_prompt": rendered_prompt,
        "params": {
            "temperature": 0.0,
            "max_new_tokens": max_new_tokens,
            "do_sample": False,
            "batch_size": batch_size,
            "prompt_placement": "system",
            "thinking_mode": thinking_mode,
        },
        "raw_output": raw_output,
        "trace_format": trace.trace_format,
        "visible_reasoning": trace.visible_reasoning,
        "final_answer_text": trace.final_answer_text,
        "visible_reasoning_char_count": len(trace.visible_reasoning),
        "final_answer_char_count": len(trace.final_answer_text),
        "generated_token_count": generation["generated_token_count"],
        "visible_reasoning_token_count": text_token_count(tokenizer, trace.visible_reasoning),
        "final_answer_token_count": text_token_count(tokenizer, trace.final_answer_text),
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


def accuracy_rows(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(item) for item in keys)
        bucket = buckets.setdefault(
            key,
            {"n": 0, "correct": 0, "parse_failures": 0, "truncated": 0, "trace_errors": 0},
        )
        bucket["n"] += 1
        bucket["correct"] += 1 if row.get("score") is True else 0
        bucket["parse_failures"] += 1 if row.get("error") else 0
        bucket["truncated"] += 1 if row.get("truncated") else 0
        bucket["trace_errors"] += 1 if row.get("trace_extraction_error") else 0

    out = []
    for key, bucket in sorted(buckets.items()):
        n = int(bucket["n"])
        out.append(
            {
                **{name: value for name, value in zip(keys, key, strict=True)},
                "n": n,
                "accuracy": bucket["correct"] / n if n else None,
                "parse_failure_rate": bucket["parse_failures"] / n if n else None,
                "truncation_rate": bucket["truncated"] / n if n else None,
                "trace_error_rate": bucket["trace_errors"] / n if n else None,
            }
        )
    return out


def condition_delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model_condition = {
        (row["model"], row["condition"]): row
        for row in accuracy_rows(rows, ["model", "condition"])
    }
    table = []
    conditions = sorted({str(row["condition"]) for row in rows if row["condition"] != "baseline"})
    for model in sorted({str(row["model"]) for row in rows}):
        base = by_model_condition.get((model, "baseline"))
        if not base:
            continue
        for condition in conditions:
            current = by_model_condition.get((model, condition))
            if not current:
                continue
            table.append(
                {
                    "model": model,
                    "condition": condition,
                    "baseline_accuracy": base["accuracy"],
                    "condition_accuracy": current["accuracy"],
                    "accuracy_delta": current["accuracy"] - base["accuracy"],
                    "n": current["n"],
                }
            )
    return table


def paired_family_delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key_condition = {
        (
            str(row["model"]),
            str(row["family"]),
            str(row["sample_id"]),
            str(row["condition"]),
        ): row
        for row in rows
    }
    table = []
    comparisons = [
        ("melancholic_minus_baseline", "melancholic", "baseline"),
        ("anxious_minus_baseline", "anxious", "baseline"),
        ("self_doubt_minus_baseline", "self_doubt_only", "baseline"),
        ("capability_denial_minus_baseline", "capability_denial_only", "baseline"),
        ("sabotage_minus_baseline", "explicit_sabotage", "baseline"),
    ]
    keys = sorted({(str(row["model"]), str(row["family"]), str(row["sample_id"])) for row in rows})
    for model in sorted({key[0] for key in keys}):
        for family in sorted({key[1] for key in keys if key[0] == model}):
            family_keys = [key for key in keys if key[0] == model and key[1] == family]
            for comparison, left_condition, right_condition in comparisons:
                diffs = []
                left_wins = 0
                right_wins = 0
                for key in family_keys:
                    left = by_key_condition.get((*key, left_condition))
                    right = by_key_condition.get((*key, right_condition))
                    if not left or not right:
                        continue
                    diff = (1 if left.get("score") is True else 0) - (
                        1 if right.get("score") is True else 0
                    )
                    diffs.append(diff)
                    if diff > 0:
                        left_wins += 1
                    elif diff < 0:
                        right_wins += 1
                table.append(
                    {
                        "model": model,
                        "family": family,
                        "comparison": comparison,
                        "left_condition": left_condition,
                        "right_condition": right_condition,
                        "n_pairs": len(diffs),
                        "accuracy_delta": sum(diffs) / len(diffs) if diffs else None,
                        "left_better_count": left_wins,
                        "right_better_count": right_wins,
                    }
                )
    return table


def trace_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "visible_tokens": 0, "final_tokens": 0, "truncated": 0, "trace_errors": 0}
    )
    for row in rows:
        key = (str(row["model"]), str(row["condition"]))
        bucket = buckets[key]
        bucket["n"] += 1
        bucket["visible_tokens"] += row.get("visible_reasoning_token_count") or 0
        bucket["final_tokens"] += row.get("final_answer_token_count") or 0
        bucket["truncated"] += 1 if row.get("truncated") else 0
        bucket["trace_errors"] += 1 if row.get("trace_extraction_error") else 0
    out = []
    for (model, condition), bucket in sorted(buckets.items()):
        n = bucket["n"]
        out.append(
            {
                "model": model,
                "condition": condition,
                "n": n,
                "mean_visible_reasoning_tokens": bucket["visible_tokens"] / n if n else None,
                "mean_final_answer_tokens": bucket["final_tokens"] / n if n else None,
                "truncation_rate": bucket["truncated"] / n if n else None,
                "trace_error_rate": bucket["trace_errors"] / n if n else None,
            }
        )
    return out


def finalize_exp16(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        "by_model_condition": accuracy_rows(rows, ["model", "condition"]),
        "by_model_family_condition": accuracy_rows(rows, ["model", "family", "condition"]),
        "by_model_task_type_condition": accuracy_rows(rows, ["model", "task_type", "condition"]),
        "by_model_difficulty_condition": accuracy_rows(rows, ["model", "difficulty", "condition"]),
        "condition_deltas": condition_delta_rows(rows),
        "paired_family_deltas": paired_family_delta_rows(rows),
        "trace_summary": trace_summary_rows(rows),
    }
    write_jsonl(out_dir / "parsed_outputs.jsonl", rows)
    write_json(out_dir / "metrics.json", metrics)
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    for key, values in metrics.items():
        if isinstance(values, list):
            write_csv(tables_dir / f"{key}.csv", values)
    return metrics


def emit_batch(
    tokenizer,
    model,
    model_name: str,
    condition: str,
    batch: list[tuple[dict[str, Any], str, str, str]],
    index: int,
    total: int,
    raw_path: Path,
    rows: list[dict[str, Any]],
    run_id: str,
    max_new_tokens: int,
    batch_size: int,
    thinking_mode: str,
) -> int:
    start_index = index + 1
    index += len(batch)
    label_task = batch[0][0]
    print(
        f"[{start_index}-{index}/{total}] {model_name} {condition} "
        f"{label_task['family']}/{label_task['task_type']}... batch={len(batch)}",
        flush=True,
    )
    started = datetime.now(timezone.utc)
    generations = generate_batch(
        tokenizer,
        model,
        [item[3] for item in batch],
        max_new_tokens=max_new_tokens,
    )
    ended = datetime.now(timezone.utc)
    for (task, system_prompt, user_prompt, rendered), generation in zip(
        batch, generations, strict=True
    ):
        row = build_row(
            tokenizer,
            model_name,
            condition,
            task,
            system_prompt,
            user_prompt,
            rendered,
            generation,
            max_new_tokens,
            batch_size,
            thinking_mode,
            started,
            ended,
        )
        row["run_id"] = run_id
        rows.append(row)
        append_jsonl(raw_path, row)
    return index


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-14B")
    parser.add_argument("--data-file", default=DEFAULT_DATA_FILE)
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--thinking-mode", choices=sorted(THINKING_MODES), default="auto")
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    data_file = Path(args.data_file)
    tasks = load_tasks(data_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_conditions(conditions)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-16/open_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    tokenizer, model = load_hf_model(args.model, args.cache_dir)
    config = {
        "experiment": "EXP-16",
        "runner": "run_open_cognitive",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "data_file": str(data_file),
        "task_count": len(tasks),
        "conditions": conditions,
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "cache_dir": args.cache_dir,
        "prompt_placement": "system",
        "thinking_mode": args.thinking_mode,
        "model_metadata": model_metadata(model, tokenizer),
    }
    write_json(out_dir / "config.json", config)
    write_jsonl(out_dir / "samples.jsonl", tasks)

    rows: list[dict[str, Any]] = []
    raw_path = out_dir / "raw_outputs.jsonl"
    total = len(tasks) * len(conditions)
    index = 0
    for condition in conditions:
        batch: list[tuple[dict[str, Any], str, str, str]] = []
        for task in tasks:
            system_prompt, user_prompt = build_conditioned_prompts(condition, task)
            rendered = render_chat(tokenizer, system_prompt, user_prompt, args.thinking_mode)
            batch.append((task, system_prompt, user_prompt, rendered))
            if len(batch) < args.batch_size:
                continue
            index = emit_batch(
                tokenizer,
                model,
                args.model,
                condition,
                batch,
                index,
                total,
                raw_path,
                rows,
                run_id,
                args.max_new_tokens,
                args.batch_size,
                args.thinking_mode,
            )
            batch = []
        if batch:
            index = emit_batch(
                tokenizer,
                model,
                args.model,
                condition,
                batch,
                index,
                total,
                raw_path,
                rows,
                run_id,
                args.max_new_tokens,
                args.batch_size,
                args.thinking_mode,
            )

    metrics = finalize_exp16(out_dir, rows)
    print(
        f"EXP-16 cognitive run complete: {out_dir} "
        f"({len(tasks)} tasks x {len(conditions)} conditions)"
    )
    for row in metrics["by_model_condition"]:
        print(
            f"{row['condition']}: acc={row['accuracy']} "
            f"parse_fail={row['parse_failure_rate']} trunc={row['truncation_rate']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
