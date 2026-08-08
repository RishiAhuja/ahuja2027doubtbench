#!/usr/bin/env python3
"""Merge generated PAIR-CTRL components into a normalized full split."""

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
    parser.add_argument("--component", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-id", required=True)
    parser.add_argument("--base-seed", type=int, required=True)
    parser.add_argument("--status", default="candidate_not_frozen")
    args = parser.parse_args()

    merged: list[dict[str, Any]] = []
    component_records: list[dict[str, Any]] = []
    for component_number, path in enumerate(args.component, start=1):
        source_rows = read_jsonl(path)
        families = sorted({str(row["family"]) for row in source_rows})
        role = f"component_{component_number}_{'_'.join(families)}"
        for source_row in source_rows:
            row = dict(source_row)
            source_task_id = str(source_row["task_id"])
            source_metadata = dict(source_row.get("metadata") or {})
            source_pair_ctrl = dict(source_metadata.get("pair_ctrl") or {})
            row["task_id"] = f"pairctrl_{args.split_id}_{source_task_id}"
            row["dataset"] = "pair_ctrl"
            source_metadata["pair_ctrl"] = {
                **source_pair_ctrl,
                "benchmark": "PAIR-CTRL",
                "schema_version": "1.0-candidate",
                "split_id": args.split_id,
                "base_seed": args.base_seed,
                "source_dataset": source_row.get("dataset"),
                "source_split_id": source_pair_ctrl.get("split_id"),
                "source_task_id": source_task_id,
                "component": role,
            }
            row["metadata"] = source_metadata
            merged.append(row)
        component_records.append(
            {
                "role": role,
                "families": families,
                "file": str(path),
                "sha256": file_hash(path),
                "task_count": len(source_rows),
            }
        )

    ids = [str(row["task_id"]) for row in merged]
    duplicates = sorted(task_id for task_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate task IDs after merge: {duplicates[:10]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in merged:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    counts = {
        field: dict(sorted(Counter(str(row[field]) for row in merged).items()))
        for field in ("family", "task_type", "difficulty", "answer_type")
    }
    manifest = {
        "benchmark": "PAIR-CTRL",
        "schema_version": "1.0-candidate",
        "status": args.status,
        "split_id": args.split_id,
        "base_seed": args.base_seed,
        "task_count": len(merged),
        "data_file": str(args.out),
        "data_sha256": file_hash(args.out),
        "counts": counts,
        "components": component_records,
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} tasks to {args.out} ({manifest['data_sha256']})")


if __name__ == "__main__":
    main()
