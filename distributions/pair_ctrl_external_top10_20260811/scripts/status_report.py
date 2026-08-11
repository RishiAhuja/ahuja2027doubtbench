#!/usr/bin/env python3
"""Build a compact campaign status without reading or sending output content."""

from __future__ import annotations

import argparse
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            count += block.count(b"\n")
    return count


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return load_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"status": "invalid_state"}


def collect_status(root: Path, campaign_path: Path) -> dict[str, Any]:
    campaign = load_json(campaign_path)
    jobs = campaign.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("campaign.json must contain a nonempty jobs list")

    total_rows = 0
    done_rows = 0
    running = 0
    queued = 0
    held = 0
    completed = 0
    failed = 0
    summaries = []

    for job in jobs:
        tag = str(job["model_tag"])
        expected = int(job["expected_response_rows"])
        total_rows += expected
        run_dir = root / "outputs" / "PAIR-CTRL" / tag
        raw_path = run_dir / "raw_outputs.jsonl"
        metrics_path = run_dir / "metrics.json"
        state = load_state(root / "state" / f"{tag}.json")
        rows = count_lines(raw_path)
        metrics_ok = metrics_path.exists() and metrics_path.stat().st_size > 0
        done_rows += min(rows, expected)

        recorded = str(state.get("status") or "pending")
        if rows == expected and metrics_ok:
            status = (
                "quality_gate_failure"
                if recorded == "quality_gate_failure"
                else "completed"
            )
            completed += 1
        elif rows > expected:
            status = "invalid_row_overflow"
            failed += 1
        elif recorded in {"failed", "interrupted", "invalid_state"}:
            status = recorded
            failed += 1
        elif recorded == "running":
            status = "running"
            running += 1
        elif recorded == "held":
            status = "held"
            held += 1
        else:
            status = "queued" if recorded == "queued" else "pending"
            queued += 1

        summaries.append(
            {
                "external_order": int(job["external_order"]),
                "model_tag": tag,
                "status": status,
                "rows": rows,
                "expected_rows": expected,
                "metrics_present": metrics_ok,
            }
        )

    percent = (100.0 * done_rows / total_rows) if total_rows else 0.0
    lines = [
        (
            f"PAIR-CTRL external top ten: {done_rows}/{total_rows} rows "
            f"({percent:.2f}%), completed={completed}/{len(jobs)}, "
            f"running={running}, pending_or_queued={queued}, failed={failed}"
        )
    ]
    lines.extend(
        f"{item['external_order']:02d} {item['model_tag']} {item['status']} "
        f"{item['rows']}/{item['expected_rows']}"
        for item in summaries
    )

    return {
        "campaign": str(campaign["campaign_id"]),
        "source": os.environ.get("PAIR_CTRL_STATUS_SOURCE", "friend-cluster"),
        "host": socket.gethostname(),
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "done": done_rows,
        "total": total_rows,
        "percent": percent,
        "running": running,
        "held": held,
        "queued": queued,
        "eta_label": None,
        "eta_note": "Sequential single-GPU campaign; ETA is estimated externally from row history.",
        "completed_jobs": completed,
        "failed_jobs": failed,
        "progress_text": "\n".join(lines),
        "jobs": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    campaign = (args.campaign or root / "campaign.json").resolve()
    payload = collect_status(root, campaign)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["progress_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

