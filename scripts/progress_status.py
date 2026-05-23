#!/usr/bin/env python3
"""Compact EXP-02 cluster progress summary for PBS batches."""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
LOG_ROOTS = [
    ROOT / "logs" / "exp05_tulu",
    ROOT / "logs" / "task_vs_system",
    ROOT / "logs" / "task_vs_system_system",
    ROOT / "logs" / "task_vs_system_task_prefix",
    ROOT / "logs" / "task_vs_system_task_suffix",
    ROOT / "logs" / "task_vs_system_system_extra",
    ROOT / "logs" / "task_vs_system_task_suffix_extra",
    ROOT / "logs" / "task_vs_system_tulu_task_prefix",
    ROOT / "logs" / "task_vs_system_tulu_task_suffix",
    ROOT / "logs" / "affect_sweep_system",
    ROOT / "logs" / "salience_ladder_task_prefix",
    ROOT / "logs" / "salience_ladder_task_suffix",
    ROOT / "logs" / "exp14_reasoning_smoke",
    ROOT / "logs" / "exp14_reasoning_pilot",
    ROOT / "logs" / "exp15_coupling_smoke",
    ROOT / "logs" / "exp15_coupling_pilot",
    ROOT / "logs" / "exp02b",
    ROOT / "logs" / "scaleup",
    ROOT / "logs" / "overnight",
]
CAMPAIGN_ROOTS = [
    ROOT / "logs" / "exp05_tulu",
    ROOT / "logs" / "task_vs_system_system",
    ROOT / "logs" / "task_vs_system_task_prefix",
    ROOT / "logs" / "task_vs_system_task_suffix",
    ROOT / "logs" / "task_vs_system_system_extra",
    ROOT / "logs" / "task_vs_system_task_suffix_extra",
    ROOT / "logs" / "task_vs_system_tulu_task_prefix",
    ROOT / "logs" / "task_vs_system_tulu_task_suffix",
    ROOT / "logs" / "affect_sweep_system",
    ROOT / "logs" / "salience_ladder_task_prefix",
    ROOT / "logs" / "salience_ladder_task_suffix",
    ROOT / "logs" / "exp14_reasoning_smoke",
    ROOT / "logs" / "exp14_reasoning_pilot",
    ROOT / "logs" / "exp15_coupling_smoke",
    ROOT / "logs" / "exp15_coupling_pilot",
]
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
    marked_batches: list[tuple[float, Path]] = []
    for log_root in LOG_ROOTS:
        marker = log_root / "latest_batch.txt"
        if marker.exists():
            path = Path(marker.read_text().strip())
            if path.exists():
                marked_batches.append((marker.stat().st_mtime, path))
    if marked_batches:
        return sorted(marked_batches)[-1][1]
    batches: list[Path] = []
    for log_root in LOG_ROOTS:
        batches.extend(log_root.glob("batch_*"))
    return sorted(batches, key=lambda path: path.stat().st_mtime)[-1] if batches else None


def read_manifest(batch_dir: Path) -> list[dict[str, str | int]]:
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
                    "counts_file": parts[5] if len(parts) > 5 else "",
                }
            )
    return rows


def latest_batch_for_root(log_root: Path) -> Path | None:
    marker = log_root / "latest_batch.txt"
    if marker.exists():
        path = Path(marker.read_text().strip())
        if path.exists():
            return path
    batches = sorted(log_root.glob("batch_*"), key=lambda path: path.stat().st_mtime)
    return batches[-1] if batches else None


def campaign_batches() -> list[Path]:
    batches = []
    seen = set()
    for log_root in CAMPAIGN_ROOTS:
        batch = latest_batch_for_root(log_root)
        if batch and batch not in seen and read_manifest(batch):
            batches.append(batch)
            seen.add(batch)
    return sorted(batches, key=lambda path: path.stat().st_mtime)


def count_rows(run_dir: Path) -> tuple[int, bool]:
    raw = run_dir / "raw_outputs.jsonl"
    if not raw.exists():
        return 0, False
    try:
        return sum(1 for _ in raw.open(encoding="utf-8")), True
    except OSError:
        return 0, False


def rows_by_dataset(run_dir: Path) -> dict[str, int]:
    raw = run_dir / "raw_outputs.jsonl"
    counts: dict[str, int] = defaultdict(int)
    if not raw.exists():
        return counts
    for line in raw.open(encoding="utf-8"):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        counts[payload.get("dataset", "?")] += 1
    return dict(counts)


def expected_by_dataset(run_dir: Path) -> dict[str, int]:
    config = run_dir / "config.json"
    if not config.exists():
        return {}
    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    counts = payload.get("counts") or {}
    conditions = payload.get("conditions") or []
    n_conditions = len(conditions) if isinstance(conditions, list) else 3
    expected: dict[str, int] = {}
    for key, value in counts.items():
        dataset = "mmlu" if key == "mmlu_stratified" else str(key)
        expected[dataset] = expected.get(dataset, 0) + int(value) * n_conditions
    return expected


