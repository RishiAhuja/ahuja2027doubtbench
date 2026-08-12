from __future__ import annotations

import argparse
import time
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np

from .common import classification_metrics, paper_split_uid_map, write_json


MAIN_RELEASE_SPLITS = ("train", "validation", "test")


def parquet_paths(data_root: Path, cross_domain: bool = False) -> list[Path]:
    root = data_root / "streaming_chunks"
    names = ("cross_domain",) if cross_domain else MAIN_RELEASE_SPLITS
    paths = [path for name in names for path in sorted(root.glob(f"{name}-*.parquet"))]
    if not paths:
        raise FileNotFoundError(f"No streaming Parquet shards found below {root}")
    return paths


def iter_batches(
    paths: list[Path],
    target_split: str,
    uid_to_split: dict[str, str],
    batch_size: int,
):
    import pyarrow.parquet as parquet

    columns = ["conversation_uid", "chunk_timestamp", "final_verdict", "cumulative_text"]
    for path in paths:
        parquet_file = parquet.ParquetFile(path)
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=columns):
            values = batch.to_pydict()
            if target_split == "cross_domain":
                keep = range(len(values["conversation_uid"]))
            else:
                keep = (
                    index
                    for index, uid in enumerate(values["conversation_uid"])
                    if uid_to_split.get(str(uid)) == target_split
                )
            selected = list(keep)
            if not selected:
                continue
            yield (
                [str(values["cumulative_text"][index] or "") for index in selected],
                np.asarray(
                    [1 if str(values["final_verdict"][index]).upper() == "YES" else 0 for index in selected],
                    dtype=np.int8,
                ),
                [str(values["conversation_uid"][index]) for index in selected],
                np.asarray([int(values["chunk_timestamp"][index]) for index in selected], dtype=np.int32),
            )


def evaluate(
    classifier,
    vectorizer,
    paths: list[Path],
    split: str,
    uid_to_split: dict[str, str],
    batch_size: int,
) -> dict:
    labels: list[int] = []
    predictions: list[int] = []
    conversations: dict[str, dict] = defaultdict(
        lambda: {"label": 0, "last_timestamp": 0, "first_positive_timestamp": None}
    )
    started = time.time()
    for batch_index, (texts, batch_labels, uids, timestamps) in enumerate(
        iter_batches(paths, split, uid_to_split, batch_size), start=1
    ):
        batch_predictions = classifier.predict(vectorizer.transform(texts)).astype(np.int8)
        labels.extend(batch_labels.tolist())
        predictions.extend(batch_predictions.tolist())
        for uid, label, prediction, timestamp in zip(
            uids, batch_labels.tolist(), batch_predictions.tolist(), timestamps.tolist()
        ):
            item = conversations[uid]
            item["label"] = label
            item["last_timestamp"] = max(item["last_timestamp"], timestamp)
            if prediction == 1 and item["first_positive_timestamp"] is None:
                item["first_positive_timestamp"] = timestamp
        if batch_index % 25 == 0:
            print(f"evaluate split={split} chunks={len(labels)}", flush=True)

    fraud = [item for item in conversations.values() if item["label"] == 1]
    normal = [item for item in conversations.values() if item["label"] == 0]
    detected = [item for item in fraud if item["first_positive_timestamp"] is not None]
    false_alerted = [item for item in normal if item["first_positive_timestamp"] is not None]
    detection_times = [item["first_positive_timestamp"] for item in detected]
    detection_fractions = [
        item["first_positive_timestamp"] / max(1, item["last_timestamp"]) for item in detected
    ]
    return {
        "chunk_metrics": classification_metrics(labels, predictions),
        "conversation_metrics": {
            "conversations": len(conversations),
            "fraud_conversations": len(fraud),
            "normal_conversations": len(normal),
            "fraud_ever_detected_rate": len(detected) / len(fraud) if fraud else 0.0,
            "normal_ever_false_alerted_rate": len(false_alerted) / len(normal) if normal else 0.0,
            "median_first_detection_seconds": float(np.median(detection_times)) if detection_times else None,
            "median_detection_fraction": float(np.median(detection_fractions)) if detection_fractions else None,
        },
        "seconds": time.time() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Online classical baseline for ICFD-31k streaming chunks")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--features", type=int, default=2**20)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--alpha", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier

    run_dir = args.output_root / "classical_streaming"
    run_dir.mkdir(parents=True, exist_ok=True)
    if (run_dir / "COMPLETE.json").exists():
        print(f"Already complete: {run_dir}")
        return

    uid_to_split = paper_split_uid_map(args.data_root, args.seed)
    main_paths = parquet_paths(args.data_root)
    cross_paths = parquet_paths(args.data_root, cross_domain=True)
    vectorizer = HashingVectorizer(
        n_features=args.features,
        alternate_sign=False,
        norm="l2",
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        dtype=np.float32,
    )
    classifier = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=args.alpha,
        random_state=args.seed,
        average=True,
    )

    training_started = time.time()
    rows_seen = 0
    updates = 0
    rng = np.random.default_rng(args.seed)
    for epoch in range(args.epochs):
        for texts, labels, _, _ in iter_batches(
            main_paths, "train", uid_to_split, args.batch_size
        ):
            order = rng.permutation(len(labels))
            matrix = vectorizer.transform([texts[index] for index in order])
            classifier.partial_fit(matrix, labels[order], classes=np.asarray([0, 1], dtype=np.int8))
            rows_seen += len(labels)
            updates += 1
            if updates % 25 == 0:
                print(
                    f"train epoch={epoch + 1}/{args.epochs} rows_seen={rows_seen} updates={updates}",
                    flush=True,
                )

    results = {
        "model": "word_bigram_hashing__online_logistic_regression",
        "protocol": {
            "conversation_disjoint_split": True,
            "features": args.features,
            "batch_size": args.batch_size,
            "epochs": args.epochs,
            "alpha": args.alpha,
            "seed": args.seed,
            "chunk_interval_seconds": 3,
        },
        "training": {
            "rows_seen_including_epochs": rows_seen,
            "updates": updates,
            "seconds": time.time() - training_started,
        },
    }
    for split in ("validation", "test"):
        results[split] = evaluate(
            classifier, vectorizer, main_paths, split, uid_to_split, args.batch_size
        )
    results["cross_domain"] = evaluate(
        classifier, vectorizer, cross_paths, "cross_domain", uid_to_split, args.batch_size
    )

    joblib.dump(classifier, run_dir / "classifier.joblib", compress=3)
    joblib.dump(vectorizer, run_dir / "vectorizer.joblib", compress=3)
    write_json(run_dir / "metrics.json", results)
    write_json(run_dir / "COMPLETE.json", {"status": "complete", "model": results["model"]})
    print(f"Streaming classical complete: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
