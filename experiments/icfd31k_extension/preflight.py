from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

from .common import EXPECTED_SOURCE_COUNTS, load_source_split


GPU_MODULES = ("accelerate", "datasets", "numpy", "pyarrow", "sklearn", "scipy", "torch", "transformers", "zstandard")
CPU_MODULES = ("joblib", "numpy", "sklearn", "scipy", "zstandard")
MODELS = (
    "google/gemma-1.1-2b-it",
    "google/gemma-3-1b-it",
    "meta-llama/Llama-3.2-1B-Instruct",
    "ibm-granite/granite-4.0-1b",
    "Qwen/Qwen3-1.7B",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "google/mobilebert-uncased",
    "distilbert/distilbert-base-uncased",
    "answerdotai/ModernBERT-base",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail-fast ICFD-31k suite validation")
    parser.add_argument("--mode", choices=["gpu", "cpu"], required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--check-model-access", action="store_true")
    args = parser.parse_args()

    missing = []
    versions = {}
    for module_name in GPU_MODULES if args.mode == "gpu" else CPU_MODULES:
        try:
            module = importlib.import_module(module_name)
            versions[module_name] = getattr(module, "__version__", "unknown")
        except ImportError:
            missing.append(module_name)
    if missing:
        raise SystemExit(
            "Missing required Python modules: " + ", ".join(missing) +
            ". Install experiments/icfd31k_extension/requirements.txt before qsub."
        )

    source_rows = {split: load_source_split(args.data_root, split) for split in EXPECTED_SOURCE_COUNTS}
    counts = {split: len(rows) for split, rows in source_rows.items()}
    source_positive_counts = {
        split: sum(str(row.get("final_verdict", "NO")).upper() == "YES" for row in rows)
        for split, rows in source_rows.items()
    }
    streaming_counts = {}
    if args.mode == "gpu":
        import pyarrow.parquet as parquet
        for split in EXPECTED_SOURCE_COUNTS:
            paths = sorted((args.data_root / "streaming_chunks").glob(f"{split}-*.parquet"))
            if not paths:
                raise SystemExit(f"Missing streaming parquet shards for {split}")
            streaming_counts[split] = sum(parquet.ParquetFile(path).metadata.num_rows for path in paths)

    access = {}
    if args.check_model_access:
        from huggingface_hub import HfApi
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        api = HfApi(token=token)
        for model in MODELS:
            try:
                access[model] = {"ok": True, "files": len(api.list_repo_files(model))}
            except Exception as error:
                access[model] = {"ok": False, "error": str(error).splitlines()[0]}
        failures = [model for model, result in access.items() if not result["ok"]]
        if failures:
            print(json.dumps({"versions": versions, "source_counts": counts, "source_positive_counts": source_positive_counts, "streaming_counts": streaming_counts, "access": access}, indent=2))
            raise SystemExit("Model access failed: " + ", ".join(failures))

    print(json.dumps({"python": sys.version, "versions": versions, "source_counts": counts, "source_positive_counts": source_positive_counts, "streaming_counts": streaming_counts, "access": access}, indent=2))


if __name__ == "__main__":
    main()
