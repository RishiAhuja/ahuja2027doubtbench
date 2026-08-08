#!/usr/bin/env python3
"""Combine a predecessor focused split with its PAIR-CTRL family extension."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            rows.append(row)
    return rows


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-id", required=True)
    parser.add_argument("--base-seed", type=int, required=True)
    args = parser.parse_args()

    predecessor_source = read_jsonl(args.predecessor)
    extension_source = read_jsonl(args.extension)
    predecessor: list[dict[str, Any]] = []
    for source_row in predecessor_source:
        row = dict(source_row)
        legacy_task_id = str(source_row["task_id"])
        row["task_id"] = f"pairctrl_{args.split_id}_{legacy_task_id}"
        row["dataset"] = "pair_ctrl"
        metadata = dict(source_row.get("metadata") or {})
        metadata["pair_ctrl"] = {
            "benchmark": "PAIR-CTRL",
            "schema_version": "1.0-candidate",
            "split_id": args.split_id,
            "base_seed": args.base_seed,
            "legacy_dataset": source_row.get("dataset"),
            "legacy_task_id": legacy_task_id,
            "component": "predecessor_working_memory_and_inhibition",
        }
        row["metadata"] = metadata
        predecessor.append(row)
    extension: list[dict[str, Any]] = []
    for source_row in extension_source:
        row = dict(source_row)
        source_task_id = str(source_row["task_id"])
        source_metadata = dict(source_row.get("metadata") or {})
        source_pair_ctrl = dict(source_metadata.get("pair_ctrl") or {})
        legacy_task_id = str(source_pair_ctrl.get("legacy_task_id", source_task_id))
        row["task_id"] = f"pairctrl_{args.split_id}_{legacy_task_id}"
        row["dataset"] = "pair_ctrl"
        source_metadata["pair_ctrl"] = {
            **source_pair_ctrl,
            "benchmark": "PAIR-CTRL",
            "schema_version": "1.0-candidate",
            "split_id": args.split_id,
            "base_seed": args.base_seed,
            "legacy_task_id": legacy_task_id,
            "source_split_id": source_pair_ctrl.get("split_id"),
            "source_task_id": source_task_id,
            "component": "flexibility_and_rule_learning_extension",
        }
        row["metadata"] = source_metadata
        extension.append(row)

    rows = predecessor + extension

    ids = [str(row.get("task_id", "")) for row in rows]
    if not all(ids):
        raise ValueError("Every row must contain a non-empty task_id")
    duplicates = sorted(task_id for task_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate task IDs: {duplicates[:10]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    counts = {
        key: dict(sorted(Counter(str(row.get(key, "missing")) for row in rows).items()))
        for key in ("family", "task_type", "difficulty", "answer_type")
    }
    manifest = {
        "benchmark": "PAIR-CTRL",
        "schema_version": "1.0-candidate",
        "status": "historical_development_or_replication",
        "split_id": args.split_id,
        "base_seed": args.base_seed,
        "task_count": len(rows),
        "data_file": str(args.out),
        "data_sha256": file_hash(args.out),
        "counts": counts,
        "components": [
            {
                "role": "predecessor_working_memory_and_inhibition",
                "file": str(args.predecessor),
                "sha256": file_hash(args.predecessor),
                "task_count": len(predecessor_source),
            },
            {
                "role": "pair_ctrl_flexibility_and_rule_learning_extension",
                "file": str(args.extension),
                "sha256": file_hash(args.extension),
                "task_count": len(extension_source),
            },
        ],
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.out} ({len(rows)} tasks, {manifest['data_sha256']}) and "
        f"{manifest_path}"
    )


if __name__ == "__main__":
    main()
