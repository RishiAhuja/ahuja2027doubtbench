#!/usr/bin/env python3
"""Small EXP-16-only progress snapshot.

This intentionally does not loop. It reads only the latest EXP-16 smoke/pilot
manifests and their raw output row counts, then prints compact text or JSON.
Use it manually on the login node instead of running a frequent watcher.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
EXP16_LOG_ROOTS = [
    ROOT / "logs" / "exp16_cognitive_smoke",
    ROOT / "logs" / "exp16_cognitive_pilot",
]
STATE_NAMES = {
    "R": "running",
    "Q": "queued",
    "H": "held",
    "E": "exiting",
}


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def qstat_jobs() -> dict[str, str]:
    try:
        out = subprocess.check_output(
            ["qstat", "-u", os.environ.get("USER", "")],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return {}
    states: dict[str, str] = {}
    for line in out.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("-") or "." not in fields[0]:
            continue
        state = next((field for field in fields[1:] if len(field) == 1 and field in STATE_NAMES), "?")
        states[fields[0]] = state
        states[fields[0].split(".", 1)[0]] = state
    return states


def latest_batch(log_root: Path) -> Path | None:
    marker = log_root / "latest_batch.txt"
    if marker.exists():
        path = Path(marker.read_text(encoding="utf-8").strip())
        if path.exists():
            return path
    batches = sorted(log_root.glob("batch_*"), key=lambda path: path.stat().st_mtime)
    return batches[-1] if batches else None


def read_manifest(batch_dir: Path) -> list[dict[str, Any]]:
    path = batch_dir / "manifest.tsv"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        rows.append(
            {
                "model": parts[0],
                "job_id": parts[1],
                "expected_rows": int(parts[2]),
                "run_dir": parts[3],
                "log_path": parts[4],
                "data_file": parts[5],
            }
        )
    return rows


def count_rows(run_dir: Path) -> int:
    raw = run_dir / "raw_outputs.jsonl"
    if not raw.exists():
        return 0
    with raw.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def row_state(run_dir: Path, done: int, expected: int, job_id: str, states: dict[str, str]) -> str:
    state_key = states.get(job_id, states.get(job_id.split(".", 1)[0], "?"))
    state = STATE_NAMES.get(state_key, state_key if state_key != "?" else "done")
    if (run_dir / "metrics.json").exists():
        return "complete"
    if done >= expected > 0:
        return "finishing"
    if done == 0 and state == "done":
        return "pending"
    return state


def pct(done: int, expected: int) -> float | None:
    return round(100 * done / expected, 1) if expected else None


def build_snapshot() -> dict[str, Any]:
    states = qstat_jobs()
    batches = []
    total_done = 0
    total_expected = 0
    state_counts: Counter[str] = Counter()
    for log_root in EXP16_LOG_ROOTS:
        batch_dir = latest_batch(log_root)
        if not batch_dir:
            continue
        rows = []
        batch_done = 0
        batch_expected = 0
        for item in read_manifest(batch_dir):
            run_dir = Path(str(item["run_dir"]))
            expected = int(item["expected_rows"])
            done = count_rows(run_dir)
            state = row_state(run_dir, done, expected, str(item["job_id"]), states)
            batch_done += done
            batch_expected += expected
            total_done += done
            total_expected += expected
            state_counts[state] += 1
            rows.append(
                {
                    "model": item["model"],
                    "job_id": item["job_id"],
                    "state": state,
                    "done": done,
                    "expected": expected,
                    "percent": pct(done, expected),
                    "run_dir": short_path(run_dir),
                }
            )
        batches.append(
            {
                "name": log_root.name,
                "batch_dir": short_path(batch_dir),
                "done": batch_done,
                "expected": batch_expected,
                "percent": pct(batch_done, batch_expected),
                "rows": rows,
            }
        )
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "overall": {
            "done": total_done,
            "expected": total_expected,
            "percent": pct(total_done, total_expected),
            "states": dict(sorted(state_counts.items())),
        },
        "batches": batches,
    }


def print_text(snapshot: dict[str, Any]) -> None:
    overall = snapshot["overall"]
    print(
        f"EXP-16 {overall['done']}/{overall['expected']} rows "
        f"({overall['percent']}%) states={overall['states']}"
    )
    for batch in snapshot["batches"]:
        print(f"{batch['name']}: {batch['done']}/{batch['expected']} ({batch['percent']}%)")
        for row in batch["rows"]:
            print(
                f"  {row['job_id']:12} {row['state']:9} "
                f"{row['done']:4}/{row['expected']:<4} {row['percent']}% {row['model']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of compact text.")
    parser.add_argument("--write-json", type=Path, default=None, help="Also write JSON snapshot here.")
    args = parser.parse_args()

    snapshot = build_snapshot()
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print_text(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
