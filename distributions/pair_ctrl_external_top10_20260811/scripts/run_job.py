#!/usr/bin/env python3
"""Run exactly one manifest job with resumable output and explicit state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from status_report import ROOT, count_lines


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_campaign(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        campaign = json.load(handle)
    if not isinstance(campaign, dict) or not isinstance(campaign.get("jobs"), list):
        raise SystemExit(f"Invalid campaign manifest: {path}")
    return campaign


def atomic_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def structural_state(root: Path, tag: str, expected_rows: int, log_path: Path) -> tuple[bool, int, bool, bool]:
    run_dir = root / "outputs" / "PAIR-CTRL" / tag
    rows = count_lines(run_dir / "raw_outputs.jsonl")
    metrics_ok = (run_dir / "metrics.json").exists() and (run_dir / "metrics.json").stat().st_size > 0
    marker_ok = False
    if log_path.exists():
        marker_ok = "PAIR-CTRL complete:" in log_path.read_text(encoding="utf-8", errors="replace")
    return rows == expected_rows and metrics_ok and marker_ok, rows, metrics_ok, marker_ok


def post_best_effort(root: Path) -> None:
    subprocess.run(
        [sys.executable, str(root / "scripts" / "post_status.py")],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=40,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-order", type=int, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    campaign_path = (args.campaign or root / "campaign.json").resolve()
    campaign = load_campaign(campaign_path)
    matches = [job for job in campaign["jobs"] if int(job["external_order"]) == args.external_order]
    if len(matches) != 1:
        raise SystemExit(f"Expected one job for external order {args.external_order}")
    job = matches[0]
    policy = campaign["execution_policy"]

    data_path = (root / str(job["data_file"])).resolve()
    try:
        data_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"Data file escapes package root: {data_path}") from exc
    if not data_path.is_file():
        raise SystemExit(f"Missing data file: {data_path}")
    data_manifest_path = data_path.with_suffix(".manifest.json")
    if not data_manifest_path.is_file():
        raise SystemExit(f"Missing data manifest: {data_manifest_path}")
    with data_manifest_path.open(encoding="utf-8") as handle:
        data_manifest = json.load(handle)
    task_rows = count_lines(data_path)
    expected_tasks = int(job["expected_tasks"])
    expected_rows = int(job["expected_response_rows"])
    if task_rows != expected_tasks:
        raise SystemExit(f"{data_path} has {task_rows} tasks; expected {expected_tasks}")
    if int(data_manifest.get("task_count", -1)) != expected_tasks:
        raise SystemExit(f"Manifest task count mismatch for {data_path}")
    expected_sha256 = str(data_manifest.get("data_sha256") or "")
    actual_sha256 = sha256_file(data_path)
    if not expected_sha256 or actual_sha256 != expected_sha256:
        raise SystemExit(f"SHA-256 mismatch for {data_path}")
    if expected_rows != expected_tasks * int(policy["expected_responses_per_task"]):
        raise SystemExit(f"Invalid expected response total for {job['model_tag']}")

    print(
        f"preflight ok order={args.external_order} model={job['model']} "
        f"tasks={expected_tasks} expected_rows={expected_rows}"
    )
    if args.preflight_only:
        return 0

    tag = str(job["model_tag"])
    output_dir = root / "outputs" / "PAIR-CTRL" / tag
    log_path = root / "logs" / f"{tag}.log"
    state_path = root / "state" / f"{tag}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    complete, rows, metrics_ok, marker_ok = structural_state(root, tag, expected_rows, log_path)
    if complete:
        existing_state = read_state(state_path)
        existing_quality_failure = existing_state.get("status") == "quality_gate_failure"
        atomic_state(
            state_path,
            {
                "status": "quality_gate_failure" if existing_quality_failure else "completed_existing",
                "updated_at": now(),
                "external_order": args.external_order,
                "model": job["model"],
                "model_tag": tag,
                "rows": rows,
                "expected_rows": expected_rows,
            },
        )
        print(f"already complete: {tag} ({rows}/{expected_rows})")
        post_best_effort(root)
        return 3 if existing_quality_failure else 0

    cache_dir = Path(os.environ.get("HF_HOME", str(root / "hf_cache"))).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "experiments.exp18.run_open_factorial",
        "--experiment-id",
        "PAIR-CTRL",
        "--model",
        str(job["model"]),
        "--data-file",
        str(data_path.relative_to(root)),
        "--cache-dir",
        str(cache_dir),
        "--max-new-tokens",
        str(policy["max_new_tokens"]),
        "--batch-size",
        str(policy["batch_size"]),
        "--thinking-mode",
        str(policy["thinking_mode"]),
        "--max-parse-failure-rate",
        str(policy["max_parse_failure_rate"]),
        "--max-truncation-rate",
        str(policy["max_truncation_rate"]),
        "--out",
        str(output_dir),
        "--resume",
    ]

    state = {
        "status": "running",
        "started_at": now(),
        "updated_at": now(),
        "external_order": args.external_order,
        "model": job["model"],
        "model_tag": tag,
        "data_file": job["data_file"],
        "expected_rows": expected_rows,
        "command": command,
        "pid": None,
    }
    atomic_state(state_path, state)
    post_best_effort(root)

    environment = os.environ.copy()
    environment["HF_HOME"] = str(cache_dir)
    environment.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "hub"))
    environment.setdefault("TOKENIZERS_PARALLELISM", "false")
    environment.setdefault("PYTHONUNBUFFERED", "1")

    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"\n[{now()}] launching external_order={args.external_order} tag={tag}\n")
        log_handle.flush()
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        state["pid"] = process.pid
        state["updated_at"] = now()
        atomic_state(state_path, state)
        try:
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                log_handle.write(line)
                log_handle.flush()
            return_code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait(timeout=30)
            state.update({"status": "interrupted", "updated_at": now()})
            atomic_state(state_path, state)
            post_best_effort(root)
            return 130

    complete, rows, metrics_ok, marker_ok = structural_state(root, tag, expected_rows, log_path)
    state.update(
        {
            "updated_at": now(),
            "finished_at": now(),
            "runner_exit_status": return_code,
            "rows": rows,
            "metrics_present": metrics_ok,
            "completion_marker_present": marker_ok,
        }
    )
    if complete and return_code == 0:
        state["status"] = "completed"
    elif complete and return_code == 3:
        state["status"] = "quality_gate_failure"
    else:
        state["status"] = "failed"
    atomic_state(state_path, state)
    post_best_effort(root)

    if not complete:
        print(
            f"structural failure: rows={rows}/{expected_rows} metrics={metrics_ok} marker={marker_ok}",
            file=sys.stderr,
        )
        return 1
    if return_code not in {0, 3}:
        return return_code or 1
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
