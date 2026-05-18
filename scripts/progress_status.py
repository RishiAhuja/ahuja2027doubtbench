#!/usr/bin/env python3
"""Compact EXP-02 cluster progress summary for overnight PBS chains."""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
OVERNIGHT_LOG = ROOT / "logs" / "overnight"
STATE_NAMES = {
    "R": "running",
    "Q": "queued",
    "H": "held",
    "E": "exiting",
}


def pct(done: int, total: int) -> str:
    if total <= 0:
        return "n/a"
    return f"{100 * done / total:5.1f}%"


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def qstat_jobs() -> list[dict[str, str]]:
    try:
        out = subprocess.check_output(
            ["qstat", "-u", os.environ.get("USER", "")],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return []

    jobs = []
    for line in out.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("-") or "." not in fields[0]:
            continue
        state = next((field for field in fields[1:] if len(field) == 1 and field in STATE_NAMES), "?")
        jobs.append(
            {
                "id": fields[0],
                "queue": fields[2] if len(fields) > 2 else "?",
                "name": fields[3] if len(fields) > 3 else "?",
                "state": state,
            }
        )
    return jobs


def latest_batch_dir() -> Path | None:
    marker = OVERNIGHT_LOG / "latest_batch.txt"
    if marker.exists():
        path = Path(marker.read_text().strip())
        if path.exists():
            return path
    batches = sorted(OVERNIGHT_LOG.glob("batch_*"))
    return batches[-1] if batches else None


def read_manifest(batch_dir: Path) -> list[dict[str, str]]:
    path = batch_dir / "manifest.tsv"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) >= 5:
            rows.append(
                {
                    "model": parts[0],
                    "job_id": parts[1],
                    "expected_rows": int(parts[2]),
                    "run_dir": parts[3],
                    "log_path": parts[4],
                }
            )
    return rows


def count_rows(run_dir: Path) -> tuple[int, bool]:
    raw = run_dir / "raw_outputs.jsonl"
    if not raw.exists():
        return 0, False
    try:
        return sum(1 for _ in raw.open(encoding="utf-8")), True
    except OSError:
        return 0, False


def scan_exp02_outputs() -> list[tuple[str, int, int]]:
    """Fallback: scan recent gpu_smoke / open dirs if no manifest."""
    rows: list[tuple[str, int, int]] = []
    base = ROOT / "outputs" / "EXP-02"
    if not base.exists():
        return rows
    for path in sorted(base.glob("**/raw_outputs.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
        done, _ = count_rows(path.parent)
        config = path.parent / "config.json"
        expected = 0
        if config.exists():
            try:
                payload = json.loads(config.read_text(encoding="utf-8"))
                counts = payload.get("counts") or {}
                conditions = payload.get("conditions") or []
                n_samples = sum(int(v) for v in counts.values())
                n_conditions = len(conditions) if isinstance(conditions, list) else 3
                expected = n_samples * n_conditions
            except (json.JSONDecodeError, TypeError, ValueError):
                expected = 0
        rows.append((short_path(path.parent), done, expected))
    return rows


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jobs = qstat_jobs()
    job_counts = Counter(job["state"] for job in jobs)
    caisc_jobs = [job for job in jobs if "caisc" in job["name"].lower()]

    print(f"Time: {now}")
    print(f"Root: {ROOT}")
    print(
        "PBS (all): "
        f"running={job_counts.get('R', 0)} "
        f"queued={job_counts.get('Q', 0)} "
        f"total={len(jobs)}"
    )
    if caisc_jobs:
        print("PBS (caisc):")
        for job in caisc_jobs:
            state = STATE_NAMES.get(job["state"], job["state"])
            print(f"  {job['id']:16} {state:8} {job['name']}")

    batch_dir = latest_batch_dir()
    if not batch_dir:
        print()
        print("Overnight batch: none (scanning recent EXP-02 outputs)")
        for path, done, expected in scan_exp02_outputs():
            print(f"  {path}: {done}/{expected} ({pct(done, expected)})")
        return 0

    manifest = read_manifest(batch_dir)
    if not manifest:
        print()
        print(f"Overnight batch: {short_path(batch_dir)} (empty manifest)")
        return 0

    state_by_job = {job["id"]: job["state"] for job in jobs}
    state_by_job.update({job["id"].split(".")[0]: job["state"] for job in jobs})

    total_expected = sum(row["expected_rows"] for row in manifest)
    total_done = 0
    completed_jobs = 0

    print()
    print(f"Overnight batch: {short_path(batch_dir)}")
    for row in manifest:
        run_dir = Path(row["run_dir"])
        done, exists = count_rows(run_dir)
        expected = row["expected_rows"]
        total_done += done
        state_key = state_by_job.get(row["job_id"], state_by_job.get(row["job_id"].split(".")[0], "?"))
        state = STATE_NAMES.get(state_key, state_key if state_key != "?" else "done")
        metrics_path = run_dir / "metrics.json"
        if metrics_path.exists():
            state = "complete"
            completed_jobs += 1
        elif done >= expected and expected > 0:
            state = "finishing"
        elif not exists and state == "?":
            state = "pending"
        print(
            f"  {row['model'][:42]:42} {done:>4}/{expected:<4} {pct(done, expected)} "
            f"{state:10} {row['job_id']}"
        )

    print(
        f"Batch total: {total_done}/{total_expected} rows ({pct(total_done, total_expected)}) | "
        f"jobs complete={completed_jobs}/{len(manifest)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
