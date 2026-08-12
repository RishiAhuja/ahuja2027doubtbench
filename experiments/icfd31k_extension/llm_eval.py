from __future__ import annotations

import argparse
import gc
import json
import os
import random
import time
from pathlib import Path

from .common import (
    binary_label,
    classification_metrics,
    json_sha256,
    load_source_split,
    parse_yes_no,
    published_prompt,
    record_uid,
    slugify,
    write_json,
)


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def completed_keys(path: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if not path.exists():
        return keys
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                keys.add((row["split"], row["sample_id"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return keys


def serialize_prompts(tokenizer, prompts: list[str], prompt_format: str, model_name: str) -> list[str]:
    if prompt_format == "raw" or not getattr(tokenizer, "chat_template", None):
        return prompts
    rendered = []
    for prompt in prompts:
        kwargs = {"tokenize": False, "add_generation_prompt": True}
        if "qwen3" in model_name.lower():
            kwargs["enable_thinking"] = False
        try:
            text = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], **kwargs)
        except TypeError:
            kwargs.pop("enable_thinking", None)
            text = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], **kwargs)
        rendered.append(text)
    return rendered


def generate_batch(model, tokenizer, texts: list[str], args) -> list[str]:
    import torch

    encoded = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=args.max_input_tokens,
    ).to(model.device)
    input_width = encoded["input_ids"].shape[1]
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=args.max_new_tokens,
            do_sample=True,
            temperature=args.temperature,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.batch_decode(generated[:, input_width:], skip_special_tokens=True)


def generate_with_backoff(model, tokenizer, texts: list[str], args) -> list[str]:
    import torch

    try:
        return generate_batch(model, tokenizer, texts, args)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        if len(texts) == 1:
            raise
        midpoint = len(texts) // 2
        print(f"OOM at batch={len(texts)}; retrying as {midpoint}+{len(texts)-midpoint}", flush=True)
        return generate_with_backoff(model, tokenizer, texts[:midpoint], args) + generate_with_backoff(
            model, tokenizer, texts[midpoint:], args
        )


def evaluate_split(model, tokenizer, records: list[dict], split: str, raw_path: Path, args) -> None:
    done = completed_keys(raw_path)
    pending = []
    for index, record in enumerate(records):
        uid = record_uid(record, split, index)
        if (split, uid) not in done:
            prompt = published_prompt(record)
            pending.append((uid, binary_label(record), prompt))

    print(f"{split}: complete={len(records)-len(pending)} pending={len(pending)} total={len(records)}", flush=True)
    started = time.time()
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        prompts = [item[2] for item in batch]
        serialized = serialize_prompts(tokenizer, prompts, args.prompt_format, args.model)
        batch_started = time.time()
        responses = generate_with_backoff(model, tokenizer, serialized, args)
        elapsed = time.time() - batch_started
        rows = []
        for (uid, label, prompt), response in zip(batch, responses):
            prediction_text, confidence, parser = parse_yes_no(response)
            rows.append(
                {
                    "model": args.model,
                    "split": split,
                    "sample_id": uid,
                    "true_label": label,
                    "prediction": 1 if prediction_text == "YES" else 0,
                    "prediction_text": prediction_text,
                    "confidence": confidence,
                    "parser": parser,
                    "response": response,
                    "prompt_sha256": json_sha256(prompt),
                    "seconds_per_item_in_batch": elapsed / len(batch),
                }
            )
        append_jsonl(raw_path, rows)
        processed = min(start + len(batch), len(pending))
        rate = processed / max(time.time() - started, 1e-6)
        print(f"{split}: {processed}/{len(pending)} new, {rate:.2f} samples/s", flush=True)


def aggregate(raw_path: Path, args, expected: dict[str, int]) -> dict:
    rows = []
    with raw_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    result = {
        "model": args.model,
        "protocol": {
            "prompt": "published_gemma_zero_shot_policy_conditioned",
            "prompt_format": args.prompt_format,
            "max_input_tokens": args.max_input_tokens,
            "max_new_tokens": args.max_new_tokens,
            "temperature": args.temperature,
            "do_sample": True,
            "seed": args.seed,
        },
        "splits": {},
    }
    for split, expected_count in expected.items():
        split_rows = [row for row in rows if row["split"] == split]
        unique = {row["sample_id"]: row for row in split_rows}
        if len(unique) != expected_count:
            raise RuntimeError(f"{split}: expected {expected_count} unique rows, found {len(unique)}")
        ordered = list(unique.values())
        result["splits"][split] = classification_metrics(
            [row["true_label"] for row in ordered], [row["prediction"] for row in ordered]
        )
        result["splits"][split]["parser_counts"] = {
            parser: sum(row["parser"] == parser for row in ordered)
            for parser in sorted({row["parser"] for row in ordered})
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Batched, resumable ICFD-31k zero-shot evaluation")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--splits", nargs="+", default=["test", "cross_domain"])
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-input-tokens", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=150)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prompt-format", choices=["raw", "chat"], default="raw")
    parser.add_argument("--trust-remote-code", action="store_true")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    run_dir = args.output_root / "llm" / slugify(args.model)
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "raw_outputs.jsonl"
    expected = {}
    datasets = {}
    for split in args.splits:
        records = load_source_split(args.data_root, split)
        datasets[split] = records
        expected[split] = len(records)

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(args.model, token=token, trust_remote_code=args.trust_remote_code)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        token=token,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
        trust_remote_code=args.trust_remote_code,
    ).eval()

    write_json(run_dir / "config.json", vars(args) | {"data_root": str(args.data_root), "output_root": str(args.output_root)})
    for split, records in datasets.items():
        evaluate_split(model, tokenizer, records, split, raw_path, args)
    metrics = aggregate(raw_path, args, expected)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "COMPLETE.json", {"status": "complete", "expected": expected})
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()

