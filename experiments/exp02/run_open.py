#!/usr/bin/env python3
"""Run EXP-02 on local/open Hugging Face causal language models."""

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

    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir, trust_remote_code=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token

    kwargs = {
        "cache_dir": cache_dir,
        "trust_remote_code": True,
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
    import torch

    encoded = tokenizer(prompt, return_tensors="pt")
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.inference_mode():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = output_ids[0][encoded["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


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
        "rendered_prompt": rendered,
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
        for sample in samples:
            index += 1
            print(f"[{index}/{total}] {args.model} {condition} {sample.dataset} {sample.sample_id}", flush=True)
            row = run_one(
                tokenizer,
                model,
                args.model,
                condition,
                sample,
                args.max_new_tokens,
                args.prompt_placement,
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
