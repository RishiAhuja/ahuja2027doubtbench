from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from .common import (
    PUBLISHED_PROMPT,
    binary_label,
    classification_metrics,
    json_sha256,
    load_source_split,
    paper_split_uid_map,
    parse_yes_no,
    record_policy,
    record_uid,
    slugify,
    write_json,
)
from .llm_eval import append_jsonl, generate_with_backoff, serialize_prompts


def stable_key(uid: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{uid}".encode()).hexdigest()


def source_domain(record: dict) -> str:
    release = record.get("release_metadata") or {}
    return str(release.get("domain") or "unknown")


def stream_paths(data_root: Path) -> list[Path]:
    paths = []
    for release_split in ("train", "validation", "test"):
        paths.extend(sorted((data_root / "streaming_chunks").glob(f"{release_split}-*.parquet")))
    if not paths:
        raise FileNotFoundError(f"No main streaming Parquet shards below {data_root}")
    return paths


def build_manifest(
    data_root: Path,
    horizons: list[int],
    per_stratum: int,
    seed: int,
) -> list[dict]:
    """Select fixed test conversations after verifying all requested horizons exist."""
    import pyarrow.parquet as parquet

    sources = load_source_split(data_root, "test", seed=seed)
    source_by_uid = {
        record_uid(record, "test", index): record for index, record in enumerate(sources)
    }
    uid_to_split = paper_split_uid_map(data_root, seed)
    selected_chunks: dict[str, dict[int, dict]] = defaultdict(dict)
    columns = ["conversation_uid", "chunk_timestamp", "final_verdict", "cumulative_text"]

    for path in stream_paths(data_root):
        parquet_file = parquet.ParquetFile(path)
        for batch in parquet_file.iter_batches(batch_size=8192, columns=columns):
            values = batch.to_pydict()
            for uid, timestamp, verdict, text in zip(
                values["conversation_uid"],
                values["chunk_timestamp"],
                values["final_verdict"],
                values["cumulative_text"],
            ):
                uid = str(uid)
                if uid_to_split.get(uid) != "test" or uid not in source_by_uid:
                    continue
                timestamp = int(timestamp)
                for horizon in horizons:
                    if timestamp > horizon:
                        continue
                    previous = selected_chunks[uid].get(horizon)
                    if previous is None or timestamp > previous["actual_timestamp"]:
                        selected_chunks[uid][horizon] = {
                            "actual_timestamp": timestamp,
                            "local_label": 1 if str(verdict).upper() == "YES" else 0,
                            "cumulative_text": str(text or ""),
                        }

    strata: dict[tuple[str, int], list[str]] = defaultdict(list)
    for uid, record in source_by_uid.items():
        if all(horizon in selected_chunks.get(uid, {}) for horizon in horizons):
            strata[(source_domain(record), binary_label(record))].append(uid)

    chosen: list[str] = []
    for stratum in sorted(strata):
        candidates = sorted(strata[stratum], key=lambda uid: stable_key(uid, seed))
        if len(candidates) < per_stratum:
            raise RuntimeError(
                f"Stratum {stratum} has {len(candidates)} eligible conversations; "
                f"need {per_stratum}"
            )
        chosen.extend(candidates[:per_stratum])

    expected_strata = 20
    if len(strata) != expected_strata:
        raise RuntimeError(f"Expected {expected_strata} domain/label strata, found {len(strata)}")

    manifest = []
    for uid in sorted(chosen, key=lambda value: stable_key(value, seed)):
        record = source_by_uid[uid]
        manifest.append(
            {
                "sample_id": uid,
                "domain": source_domain(record),
                "eventual_label": binary_label(record),
                "policy": record_policy(record),
                "horizons": {
                    str(horizon): selected_chunks[uid][horizon] for horizon in horizons
                },
            }
        )
    return manifest


def load_or_create_manifest(args) -> list[dict]:
    manifest_path = args.output_root / "llm_streaming" / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text())
        expected = {
            "seed": args.seed,
            "horizons_seconds": args.horizons,
            "per_domain_label_stratum": args.per_stratum,
        }
        if payload.get("protocol") != expected:
            raise RuntimeError("Existing streaming manifest uses a different protocol")
        return payload["conversations"]

    conversations = build_manifest(
        args.data_root, args.horizons, args.per_stratum, args.seed
    )
    write_json(
        manifest_path,
        {
            "protocol": {
                "seed": args.seed,
                "horizons_seconds": args.horizons,
                "per_domain_label_stratum": args.per_stratum,
            },
            "conversation_count": len(conversations),
            "generated_prompt_count_per_model": len(conversations) * len(args.horizons),
            "full_transcript_rows_reused_per_model": len(conversations),
            "conversations": conversations,
        },
    )
    return conversations