def scan_exp02_outputs() -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    base = ROOT / "outputs" / "EXP-02"
    if not base.exists():
        return rows
    for path in sorted(base.glob("**/raw_outputs.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
        done, _ = count_rows(path.parent)
        expected = 0
        config = path.parent / "config.json"
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


def print_dataset_progress(run_dir: Path) -> None:
    done_by = rows_by_dataset(run_dir)
    expected_by = expected_by_dataset(run_dir)
    if not expected_by:
        return
    parts = []
    for dataset in sorted(expected_by):
        done = done_by.get(dataset, 0)
        expected = expected_by.get(dataset, 0)
        parts.append(f"{dataset}={done}/{expected}")
    if parts:
        print(f"      datasets: {' | '.join(parts)}")


def manifest_row_progress(
    row: dict[str, str | int],
    state_by_job: dict[str, str],
) -> tuple[int, int, str]:
    run_dir = Path(str(row["run_dir"]))
    done, exists = count_rows(run_dir)
    expected = int(row["expected_rows"])
    job_id = str(row["job_id"])
    state_key = state_by_job.get(job_id, state_by_job.get(job_id.split(".")[0], "?"))
    state = STATE_NAMES.get(state_key, state_key if state_key != "?" else "done")
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        state = "complete"
    elif done >= expected and expected > 0:
        state = "finishing"
    elif not exists and state == "?":
        state = "pending"
    return done, expected, state


def print_campaign(batches: list[Path], jobs: list[dict[str, str]]) -> bool:
    if not batches:
        return False
    state_by_job = {job["id"]: job["state"] for job in jobs}
    state_by_job.update({job["id"].split(".")[0]: job["state"] for job in jobs})

    total_done = 0
    total_expected = 0
    total_jobs = 0
    complete_jobs = 0
    held_jobs = 0
    running_jobs = 0

    print()
    print("Campaign: EXP-02B + task-vs-system queue")
    for batch in batches:
        manifest = read_manifest(batch)
        if not manifest:
            continue
        batch_done = 0
        batch_expected = 0
        batch_states = Counter()
        label = batch.parent.name
        print()
        print(f"{label}: {short_path(batch)}")
        for row in manifest:
            done, expected, state = manifest_row_progress(row, state_by_job)
            batch_done += done
            batch_expected += expected
            total_done += done
            total_expected += expected
            total_jobs += 1
            batch_states[state] += 1
            if state == "complete":
                complete_jobs += 1
            if state == "held":
                held_jobs += 1
            if state == "running":
                running_jobs += 1
            placement = ""
            run_dir = Path(str(row["run_dir"]))
            cfg = run_dir / "config.json"
            if cfg.exists():
                try:
                    payload = json.loads(cfg.read_text(encoding="utf-8"))
                    placement = f" placement={payload.get('prompt_placement', '')}"
                except (json.JSONDecodeError, OSError):
                    placement = ""
            print(
                f"  {str(row['model'])[:48]:48} {done:>4}/{expected:<4} "
                f"{pct(done, expected)} {state:10} {row['job_id']}{placement}"
            )
            if state == "running":
                print_dataset_progress(run_dir)
        print(
            f"  batch total: {batch_done}/{batch_expected} "
            f"({pct(batch_done, batch_expected)}) | states={dict(batch_states)}"
        )

    print()
    print(
        f"OVERALL: {total_done}/{total_expected} rows ({pct(total_done, total_expected)}) | "
        f"jobs complete={complete_jobs}/{total_jobs} running={running_jobs} held={held_jobs}"
    )
    return True


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

    batches = campaign_batches()
    if print_campaign(batches, jobs):
        return 0

    batch_dir = latest_batch_dir()
    if not batch_dir:
        print()
        print("Batch: none (scanning recent EXP-02 outputs)")
        for path, done, expected in scan_exp02_outputs():
            print(f"  {path}: {done}/{expected} ({pct(done, expected)})")
        return 0

    manifest = read_manifest(batch_dir)
    if not manifest:
        print()
        print(f"Batch: {short_path(batch_dir)} (empty manifest)")
        return 0

    state_by_job = {job["id"]: job["state"] for job in jobs}
    state_by_job.update({job["id"].split(".")[0]: job["state"] for job in jobs})

    total_expected = sum(int(row["expected_rows"]) for row in manifest)
    total_done = 0
    completed_jobs = 0
    profile = manifest[0].get("counts_file") or "?"

    print()
    print(f"Batch: {short_path(batch_dir)}")
    print(f"Profile: {profile}")
    for row in manifest:
        run_dir = Path(str(row["run_dir"]))
        done, exists = count_rows(run_dir)
        expected = int(row["expected_rows"])
        total_done += done
        state_key = state_by_job.get(str(row["job_id"]), state_by_job.get(str(row["job_id"]).split(".")[0], "?"))
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
            f"  {str(row['model'])[:42]:42} {done:>4}/{expected:<4} {pct(done, expected)} "
            f"{state:10} {row['job_id']}"
        )
        print_dataset_progress(run_dir)

    print(
        f"Batch total: {total_done}/{total_expected} rows ({pct(total_done, total_expected)}) | "
        f"jobs complete={completed_jobs}/{len(manifest)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
