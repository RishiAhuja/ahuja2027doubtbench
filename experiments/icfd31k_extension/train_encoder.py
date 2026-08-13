from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

import numpy as np

from .common import (
    binary_label,
    classification_metrics,
    load_source_split,
    paper_split_uid_map,
    slugify,
    transcript_to_text,
    write_json,
)


def static_datasets(data_root: Path):
    from datasets import Dataset, DatasetDict

    result = {}
    for split in ("train", "validation", "test", "cross_domain"):
        rows = load_source_split(data_root, split)
        result[split] = Dataset.from_dict(
            {
                "text": [transcript_to_text(row) for row in rows],
                "labels": [binary_label(row) for row in rows],
            }
        )
    return DatasetDict(result)


def streaming_datasets(data_root: Path, seed: int = 42, num_workers: int = 8):
    from datasets import load_dataset

    main_paths = []
    for release_split in ("train", "validation", "test"):
        main_paths.extend(sorted((data_root / "streaming_chunks").glob(f"{release_split}-*.parquet")))
    cross_paths = sorted((data_root / "streaming_chunks").glob("cross_domain-*.parquet"))
    if not main_paths or not cross_paths:
        raise FileNotFoundError("Missing main or cross-domain streaming Parquet shards")
    dataset = load_dataset(
        "parquet",
        data_files={"main": [str(path) for path in main_paths], "cross_domain": [str(path) for path in cross_paths]},
    )
    uid_to_split = paper_split_uid_map(data_root, seed)

    def normalize(batch):
        return {
            "text": batch["cumulative_text"],
            "labels": [1 if str(value).upper() == "YES" else 0 for value in batch["final_verdict"]],
            "target_split": [uid_to_split.get(uid, "missing") for uid in batch["conversation_uid"]],
        }

    main = dataset["main"].map(
        normalize,
        batched=True,
        num_proc=max(1, num_workers),
        remove_columns=dataset["main"].column_names,
        desc="Assign paper conversation splits to streaming chunks",
    )
    missing = main.filter(lambda row: row["target_split"] == "missing", num_proc=max(1, num_workers))
    if len(missing):
        raise RuntimeError(f"Could not map {len(missing)} streaming chunks to a source conversation split")
    result = {
        split: main.filter(
            lambda row, expected=split: row["target_split"] == expected,
            num_proc=max(1, num_workers),
        ).remove_columns(["target_split"])
        for split in ("train", "validation", "test")
    }
    cross = dataset["cross_domain"].map(
        lambda batch: {
            "text": batch["cumulative_text"],
            "labels": [1 if str(value).upper() == "YES" else 0 for value in batch["final_verdict"]],
        },
        batched=True,
        num_proc=max(1, num_workers),
        remove_columns=dataset["cross_domain"].column_names,
        desc="Normalize cross-domain streaming chunks",
    )
    result["cross_domain"] = cross
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune compact encoders on ICFD-31k")
    parser.add_argument("--model", required=True)
    parser.add_argument("--task", choices=["static", "streaming"], required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--epochs", type=float, default=5.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--trust-remote-code", action="store_true")
    args = parser.parse_args()

    # The first MobileBERT runs showed substantial headroom on the 3g.40GB
    # H100 MIG slice.  Keep that completed protocol unchanged, but use the
    # requested 3x throughput batches for the two later encoder families.
    # TrainingArguments.auto_find_batch_size remains enabled below, so a model
    # that cannot fit the requested batch backs off instead of failing.
    throughput_batches = {
        "distilbert/distilbert-base-uncased": (192, 384),
        "answerdotai/ModernBERT-base": (96, 192),
    }
    if args.model in throughput_batches:
        args.batch_size, args.eval_batch_size = throughput_batches[args.model]
        print(
            f"Throughput batch override for {args.model}: "
            f"train={args.batch_size}, eval={args.eval_batch_size}",
            flush=True,
        )

    import torch
    from datasets import DatasetDict
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
        set_seed,
    )
    from transformers.trainer_utils import get_last_checkpoint

    set_seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    run_dir = args.output_root / "encoders" / slugify(args.model) / args.task
    run_dir.mkdir(parents=True, exist_ok=True)
    if (run_dir / "COMPLETE.json").exists():
        print(f"Already complete: {run_dir}")
        return

    raw = (
        static_datasets(args.data_root)
        if args.task == "static"
        else streaming_datasets(args.data_root, seed=args.seed, num_workers=args.num_workers)
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True, trust_remote_code=args.trust_remote_code)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=args.max_length)

    tokenized = DatasetDict()
    for split, dataset in raw.items():
        tokenized[split] = dataset.map(
            tokenize,
            batched=True,
            num_proc=max(1, args.num_workers),
            remove_columns=["text"],
            desc=f"Tokenize {split}",
        )

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        id2label={0: "NO", 1: "YES"},
        label2id={"NO": 0, "YES": 1},
        trust_remote_code=args.trust_remote_code,
    )

    def compute_metrics(prediction):
        predictions = np.argmax(prediction.predictions, axis=-1).tolist()
        full = classification_metrics(prediction.label_ids.tolist(), predictions)
        return {key: full[key] for key in ("accuracy", "precision", "recall", "f1")}

    kwargs = dict(
        output_dir=str(run_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        auto_find_batch_size=True,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_strategy="steps",
        logging_steps=100,
        bf16=True,
        tf32=True,
        dataloader_num_workers=args.num_workers,
        dataloader_pin_memory=True,
        report_to="none",
        seed=args.seed,
    )
    parameter_names = inspect.signature(TrainingArguments.__init__).parameters
    if "eval_strategy" in parameter_names:
        kwargs["eval_strategy"] = "epoch"
    else:
        kwargs["evaluation_strategy"] = "epoch"
    training_args = TrainingArguments(**kwargs)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=DataCollatorWithPadding(tokenizer, pad_to_multiple_of=8),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    # Resume interrupted PBS runs from their latest durable Trainer checkpoint.
    # A completed run is still skipped above via COMPLETE.json.
    last_checkpoint = get_last_checkpoint(training_args.output_dir)
    if last_checkpoint:
        print(f"Resuming from checkpoint: {last_checkpoint}", flush=True)
    train_result = trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(run_dir / "final_model"))
    tokenizer.save_pretrained(str(run_dir / "final_model"))

    metrics = {
        "model": args.model,
        "task": args.task,
        "protocol": {
            "max_length": args.max_length,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "warmup_ratio": args.warmup_ratio,
            "requested_batch_size": args.batch_size,
            "actual_batch_size": trainer.args.per_device_train_batch_size,
            "seed": args.seed,
        },
        "train": train_result.metrics,
        "validation": trainer.evaluate(tokenized["validation"], metric_key_prefix="validation"),
    }
    for split in ("test", "cross_domain"):
        prediction = trainer.predict(tokenized[split], metric_key_prefix=split)
        predicted_labels = np.argmax(prediction.predictions, axis=-1).tolist()
        metrics[split] = {
            **prediction.metrics,
            **classification_metrics(prediction.label_ids.tolist(), predicted_labels),
        }
        np.savez_compressed(
            run_dir / f"{split}_predictions.npz",
            labels=prediction.label_ids,
            logits=prediction.predictions,
        )
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "COMPLETE.json", {"status": "complete", "model": args.model, "task": args.task})


if __name__ == "__main__":
    main()
