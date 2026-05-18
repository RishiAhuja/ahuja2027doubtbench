#!/usr/bin/env python3
"""Run EXP-02 on local/open Hugging Face causal language models."""

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
from core.metrics import exp02_metrics
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


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def run_one(tokenizer, model, model_name: str, condition: str, sample, max_new_tokens: int):
    system_prompt = PROMPT_BY_CONDITION[condition].text
    user_prompt = build_user_prompt(sample)
    rendered = render_chat(tokenizer, system_prompt, user_prompt)
    started = datetime.now(timezone.utc)
    raw_output = generate(tokenizer, model, rendered, max_new_tokens=max_new_tokens)
    ended = datetime.now(timezone.utc)
    parsed = parse_answer(sample.dataset, raw_output)
    score = score_prediction(sample.dataset, parsed, sample.gold)
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
        },
        "raw_output": raw_output,
        "parsed_answer": parsed,
        "gold": sample.gold,
        "score": score,
        "error": None,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--counts", default="gsm8k:5,mmlu:5")
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--out", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/EXP-02/open_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = parse_counts(args.counts)
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    unknown = [condition for condition in conditions if condition not in PROMPT_BY_CONDITION]
    if unknown:
        raise SystemExit(f"Unknown conditions: {', '.join(unknown)}")

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
    }
    write_json(out_dir / "config.json", config)
    write_jsonl(out_dir / "samples.jsonl", [sample_to_dict(sample) for sample in samples])

    tokenizer, model = load_hf_model(args.model, args.cache_dir)

    rows = []
    raw_path = out_dir / "raw_outputs.jsonl"
    total = len(samples) * len(conditions)
    index = 0
    for condition in conditions:
        for sample in samples:
            index += 1
            print(f"[{index}/{total}] {args.model} {condition} {sample.dataset} {sample.sample_id}", flush=True)
            row = run_one(tokenizer, model, args.model, condition, sample, args.max_new_tokens)
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

    print(f"EXP-02 open-model run complete: {out_dir}")
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
