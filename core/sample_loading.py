"""Load benchmark samples from count profiles (JSON or CLI)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.benchmarks import (
    BenchmarkSample,
    load_bigbench,
    load_creative,
    load_gsm8k,
    load_math_level3,
    load_mmlu,
    load_mmlu_stratified,
    load_triviaqa,
)


def load_counts_file(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Counts file must be a JSON object: {path}")
    return {str(key): int(value) for key, value in payload.items() if int(value) > 0}


def parse_counts_cli(value: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for part in value.split(","):
        if not part.strip():
            continue
        key, raw_count = part.split(":", 1)
        result[key.strip()] = int(raw_count)
    return result


def total_samples(counts: dict[str, int]) -> int:
    return sum(counts.values())


def expected_rows(counts: dict[str, int], n_conditions: int) -> int:
    return total_samples(counts) * n_conditions


def load_samples(counts: dict[str, int]) -> list[BenchmarkSample]:
    samples: list[BenchmarkSample] = []
    if counts.get("gsm8k", 0):
        samples.extend(load_gsm8k(counts["gsm8k"]))
    mmlu_n = counts.get("mmlu_stratified", 0) or counts.get("mmlu", 0)
    if mmlu_n:
        if counts.get("mmlu_stratified", 0):
            samples.extend(load_mmlu_stratified(mmlu_n))
        else:
            samples.extend(load_mmlu(mmlu_n))
    if counts.get("math", 0):
        samples.extend(load_math_level3(counts["math"]))
    if counts.get("triviaqa", 0):
        samples.extend(load_triviaqa(counts["triviaqa"]))
    if counts.get("bigbench", 0):
        samples.extend(load_bigbench(counts["bigbench"]))
    if counts.get("creative", 0):
        samples.extend(load_creative(counts["creative"]))
    return samples


def counts_summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def resolve_counts(
    counts: str | None = None,
    counts_file: str | Path | None = None,
) -> dict[str, int]:
    if counts_file:
        return load_counts_file(Path(counts_file))
    if counts:
        return parse_counts_cli(counts)
    raise ValueError("Provide --counts or --counts-file")
