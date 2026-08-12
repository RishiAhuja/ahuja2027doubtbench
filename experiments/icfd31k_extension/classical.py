from __future__ import annotations

import argparse
import time
from pathlib import Path

import joblib
import numpy as np

from .common import binary_label, classification_metrics, load_source_split, transcript_to_text, write_json


def load_xy(data_root: Path, split: str) -> tuple[list[str], list[int]]:
    rows = load_source_split(data_root, split)
    return [transcript_to_text(row) for row in rows], [binary_label(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Classical ICFD-31k baselines")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-word-features", type=int, default=100_000)
    parser.add_argument("--max-char-features", type=int, default=150_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import scipy.sparse as sparse
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC

    run_dir = args.output_root / "classical"
    run_dir.mkdir(parents=True, exist_ok=True)
    if (run_dir / "COMPLETE.json").exists():
        print(f"Already complete: {run_dir}")
        return

    datasets = {split: load_xy(args.data_root, split) for split in ("train", "validation", "test", "cross_domain")}
    word = TfidfVectorizer(
        lowercase=True,
        sublinear_tf=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_features=args.max_word_features,
        dtype=np.float32,
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        lowercase=True,
        sublinear_tf=True,
        ngram_range=(3, 5),
        min_df=2,
        max_features=args.max_char_features,
        dtype=np.float32,
    )
    train_texts, train_labels = datasets["train"]
    started = time.time()
    train_word = word.fit_transform(train_texts)
    train_char = char.fit_transform(train_texts)
    features = {"word": train_word, "char": train_char, "word_char": sparse.hstack([train_word, train_char], format="csr")}
    transformed = {}
    for split in ("validation", "test", "cross_domain"):
        texts, _ = datasets[split]
        word_matrix = word.transform(texts)
        char_matrix = char.transform(texts)
        transformed[split] = {
            "word": word_matrix,
            "char": char_matrix,
            "word_char": sparse.hstack([word_matrix, char_matrix], format="csr"),
        }

    results = {"feature_seconds": time.time() - started, "models": {}}
    for feature_name, train_matrix in features.items():
        estimators = {
            "logistic_regression": LogisticRegression(
                solver="liblinear", max_iter=1_000, random_state=args.seed
            ),
            "linear_svm": LinearSVC(random_state=args.seed),
        }
        for classifier_name, estimator in estimators.items():
            name = f"{feature_name}__{classifier_name}"
            model_started = time.time()
            estimator.fit(train_matrix, train_labels)
            model_result = {"fit_seconds": time.time() - model_started}
            for split in ("validation", "test", "cross_domain"):
                predictions = estimator.predict(transformed[split][feature_name]).tolist()
                model_result[split] = classification_metrics(datasets[split][1], predictions)
            results["models"][name] = model_result
            joblib.dump(estimator, run_dir / f"{name}.joblib", compress=3)
            print(name, model_result["test"], flush=True)
    joblib.dump(word, run_dir / "word_vectorizer.joblib", compress=3)
    joblib.dump(char, run_dir / "char_vectorizer.joblib", compress=3)
    write_json(run_dir / "metrics.json", results)
    write_json(run_dir / "COMPLETE.json", {"status": "complete", "models": len(results["models"])})


if __name__ == "__main__":
    main()
