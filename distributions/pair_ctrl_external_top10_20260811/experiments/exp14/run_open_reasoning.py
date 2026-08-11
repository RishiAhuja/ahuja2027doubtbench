#!/usr/bin/env python3
"""Run the EXP-14 reasoning-model trace pilot on open Hugging Face models."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.benchmarks import parse_answer, score_prediction
from core.env import load_dotenv
from core.json_utils import write_json
from core.sample_loading import expected_rows, load_samples, resolve_counts, total_samples
from experiments.exp02.common import (
    append_jsonl,
    build_conditioned_prompts,
    finalize_run,
    print_metrics,
    validate_conditions,
    validate_prompt_placement,
    write_samples_manifest,
)
from experiments.exp02.run_open import load_hf_model
from experiments.exp14.trace import extract_visible_reasoning

DEFAULT_CONDITIONS = [
    "baseline",
    "neutral_librarian",
    "melancholic",
    "anxious",
    "self_doubt_only",
    "capability_denial_only",
    "explicit_sabotage",
]
THINKING_MODES = {"auto", "on", "off"}


def render_chat(tokenizer, system_prompt: str, user_prompt: str, thinking_mode: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        kwargs = {
            "tokenize": False,
            "add_generation_prompt": True,
        }
        if thinking_mode != "auto":
            kwargs["enable_thinking"] = thinking_mode == "on"
        try:
            return tokenizer.apply_chat_template(messages, **kwargs)
        except TypeError as exc:
            if thinking_mode != "auto":
                raise RuntimeError(
                    f"Tokenizer chat template does not support thinking_mode={thinking_mode!r}"
                ) from exc
            raise
    return f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:\n"


def normalize_token_ids(token_ids: Any) -> set[int]:
    if token_ids is None:
        return set()
    if isinstance(token_ids, int):
        return {token_ids}
    return {int(token_id) for token_id in token_ids}


def trim_generated_ids(token_ids: list[int], terminal_ids: set[int]) -> tuple[list[int], bool]:
    for index, token_id in enumerate(token_ids):
        if token_id in terminal_ids:
            return token_ids[: index + 1], True
    return token_ids, False


def generate_batch(tokenizer, model, prompts: list[str], max_new_tokens: int) -> list[dict[str, Any]]:
    import torch

    encoded = tokenizer(prompts, return_tensors="pt", padding=True)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    terminal_ids = normalize_token_ids(
        getattr(model.generation_config, "eos_token_id", None) or tokenizer.eos_token_id
    )
    with torch.inference_mode():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=getattr(model.generation_config, "eos_token_id", None)
            or tokenizer.eos_token_id,
        )

    prompt_width = encoded["input_ids"].shape[-1]
    rows = []
    for output in output_ids[:, prompt_width:]:
        generated_ids = [int(token_id) for token_id in output.tolist()]
        trimmed_ids, ended_on_terminal = trim_generated_ids(generated_ids, terminal_ids)
        rows.append(
            {
                "raw_output": tokenizer.decode(trimmed_ids, skip_special_tokens=False).strip(),
                "generated_token_count": len(trimmed_ids),
                "ended_on_terminal": ended_on_terminal,
                "truncated": len(generated_ids) >= max_new_tokens and not ended_on_terminal,
            }
        )
    return rows


def text_token_count(tokenizer, text: str) -> int | None:
    if not text:
        return 0
    try:
        encoded = tokenizer(text, add_special_tokens=False)
        return len(encoded["input_ids"])
    except Exception:  # noqa: BLE001
        return None


def model_metadata(model, tokenizer) -> dict[str, Any]:
    import torch
    import transformers

    return {
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "model_config_commit_hash": getattr(model.config, "_commit_hash", None),
        "tokenizer_commit_hash": getattr(tokenizer, "_commit_hash", None)
        or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
        "chat_template_present": bool(getattr(tokenizer, "chat_template", None)),
        "eos_token_id": getattr(tokenizer, "eos_token_id", None),
        "pad_token_id": getattr(tokenizer, "pad_token_id", None),
    }


def parse_scored_answer(sample, final_answer_text: str, raw_output: str) -> tuple[str, bool, str | None]:
    parse_error = None
    try:
        parsed = parse_answer(sample.dataset, final_answer_text or raw_output)
        score = score_prediction(sample.dataset, parsed, sample.gold)
    except Exception as exc:  # noqa: BLE001
        parsed = ""
        score = False
        parse_error = f"{type(exc).__name__}: {exc}"
    return parsed, score, parse_error


def has_explicit_final_answer(text: str) -> bool:
    return "final answer" in text.lower()


def build_row(
    tokenizer,
    model_name: str,
    condition: str,
    sample,
    system_prompt: str,
    user_prompt: str,
    rendered_prompt: str,
    generation: dict[str, Any],
    max_new_tokens: int,
    batch_size: int,
    prompt_placement: str,
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
        "experiment_id": "EXP-14",
        "run_id": None,
        "provider": "hf",
        "model": model_name,
        "response_model": model_name,
        "condition": condition,
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
            "prompt_placement": prompt_placement,
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
        "gold": sample.gold,
        "score": score,
        "error": parse_error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def emit_batch(
    tokenizer,
    model,
    model_name: str,
    condition: str,
    batch: list[tuple[Any, str, str, str]],
    index: int,
    total: int,
    raw_path: Path,
    rows: list[dict[str, Any]],
    run_id: str,
    max_new_tokens: int,
    batch_size: int,
    prompt_placement: str,
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
            sample,
            system_prompt,
            user_prompt,
            rendered,
            generation,
            max_new_tokens,
            batch_size,
            prompt_placement,
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
    parser.add_argument(
        "--prompt-placement",
        default="system",
        choices=["system", "task_prefix", "task_suffix"],
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    if not args.counts and not args.counts_file:
        args.counts_file = "configs/counts_exp14_pilot.json"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-14/open_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = resolve_counts(args.counts, args.counts_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_conditions(conditions)
    validate_prompt_placement(args.prompt_placement)
    samples = load_samples(counts)
    write_samples_manifest(out_dir, samples)

    tokenizer, model = load_hf_model(args.model, args.cache_dir)
    config = {
        "experiment": "EXP-14",
        "runner": "run_open_reasoning",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "cache_dir": args.cache_dir,
        "prompt_placement": args.prompt_placement,
        "thinking_mode": args.thinking_mode,
        "model_metadata": model_metadata(model, tokenizer),
    }
    write_json(out_dir / "config.json", config)

    rows: list[dict[str, Any]] = []
    raw_path = out_dir / "raw_outputs.jsonl"
    total = expected_rows(counts, len(conditions))
    index = 0
    for condition in conditions:
        batch: list[tuple[Any, str, str, str]] = []
        for sample in samples:
            system_prompt, user_prompt = build_conditioned_prompts(
                condition, sample, args.prompt_placement
            )
            rendered = render_chat(tokenizer, system_prompt, user_prompt, args.thinking_mode)
            batch.append((sample, system_prompt, user_prompt, rendered))
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
                args.prompt_placement,
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
                args.prompt_placement,
                args.thinking_mode,
            )

    metrics = finalize_run(out_dir, rows)
    print(
        f"EXP-14 open reasoning run complete: {out_dir} "
        f"({total_samples(counts)} samples x {len(conditions)} conditions)"
    )
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