def completed_keys(path: Path) -> set[tuple[str, str]]:
    keys = set()
    if not path.exists():
        return keys
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                keys.add((str(row["sample_id"]), str(row["horizon"])))
            except (json.JSONDecodeError, KeyError):
                continue
    return keys


def load_static_rows(static_path: Path, wanted: set[str]) -> dict[str, dict]:
    result = {}
    with static_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            uid = str(row.get("sample_id"))
            if row.get("split") == "test" and uid in wanted:
                result[uid] = row
    if set(result) != wanted:
        raise RuntimeError(
            f"Static reuse expected {len(wanted)} test rows, found {len(result)}"
        )
    return result


def render_prompt(item: dict, horizon: int) -> str:
    chunk = item["horizons"][str(horizon)]
    return PUBLISHED_PROMPT.format(
        policy_text=item["policy"], transcript_text=chunk["cumulative_text"]
    )


def bootstrap_ci(labels: list[int], predictions: list[int], seed: int, samples: int = 1000) -> dict:
    labels_array = np.asarray(labels, dtype=np.int8)
    predictions_array = np.asarray(predictions, dtype=np.int8)
    rng = np.random.default_rng(seed)
    values = {name: [] for name in ("accuracy", "precision", "recall", "f1")}
    for _ in range(samples):
        index = rng.integers(0, len(labels_array), len(labels_array))
        y = labels_array[index]
        p = predictions_array[index]
        tp = int(np.sum((y == 1) & (p == 1)))
        fp = int(np.sum((y == 0) & (p == 1)))
        fn = int(np.sum((y == 1) & (p == 0)))
        values["accuracy"].append(float(np.mean(y == p)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        values["precision"].append(precision)
        values["recall"].append(recall)
        values["f1"].append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return {
        name: {
            "low": float(np.percentile(metric_values, 2.5)),
            "high": float(np.percentile(metric_values, 97.5)),
        }
        for name, metric_values in values.items()
    }


def aggregate(raw_path: Path, manifest: list[dict], args) -> dict:
    rows = []
    with raw_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    by_key = {(str(row["sample_id"]), str(row["horizon"])): row for row in rows}
    expected_horizons = [str(value) for value in args.horizons] + ["full"]
    expected = len(manifest) * len(expected_horizons)
    if len(by_key) != expected:
        raise RuntimeError(f"Expected {expected} unique trajectory rows, found {len(by_key)}")

    result = {
        "model": args.model,
        "protocol": {
            "conversation_count": len(manifest),
            "generated_horizons_seconds": args.horizons,
            "full_transcript_reused_from_static": True,
            "conversation_stratification": "100 per domain x eventual-label cell",
            "prompt": "published_gemma_zero_shot_policy_conditioned",
            "prompt_format": args.prompt_format,
            "max_input_tokens": args.max_input_tokens,
            "max_new_tokens": args.max_new_tokens,
            "temperature": args.temperature,
            "seed": args.seed,
            "confidence_intervals": "conversation bootstrap, 1000 resamples, 95% percentile",
        },
        "horizons": {},
    }
    for horizon_index, horizon in enumerate(expected_horizons):
        ordered = [by_key[(item["sample_id"], horizon)] for item in manifest]
        labels = [int(row["local_label"]) for row in ordered]
        predictions = [int(row["prediction"]) for row in ordered]
        metrics = classification_metrics(labels, predictions)
        metrics["bootstrap_95_ci"] = bootstrap_ci(
            labels, predictions, args.seed + horizon_index
        )
        metrics["eventual_fraud_view"] = classification_metrics(
            [int(row["eventual_label"]) for row in ordered], predictions
        )
        result["horizons"][horizon] = metrics

    trajectories = []
    for item in manifest:
        predictions = [
            int(by_key[(item["sample_id"], horizon)]["prediction"])
            for horizon in expected_horizons
        ]
        first_positive = next(
            (
                int(horizon)
                for horizon, prediction in zip(expected_horizons[:-1], predictions[:-1])
                if prediction == 1
            ),
            None,
        )
        trajectories.append(
            {
                "sample_id": item["sample_id"],
                "eventual_label": int(item["eventual_label"]),
                "predictions": predictions,
                "first_positive_horizon": first_positive,
                "transition_count": sum(
                    left != right for left, right in zip(predictions, predictions[1:])
                ),
            }
        )
    fraud = [row for row in trajectories if row["eventual_label"] == 1]
    benign = [row for row in trajectories if row["eventual_label"] == 0]
    detected = [row for row in fraud if row["first_positive_horizon"] is not None]
    false_alerted = [row for row in benign if row["first_positive_horizon"] is not None]
    result["trajectory"] = {
        "eventual_fraud_conversations": len(fraud),
        "eventual_benign_conversations": len(benign),
        "eventual_fraud_detected_by_horizon": {
            str(horizon): sum(
                row["first_positive_horizon"] is not None
                and row["first_positive_horizon"] <= horizon
                for row in fraud
            )
            / len(fraud)
            for horizon in args.horizons
        },
        "median_first_positive_horizon_seconds": float(
            np.median([row["first_positive_horizon"] for row in detected])
        )
        if detected
        else None,
        "benign_ever_false_alerted_rate": len(false_alerted) / len(benign),
        "any_prediction_flip_rate": sum(row["transition_count"] > 0 for row in trajectories)
        / len(trajectories),
        "mean_prediction_transitions": float(
            np.mean([row["transition_count"] for row in trajectories])
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact-LLM streaming trajectory evaluation")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--horizons", type=int, nargs="+", default=[15, 30, 60, 90])
    parser.add_argument("--per-stratum", type=int, default=100)
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

    manifest = load_or_create_manifest(args)
    run_dir = args.output_root / "llm_streaming" / slugify(args.model)
    run_dir.mkdir(parents=True, exist_ok=True)
    if (run_dir / "COMPLETE.json").exists():
        print(f"Already complete: {run_dir}", flush=True)
        return
    raw_path = run_dir / "raw_outputs.jsonl"
    done = completed_keys(raw_path)
    wanted = {item["sample_id"] for item in manifest}
    static_path = args.output_root / "llm" / slugify(args.model) / "raw_outputs.jsonl"
    static_rows = load_static_rows(static_path, wanted)

    reused_rows = []
    for item in manifest:
        uid = item["sample_id"]
        if (uid, "full") in done:
            continue
        static = static_rows[uid]
        reused_rows.append(
            {
                "model": args.model,
                "sample_id": uid,
                "domain": item["domain"],
                "horizon": "full",
                "actual_timestamp": None,
                "local_label": int(item["eventual_label"]),
                "eventual_label": int(item["eventual_label"]),
                "prediction": int(static["prediction"]),
                "prediction_text": static["prediction_text"],
                "confidence": static["confidence"],
                "parser": static["parser"],
                "response": static["response"],
                "prompt_sha256": static["prompt_sha256"],
                "seconds_per_item_in_batch": static.get("seconds_per_item_in_batch"),
                "reused_from_static": True,
            }
        )
    if reused_rows:
        append_jsonl(raw_path, reused_rows)

    pending = []
    done = completed_keys(raw_path)
    for horizon in args.horizons:
        for item in manifest:
            key = (item["sample_id"], str(horizon))
            if key not in done:
                pending.append((item, horizon, render_prompt(item, horizon)))
    print(
        f"{args.model}: complete={len(manifest) * (len(args.horizons) + 1) - len(pending)} "
        f"pending_generated={len(pending)} total={len(manifest) * (len(args.horizons) + 1)}",
        flush=True,
    )

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, token=token, trust_remote_code=args.trust_remote_code
    )
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

    started = time.time()
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        prompts = [row[2] for row in batch]
        serialized = serialize_prompts(tokenizer, prompts, args.prompt_format, args.model)
        batch_started = time.time()
        responses = generate_with_backoff(model, tokenizer, serialized, args)
        elapsed = time.time() - batch_started
        output_rows = []
        for (item, horizon, prompt), response in zip(batch, responses):
            prediction_text, confidence, parser_name = parse_yes_no(response)
            chunk = item["horizons"][str(horizon)]
            output_rows.append(
                {
                    "model": args.model,
                    "sample_id": item["sample_id"],
                    "domain": item["domain"],
                    "horizon": str(horizon),
                    "actual_timestamp": int(chunk["actual_timestamp"]),
                    "local_label": int(chunk["local_label"]),
                    "eventual_label": int(item["eventual_label"]),
                    "prediction": 1 if prediction_text == "YES" else 0,
                    "prediction_text": prediction_text,
                    "confidence": confidence,
                    "parser": parser_name,
                    "response": response,
                    "prompt_sha256": json_sha256(prompt),
                    "seconds_per_item_in_batch": elapsed / len(batch),
                    "reused_from_static": False,
                }
            )
        append_jsonl(raw_path, output_rows)
        processed = min(start + len(batch), len(pending))
        rate = processed / max(time.time() - started, 1e-6)
        print(f"{args.model}: {processed}/{len(pending)} generated, {rate:.2f} rows/s", flush=True)

    metrics = aggregate(raw_path, manifest, args)
    write_json(run_dir / "metrics.json", metrics)
    write_json(
        run_dir / "COMPLETE.json",
        {
            "status": "complete",
            "model": args.model,
            "conversations": len(manifest),
            "rows": len(manifest) * (len(args.horizons) + 1),
        },
    )
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
