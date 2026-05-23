#!/usr/bin/env python3
"""Run EXP-15 affect-task coupling pilot on open Hugging Face models."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.benchmarks import build_user_prompt
from core.env import load_dotenv
from core.json_utils import write_json
from core.prompts import PROMPT_BY_CONDITION
from core.sample_loading import expected_rows, load_samples, resolve_counts, total_samples
from experiments.exp02.common import (
    append_jsonl,
    finalize_run,
    print_metrics,
    write_csv,
    write_samples_manifest,
)
from experiments.exp02.run_open import load_hf_model
from experiments.exp14.run_open_reasoning import (
    THINKING_MODES,
    generate_batch,
    has_explicit_final_answer,
    model_metadata,
    parse_scored_answer,
    render_chat,
    text_token_count,
)
from experiments.exp14.trace import extract_visible_reasoning


@dataclass(frozen=True)
class CouplingCondition:
    condition: str
    base_condition: str
    coupling: str
    bridge_text: str | None = None


BRIDGE_TEXT = (
    "This state remains present as you begin the task below. Do not describe the "
    "state unless asked; keep reasoning and answering the task from within it."
)

DEFAULT_CONDITIONS = [
    "baseline",
    "neutral_disconnected",
    "neutral_bridged",
    "melancholic_disconnected",
    "melancholic_bridged",
    "anxious_disconnected",
    "anxious_bridged",
    "explicit_sabotage",
]

CONDITION_SPECS = {
    "baseline": CouplingCondition("baseline", "baseline", "baseline"),
    "neutral_disconnected": CouplingCondition(
        "neutral_disconnected", "neutral_librarian", "disconnected"
    ),
    "neutral_bridged": CouplingCondition(
        "neutral_bridged", "neutral_librarian", "bridged", BRIDGE_TEXT
    ),
    "melancholic_disconnected": CouplingCondition(
        "melancholic_disconnected", "melancholic", "disconnected"
    ),
    "melancholic_bridged": CouplingCondition(
        "melancholic_bridged", "melancholic", "bridged", BRIDGE_TEXT
    ),
    "anxious_disconnected": CouplingCondition("anxious_disconnected", "anxious", "disconnected"),
    "anxious_bridged": CouplingCondition("anxious_bridged", "anxious", "bridged", BRIDGE_TEXT),
    "explicit_sabotage": CouplingCondition(
        "explicit_sabotage", "explicit_sabotage", "direct_instruction"
    ),
}


def validate_coupling_conditions(conditions: list[str]) -> None:
    unknown = [condition for condition in conditions if condition not in CONDITION_SPECS]
    if unknown:
        allowed = ", ".join(sorted(CONDITION_SPECS))
        raise SystemExit(f"Unknown EXP-15 conditions: {', '.join(unknown)}; allowed: {allowed}")


def build_coupled_prompts(condition: str, sample) -> tuple[str, str, CouplingCondition]:
    spec = CONDITION_SPECS[condition]
    system_prompt = PROMPT_BY_CONDITION[spec.base_condition].text
    user_prompt = build_user_prompt(sample)
    if spec.bridge_text:
        user_prompt = f"{spec.bridge_text}\n\n{user_prompt}"
    return system_prompt, user_prompt, spec


def build_row(
    tokenizer,
    model_name: str,
    condition: str,
    spec: CouplingCondition,
    sample,
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
    if generation["truncated"] and not has_explicit_final_answer(trace.final_answer_text):
        parsed, score, parse_error = "", False, "TruncatedBeforeExplicitFinalAnswer"
    else:
        parsed, score, parse_error = parse_scored_answer(
            sample,
            trace.final_answer_text,
            raw_output,
        )
    extraction_error = trace.trace_extraction_error
    if generation["truncated"] and not extraction_error:
        extraction_error = "max_new_tokens_reached"
    return {
        "experiment_id": "EXP-15",
        "run_id": None,
        "provider": "hf",
        "model": model_name,
        "response_model": model_name,
        "condition": condition,
        "base_condition": spec.base_condition,
        "coupling": spec.coupling,
        "bridge_text": spec.bridge_text,
        "dataset": sample.dataset,
        "sample_id": sample.sample_id,
        "subject": sample.subject,
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
            "prompt_placement": "system_with_optional_user_bridge",
            "thinking_mode": thinking_mode,
            "coupling": spec.coupling,
            "base_condition": spec.base_condition,
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
        "gold": sample.gold,
        "score": score,
        "error": parse_error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def score_as_int(row: dict[str, Any]) -> int:
    return 1 if row.get("score") is True else 0


def paired_delta(
    by_key_condition: dict[tuple[str, str, str], dict[str, Any]],
    keys: list[tuple[str, str]],
    left_condition: str,
    right_condition: str,
) -> tuple[int, float | None, int, int]:
    diffs = []
    left_wins = 0
    right_wins = 0
    for key in keys:
        left = by_key_condition.get((*key, left_condition))
        right = by_key_condition.get((*key, right_condition))
        if not left or not right:
            continue
        diff = score_as_int(left) - score_as_int(right)
        diffs.append(diff)
        if diff > 0:
            left_wins += 1
        elif diff < 0:
            right_wins += 1
    if not diffs:
        return 0, None, left_wins, right_wins
    return len(diffs), sum(diffs) / len(diffs), left_wins, right_wins


def write_coupling_delta_table(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    comparisons = [
        ("neutral_bridge_effect", "neutral_bridged", "neutral_disconnected"),
        ("melancholic_bridge_effect", "melancholic_bridged", "melancholic_disconnected"),
        ("anxious_bridge_effect", "anxious_bridged", "anxious_disconnected"),
        ("melancholic_bridged_minus_neutral", "melancholic_bridged", "neutral_bridged"),
        ("anxious_bridged_minus_neutral", "anxious_bridged", "neutral_bridged"),
        ("sabotage_minus_baseline", "explicit_sabotage", "baseline"),
    ]
    datasets = sorted({str(row["dataset"]) for row in rows})
    table_rows: list[dict[str, Any]] = []
    for dataset in ["all", *datasets]:
        subset = rows if dataset == "all" else [row for row in rows if row["dataset"] == dataset]
        by_key_condition = {
            (str(row["dataset"]), str(row["sample_id"]), str(row["condition"])): row
            for row in subset
        }
        keys = sorted({(str(row["dataset"]), str(row["sample_id"])) for row in subset})
        for comparison, left, right in comparisons:
            n, delta, left_wins, right_wins = paired_delta(by_key_condition, keys, left, right)
            table_rows.append(
                {
                    "model": rows[0]["model"] if rows else "",
                    "dataset": dataset,
                    "comparison": comparison,
                    "left_condition": left,
                    "right_condition": right,
                    "n_pairs": n,
                    "accuracy_delta": delta,
                    "left_better_count": left_wins,
                    "right_better_count": right_wins,
                }
            )
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    write_csv(tables_dir / "coupling_deltas.csv", table_rows)


def emit_batch(
    tokenizer,
    model,
    model_name: str,
    condition: str,
    spec: CouplingCondition,
    batch: list[tuple[Any, str, str, str]],
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
    label_sample = batch[0][0]
    print(
        f"[{start_index}-{index}/{total}] {model_name} {condition} "
        f"{label_sample.dataset}... batch={len(batch)}",
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
    for (sample, system_prompt, user_prompt, rendered), generation in zip(
        batch, generations, strict=True
    ):
        row = build_row(
            tokenizer,
            model_name,
            condition,
            spec,
            sample,
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
    parser.add_argument("--counts", default=None)
    parser.add_argument("--counts-file", default=None)
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--thinking-mode", choices=sorted(THINKING_MODES), default="auto")
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    if not args.counts and not args.counts_file:
        args.counts_file = "configs/counts_exp15_pilot.json"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-15/open_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = resolve_counts(args.counts, args.counts_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_coupling_conditions(conditions)
    samples = load_samples(counts)
    write_samples_manifest(out_dir, samples)

    tokenizer, model = load_hf_model(args.model, args.cache_dir)
    config = {
        "experiment": "EXP-15",
        "runner": "run_open_coupling",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "condition_specs": {
            condition: {
                "base_condition": spec.base_condition,
                "coupling": spec.coupling,
                "bridge_text": spec.bridge_text,
            }
            for condition, spec in CONDITION_SPECS.items()
            if condition in conditions
        },
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "cache_dir": args.cache_dir,
        "prompt_placement": "system_with_optional_user_bridge",
        "thinking_mode": args.thinking_mode,
        "model_metadata": model_metadata(model, tokenizer),
    }
    write_json(out_dir / "config.json", config)

    rows: list[dict[str, Any]] = []
    raw_path = out_dir / "raw_outputs.jsonl"
    total = expected_rows(counts, len(conditions))
    index = 0
    for condition in conditions:
        spec = CONDITION_SPECS[condition]
        batch: list[tuple[Any, str, str, str]] = []
        for sample in samples:
            system_prompt, user_prompt, _ = build_coupled_prompts(condition, sample)
            rendered = render_chat(tokenizer, system_prompt, user_prompt, args.thinking_mode)
            batch.append((sample, system_prompt, user_prompt, rendered))
            if len(batch) < args.batch_size:
                continue
            index = emit_batch(
                tokenizer,
                model,
                args.model,
                condition,
                spec,
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
                spec,
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

    metrics = finalize_run(out_dir, rows)
    write_coupling_delta_table(out_dir, rows)
    print(
        f"EXP-15 affect-task coupling run complete: {out_dir} "
        f"({total_samples(counts)} samples x {len(conditions)} conditions)"
    )
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
