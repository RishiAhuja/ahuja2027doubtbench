#!/usr/bin/env python3
"""Compare paired EXP-02 runs with system vs task prompt placement.

Inputs can be either a single model run directory containing `raw_outputs.jsonl`
or a run root with one child directory per model.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def find_run_dirs(root: Path) -> list[Path]:
    if (root / "raw_outputs.jsonl").exists():
        return [root]
    run_dirs = sorted(path.parent for path in root.glob("*/raw_outputs.jsonl"))
    if not run_dirs:
        raise FileNotFoundError(f"No raw_outputs.jsonl found under {root}")
    return run_dirs


def load_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "raw_outputs.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def load_run_root(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_dir in find_run_dirs(root):
        rows.extend(load_rows(run_dir))
    return rows


def accuracy(rows: list[dict[str, Any]]) -> float | None:
    scored = [row for row in rows if row.get("score") is not None]
    if not scored:
        return None
    return mean(1.0 if row["score"] else 0.0 for row in scored)


def placement_for_row(row: dict[str, Any], fallback: str) -> str:
    params = row.get("params") if isinstance(row.get("params"), dict) else {}
    return str(params.get("prompt_placement") or fallback)


def summarize(rows: list[dict[str, Any]], fallback_placement: str) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("dataset") == "creative":
            continue
        model = row.get("model", "")
        dataset = row.get("dataset", "")
        condition = row.get("condition", "")
        placement = placement_for_row(row, fallback_placement)
        groups[(model, dataset, condition, placement)].append(row)

    summaries: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for key, group in groups.items():
        summaries[key] = {
            "placement": key[3],
            "n": len(group),
            "accuracy": accuracy(group),
            "parse_failure_rate": sum(1 for row in group if not row.get("parsed_answer")) / len(group),
        }
    return summaries


def delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return value - baseline


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-run", required=True, type=Path)
    parser.add_argument("--task-run", required=True, type=Path)
    parser.add_argument("--task-placement", default="task_suffix")
    parser.add_argument("--out", default=None, type=Path)
    args = parser.parse_args()

    system = summarize(load_run_root(args.system_run), "system")
    task = summarize(load_run_root(args.task_run), args.task_placement)

    system_keys = {(model, dataset, condition) for model, dataset, condition, placement in system if placement == "system"}
    task_keys = {
        (model, dataset, condition)
        for model, dataset, condition, placement in task
        if placement == args.task_placement
    }
    keys = sorted(system_keys | task_keys)
    by_model_dataset: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for model, dataset, condition in keys:
        by_model_dataset[(model, dataset)][condition] = {
            "system": system.get((model, dataset, condition, "system"), {}),
            "task": task.get((model, dataset, condition, args.task_placement), {}),
        }

    rows = []
    for (model, dataset), conditions in sorted(by_model_dataset.items()):
        sys_base = conditions.get("baseline", {}).get("system", {}).get("accuracy")
        task_base = conditions.get("baseline", {}).get("task", {}).get("accuracy")
        for condition, payload in sorted(conditions.items()):
            if condition == "baseline":
                continue
            sys_acc = payload.get("system", {}).get("accuracy")
            task_acc = payload.get("task", {}).get("accuracy")
            sys_delta = delta(sys_acc, sys_base)
            task_delta = delta(task_acc, task_base)
            rows.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "condition": condition,
                    "system_accuracy": fmt(sys_acc),
                    f"{args.task_placement}_accuracy": fmt(task_acc),
                    "system_delta_vs_baseline": fmt(sys_delta),
                    f"{args.task_placement}_delta_vs_baseline": fmt(task_delta),
                    "task_minus_system_delta": fmt(
                        None if sys_delta is None or task_delta is None else task_delta - sys_delta
                    ),
                    "system_n": payload.get("system", {}).get("n", 0),
                    f"{args.task_placement}_n": payload.get("task", {}).get("n", 0),
                    "system_parse_failure_rate": fmt(payload.get("system", {}).get("parse_failure_rate")),
                    f"{args.task_placement}_parse_failure_rate": fmt(
                        payload.get("task", {}).get("parse_failure_rate")
                    ),
                }
            )

    out = args.out or (Path("outputs") / "analysis" / "task_vs_system_effects.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
