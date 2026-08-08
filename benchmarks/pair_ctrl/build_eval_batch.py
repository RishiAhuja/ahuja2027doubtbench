#!/usr/bin/env python3
"""Concatenate unchanged PAIR-CTRL task files into an evaluation-only batch.

Unlike ``merge_components.py``, this utility preserves every source task ID and
prompt verbatim.  It is intended only to reduce model-loading overhead when a
checkpoint is missing several already-frozen benchmark components.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp16.scoring import score_output


REQUIRED_FIELDS = {
    "answer_type",
    "difficulty",
    "family",
    "gold",
    "prompt",
    "task_id",
    "task_type",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            missing = sorted(REQUIRED_FIELDS - set(row))
            if missing:
                raise ValueError(f"{path}:{line_number}: missing fields {missing}")
            if not score_output(
                f"Final answer: {row['gold']}", row["gold"], row["answer_type"]
            ):
                raise ValueError(
                    f"{path}:{line_number}: gold does not self-score for {row['task_id']}"
                )
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--expected-tasks", type=int, required=True)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    for path in args.component:
        source_rows = read_jsonl(path)
        rows.extend(source_rows)
        components.append(
            {
                "file": str(path),
                "sha256": file_hash(path),
                "task_count": len(source_rows),
                "families": sorted({str(row["family"]) for row in source_rows}),
            }
        )

    if len(rows) != args.expected_tasks:
        raise ValueError(
            f"Expected {args.expected_tasks} tasks for {args.batch_id}, got {len(rows)}"
        )

    ids = [str(row["task_id"]) for row in rows]
    duplicate_ids = sorted(task_id for task_id, n in Counter(ids).items() if n > 1)
    if duplicate_ids:
        raise ValueError(f"Duplicate task IDs: {duplicate_ids[:10]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    counts = {
        field: dict(sorted(Counter(str(row[field]) for row in rows).items()))
        for field in ("family", "task_type", "difficulty", "answer_type")
    }
    manifest = {
        "artifact_role": "evaluation_batch_only",
        "batch_id": args.batch_id,
        "benchmark": "PAIR-CTRL",
        "data_file": str(args.out),
        "data_sha256": file_hash(args.out),
        "preserves_source_task_fields": True,
        "task_count": len(rows),
        "expected_response_rows": len(rows) * 10,
        "counts": counts,
        "components": components,
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(rows)} unchanged tasks to {args.out} "
        f"({manifest['data_sha256']})"
    )


if __name__ == "__main__":
    main()
