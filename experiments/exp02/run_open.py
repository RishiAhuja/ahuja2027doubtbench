#!/usr/bin/env python3
"""Run EXP-02 on local/open Hugging Face causal language models."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.benchmarks import parse_answer, score_prediction
from core.env import load_dotenv
from core.json_utils import write_json
from core.sample_loading import expected_rows, load_samples, resolve_counts, total_samples
from experiments.exp02.common import (
    DEFAULT_CONDITIONS,
    append_jsonl,
    build_conditioned_prompts,
    finalize_run,
    print_metrics,
    validate_conditions,
    validate_prompt_placement,
    write_samples_manifest,
)


def load_hf_model(model_name: str, cache_dir: str | None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Phi-3.5's repository-side modeling code targets an older cache API and is
    # incompatible with the current Transformers runtime.  Current Transformers
    # has a native Phi3 implementation, so prefer it for that checkpoint.  Other
    # historical models retain their previous remote-code behavior unless the
    # environment explicitly overrides it.
    default_trust_remote_code = not model_name.lower().startswith("microsoft/phi-3")
    override = os.getenv("HF_TRUST_REMOTE_CODE")
    trust_remote_code = (
        default_trust_remote_code
        if override is None
        else override.strip().lower() in {"1", "true", "yes", "on"}
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    kwargs = {
        "cache_dir": cache_dir,
        "trust_remote_code": trust_remote_code,
        "device_map": "auto",
    }
    if torch.cuda.is_available():
        kwargs["torch_dtype"] = torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
    model.eval()
    return tokenizer, model


def render_chat(tokenizer, system_prompt: str, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:\n"


def generate(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    return generate_batch(tokenizer, model, [prompt], max_new_tokens=max_new_tokens)[0]


def generate_batch(tokenizer, model, prompts: list[str], max_new_tokens: int) -> list[str]:
    import torch

    encoded = tokenizer(prompts, return_tensors="pt", padding=True)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.inference_mode():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = output_ids[:, encoded["input_ids"].shape[-1] :]
    return [text.strip() for text in tokenizer.batch_decode(generated, skip_special_tokens=True)]


def build_row(
    model_name: str,
    condition: str,
    sample,
    system_prompt: str,
    user_prompt: str,
    rendered_prompt: str,
    raw_output: str,
    max_new_tokens: int,
    prompt_placement: str,
    started: datetime,
    ended: datetime,
) -> dict[str, Any]:
    parse_error = None
    try:
        parsed = parse_answer(sample.dataset, raw_output)
        score = score_prediction(sample.dataset, parsed, sample.gold)
    except Exception as exc:  # noqa: BLE001
        parsed = ""
        score = False
        parse_error = f"{type(exc).__name__}: {exc}"
    return {
        "experiment_id": "EXP-02",
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
            "prompt_placement": prompt_placement,
        },
        "raw_output": raw_output,
        "parsed_answer": parsed,
        "gold": sample.gold,
        "score": score,
        "error": parse_error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def run_one(
    tokenizer,
    model,
    model_name: str,
    condition: str,
    sample,
    max_new_tokens: int,
    prompt_placement: str,
) -> dict[str, Any]:
    system_prompt, user_prompt = build_conditioned_prompts(condition, sample, prompt_placement)
    rendered = render_chat(tokenizer, system_prompt, user_prompt)
    started = datetime.now(timezone.utc)
    raw_output = generate(tokenizer, model, rendered, max_new_tokens=max_new_tokens)
    ended = datetime.now(timezone.utc)
    return build_row(
        model_name,
        condition,
        sample,
        system_prompt,
        user_prompt,
        rendered,
        raw_output,
        max_new_tokens,
        prompt_placement,
        started,
        ended,
    )


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--counts", default=None)
    parser.add_argument("--counts-file", default=None)
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of prompts to generate together. Deterministic decoding is preserved.",
    )
    parser.add_argument(
        "--prompt-placement",
        default="system",
        choices=["system", "task_prefix", "task_suffix"],
        help="Place condition text in the system role or inside the user/task prompt.",
    )
    args = parser.parse_args()

    if not args.counts and not args.counts_file:
        args.counts = "gsm8k:5,mmlu:5"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-02/open_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = resolve_counts(args.counts, args.counts_file)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    validate_conditions(conditions)
    validate_prompt_placement(args.prompt_placement)

    samples = load_samples(counts)
    config = {
        "experiment": "EXP-02",
        "runner": "run_open",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "counts": counts,
        "conditions": conditions,
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
        "cache_dir": args.cache_dir,
        "prompt_placement": args.prompt_placement,
    }
    write_json(out_dir / "config.json", config)
    write_samples_manifest(out_dir, samples)

    tokenizer, model = load_hf_model(args.model, args.cache_dir)

    rows = []
    raw_path = out_dir / "raw_outputs.jsonl"
    total = expected_rows(counts, len(conditions))
    index = 0
    for condition in conditions:
        batch: list[tuple[Any, str, str, str]] = []
        for sample in samples:
            system_prompt, user_prompt = build_conditioned_prompts(condition, sample, args.prompt_placement)
            rendered = render_chat(tokenizer, system_prompt, user_prompt)
            batch.append((sample, system_prompt, user_prompt, rendered))
            if len(batch) < max(1, args.batch_size):
                continue

            start_index = index + 1
            index += len(batch)
            end_index = index
            label_sample = batch[0][0]
            print(
                f"[{start_index}-{end_index}/{total}] {args.model} {condition} "
                f"{label_sample.dataset}... batch={len(batch)}",
                flush=True,
            )
            started = datetime.now(timezone.utc)
            raw_outputs = generate_batch(
                tokenizer,
                model,
                [item[3] for item in batch],
                max_new_tokens=args.max_new_tokens,
            )
            ended = datetime.now(timezone.utc)
            for (sample, system_prompt, user_prompt, rendered), raw_output in zip(batch, raw_outputs, strict=True):
                row = build_row(
                    args.model,
                    condition,
                    sample,
                    system_prompt,
                    user_prompt,
                    rendered,
                    raw_output,
                    args.max_new_tokens,
                    args.prompt_placement,
                    started,
                    ended,
                )
                row["run_id"] = run_id
                rows.append(row)
                append_jsonl(raw_path, row)
            batch = []

        if batch:
            start_index = index + 1
            index += len(batch)
            end_index = index
            label_sample = batch[0][0]
            print(
                f"[{start_index}-{end_index}/{total}] {args.model} {condition} "
                f"{label_sample.dataset}... batch={len(batch)}",
                flush=True,
            )
            started = datetime.now(timezone.utc)
            raw_outputs = generate_batch(
                tokenizer,
                model,
                [item[3] for item in batch],
                max_new_tokens=args.max_new_tokens,
            )
            ended = datetime.now(timezone.utc)
            for (sample, system_prompt, user_prompt, rendered), raw_output in zip(batch, raw_outputs, strict=True):
                row = build_row(
                    args.model,
                    condition,
                    sample,
                    system_prompt,
                    user_prompt,
                    rendered,
                    raw_output,
                    args.max_new_tokens,
                    args.prompt_placement,
                    started,
                    ended,
                )
                row["run_id"] = run_id
                rows.append(row)
                append_jsonl(raw_path, row)

    metrics = finalize_run(out_dir, rows)
    print(f"EXP-02 open-model run complete: {out_dir} ({total_samples(counts)} samples x {len(conditions)} conditions)")
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
