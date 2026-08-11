"""Metrics helpers for benchmark experiments."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any


def accuracy(rows: list[dict[str, Any]]) -> float | None:
    scored = [row for row in rows if row.get("score") is not None]
    if not scored:
        return None
    return mean(1.0 if row["score"] else 0.0 for row in scored)


def group_rows(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple, list[dict[str, Any]]]:
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    return dict(groups)


def exp02_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model_dataset_condition = []
    grouped = group_rows(rows, ["model", "dataset", "condition"])
    for (model, dataset, condition), group in sorted(grouped.items()):
        parse_failures = sum(1 for row in group if not row.get("parsed_answer"))
        by_model_dataset_condition.append(
            {
                "model": model,
                "dataset": dataset,
                "condition": condition,
                "n": len(group),
                "accuracy": accuracy(group),
                "parse_failure_rate": parse_failures / len(group) if group else None,
            }
        )

    deltas = []
    by_model_dataset = group_rows(by_model_dataset_condition, ["model", "dataset"])
    for (model, dataset), summaries in sorted(by_model_dataset.items()):
        by_condition = {row["condition"]: row for row in summaries}
        baseline = by_condition.get("baseline", {}).get("accuracy")
        if baseline is None:
            continue
        melancholic = by_condition.get("melancholic", {}).get("accuracy")
        neg_cap = by_condition.get("negative_capability", {}).get("accuracy")
        delta_mel = None if melancholic is None else melancholic - baseline
        delta_neg = None if neg_cap is None else neg_cap - baseline
        confound_excess = (
            None
            if delta_mel is None or delta_neg is None
            else abs(delta_neg) - abs(delta_mel)
        )
        deltas.append(
            {
                "model": model,
                "dataset": dataset,
                "baseline_accuracy": baseline,
                "melancholic_accuracy": melancholic,
                "negative_capability_accuracy": neg_cap,
                "delta_melancholic": delta_mel,
                "delta_negative_capability": delta_neg,
                "confound_excess_abs_delta": confound_excess,
            }
        )

    return {
        "by_model_dataset_condition": by_model_dataset_condition,
        "deltas": deltas,
    }
