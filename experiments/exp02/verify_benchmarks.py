#!/usr/bin/env python3
"""Load-only smoke: verify all benchmark loaders without calling models."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from core.sample_loading import load_counts_file, load_samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts-file", default="configs/counts_smoke.json")
    args = parser.parse_args()

    counts = load_counts_file(Path(args.counts_file))
    samples = load_samples(counts)
    by_dataset = Counter(sample.dataset for sample in samples)

    print(f"Profile: {args.counts_file}")
    print(f"Requested: {counts}")
    print(f"Loaded {len(samples)} samples:")
    for dataset, count in sorted(by_dataset.items()):
        if dataset == "mmlu":
            expected = counts.get("mmlu_stratified", counts.get("mmlu", 0))
        else:
            expected = counts.get(dataset, 0)
        ok = "ok" if count == expected else "check"
        print(f"  {dataset}: {count} (expected {expected}, {ok})")

    missing = []
    for key, value in counts.items():
        if value <= 0:
            continue
        dataset_key = "mmlu" if key == "mmlu_stratified" else key
        if by_dataset.get(dataset_key, 0) == 0:
            missing.append(key)
    if missing:
        print(f"ERROR: no samples for: {missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
