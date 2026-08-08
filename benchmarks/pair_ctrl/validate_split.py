#!/usr/bin/env python3
"""Validate PAIR-CTRL split structure, hashes, and cross-file ID uniqueness."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from experiments.exp16.scoring import score_output


REQUIRED = {
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path: Path) -> tuple[list[dict], dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise SystemExit(f"{path}: missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    if manifest["data_sha256"] != sha256(path):
        raise SystemExit(f"{path}: SHA-256 does not match manifest")
    if manifest["task_count"] != len(rows):
        raise SystemExit(f"{path}: row count does not match manifest")

    ids = []
    for row in rows:
        missing = REQUIRED - set(row)
        if missing:
            raise SystemExit(f"{path}: row missing {sorted(missing)}")
        if row["dataset"] != "pair_ctrl":
            raise SystemExit(f"{path}: unexpected dataset {row['dataset']}")
        pair_meta = row["metadata"].get("pair_ctrl", {})
        if pair_meta.get("split_id") != manifest["split_id"]:
            raise SystemExit(f"{path}: split metadata mismatch for {row['task_id']}")
        if not score_output(
            f"Final answer: {row['gold']}", row["gold"], row["answer_type"]
        ):
            raise SystemExit(f"{path}: gold does not self-score for {row['task_id']}")
        ids.append(row["task_id"])

    if len(ids) != len(set(ids)):
        raise SystemExit(f"{path}: duplicate IDs within split")

    counts = {
        field: dict(sorted(Counter(str(row[field]) for row in rows).items()))
        for field in ["family", "task_type", "difficulty", "answer_type"]
    }
    if counts != manifest["counts"]:
        raise SystemExit(f"{path}: inventory does not match manifest")
    return rows, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    global_ids: dict[str, Path] = {}
    for path in args.paths:
        rows, manifest = validate(path)
        for row in rows:
            task_id = row["task_id"]
            if task_id in global_ids:
                raise SystemExit(
                    f"duplicate global ID {task_id}: {global_ids[task_id]} and {path}"
                )
            global_ids[task_id] = path
        print(
            f"{path}: valid; split={manifest['split_id']} tasks={len(rows)} "
            f"sha256={manifest['data_sha256']}"
        )
    print(f"Validated {len(args.paths)} splits and {len(global_ids)} globally unique tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

