#!/usr/bin/env python3
"""Validate generated EXP-16 cognitive battery files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from experiments.exp16.scoring import score_output


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows


def validate_file(path: Path) -> None:
    rows = load_rows(path)
    ids = [row["task_id"] for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = [task_id for task_id, count in Counter(ids).items() if count > 1]
        raise SystemExit(f"{path}: duplicate task ids: {duplicates[:5]}")
    required = {
        "task_id",
        "dataset",
        "family",
        "task_type",
        "difficulty",
        "prompt",
        "gold",
        "answer_type",
        "metadata",
    }
    for row in rows:
        missing = required - set(row)
        if missing:
            raise SystemExit(f"{path}: {row.get('task_id')} missing {sorted(missing)}")
        if row["dataset"] != "exp16_cognitive":
            raise SystemExit(f"{path}: {row['task_id']} has dataset={row['dataset']!r}")
        if "Final answer:" not in row["prompt"]:
            raise SystemExit(f"{path}: {row['task_id']} missing final-answer instruction")
        if not score_output(f"Final answer: {row['gold']}", row["gold"], row["answer_type"]):
            raise SystemExit(f"{path}: gold answer does not self-score for {row['task_id']}")
    print(f"{path}: {len(rows)} rows")
    for key in ["family", "task_type", "difficulty", "answer_type"]:
        print(f"  {key}: {dict(sorted(Counter(row[key] for row in rows).items()))}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        validate_file(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
