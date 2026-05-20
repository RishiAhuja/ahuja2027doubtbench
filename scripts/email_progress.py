#!/usr/bin/env python3
"""Email compact CAISc cluster progress through Resend.

Required env: RESEND_API_KEY, RESEND_FROM, RESEND_TO
Optional: ROOT (default /Data3/it_FA0571/caisc)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
RESEND_URL = "https://api.resend.com/emails"
ETA_HISTORY = Path(
    os.environ.get("CAISC_ETA_HISTORY", str(ROOT / "logs" / "progress_email" / "eta_history.jsonl"))
)


def run_progress() -> str:
    python = os.environ.get("PYTHON", "/Data3/it_FA0571/.conda/envs/cultural_env/bin/python")
    env = os.environ.copy()
    env["PATH"] = "/opt/pbs/bin:" + env.get("PATH", "")
    env["ROOT"] = str(ROOT)
    proc = subprocess.run(
        [python, str(ROOT / "scripts" / "progress_status.py")],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
        env=env,
    )
    return proc.stdout.strip()


def send_email(subject: str, text: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("RESEND_FROM", "").strip()
    recipient = os.environ.get("RESEND_TO", "").strip()
    if not api_key or not sender or not recipient:
        raise SystemExit("Missing RESEND_API_KEY, RESEND_FROM, or RESEND_TO")

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": text,
    }
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "caisc-progress-email/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Resend accepted: HTTP {response.status} {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend HTTP {exc.code}: {body}") from exc


def parse_progress_summary(progress: str) -> dict[str, int | float | str] | None:
    overall = re.search(
        r"OVERALL:\s+(\d+)/(\d+)\s+rows\s+\(\s*([0-9.]+%)\).*?running=(\d+)\s+held=(\d+)",
        progress,
    )
    if overall:
        done, total, percent, running, held = overall.groups()
        return {
            "scope": "overall",
            "done": int(done),
            "total": int(total),
            "percent": float(percent.rstrip("%")),
            "running": int(running),
            "held": int(held),
        }

    batch = re.search(r"Batch total:\s+(\d+)/(\d+)\s+rows\s+\(\s*([0-9.]+%)\)", progress)
    if batch:
        done, total, percent = batch.groups()
        return {
            "scope": "batch",
            "done": int(done),
            "total": int(total),
            "percent": float(percent.rstrip("%")),
        }

    return None


def load_eta_history() -> list[dict[str, Any]]:
    if not ETA_HISTORY.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in ETA_HISTORY.read_text(encoding="utf-8").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if {"ts", "done", "total"}.issubset(payload):
                rows.append(payload)
    except OSError:
        return []
    return rows


def append_eta_history(entry: dict[str, Any]) -> None:
    ETA_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with ETA_HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_duration(seconds: float) -> str:
    if seconds < 0:
        return "n/a"
    minutes = int(round(seconds / 60))
    if minutes < 90:
        return f"{minutes}m"
    hours = seconds / 3600
    if hours < 48:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def eta_from_history(
    history: list[dict[str, Any]],
    current: dict[str, Any],
) -> tuple[str | None, str | None]:
    total = int(current["total"])
    done = int(current["done"])
    if total <= 0 or done >= total:
        return "done", None

    current_ts = parse_ts(str(current["ts"]))
    if current_ts is None:
        return None, None

    relevant = [
        row
        for row in history
        if int(row.get("total", -1)) == total and str(row.get("scope", current["scope"])) == current["scope"]
    ]
    relevant.append(current)
    relevant = sorted(relevant, key=lambda row: str(row.get("ts", "")))

    progress_seconds = 0.0
    progress_rows = 0
    first_done: int | None = None
    first_ts: datetime | None = None

    previous: dict[str, Any] | None = None
    for row in relevant:
        row_ts = parse_ts(str(row.get("ts", "")))
        if row_ts is None:
            continue
        row_done = int(row.get("done", 0))
        if first_done is None:
            first_done = row_done
            first_ts = row_ts
        if previous is None:
            previous = row
            continue
        prev_ts = parse_ts(str(previous.get("ts", "")))
        prev_done = int(previous.get("done", 0))
        if prev_ts is not None and row_ts > prev_ts and row_done > prev_done:
            progress_seconds += (row_ts - prev_ts).total_seconds()
            progress_rows += row_done - prev_done
        previous = row

    if progress_rows <= 0 or progress_seconds <= 0:
        return None, "waiting for another progress point"

    rows_per_second = progress_rows / progress_seconds
    remaining_seconds = (total - done) / rows_per_second
    eta_time = current_ts.timestamp() + remaining_seconds
    eta_dt = datetime.fromtimestamp(eta_time, tz=current_ts.tzinfo)
    eta_label = f"~{format_duration(remaining_seconds)}"

    if first_done is not None and first_ts is not None:
        window_hours = (current_ts - first_ts).total_seconds() / 3600
        note = f"rate {progress_rows} rows/{format_duration(progress_seconds)}, window {window_hours:.1f}h"
    else:
        note = f"rate {progress_rows} rows/{format_duration(progress_seconds)}"
    note += f", ETA {eta_dt.strftime('%Y-%m-%d %H:%M')}"
    return eta_label, note


def subject_from_progress(prefix: str, progress: str, now: str, eta_label: str | None) -> str:
    summary = parse_progress_summary(progress)
    if summary and summary["scope"] == "overall":
        eta = f" | ETA {eta_label}" if eta_label else ""
        return (
            f"{prefix} {summary['percent']:.1f}% | {summary['done']}/{summary['total']} rows"
            f"{eta} | R{summary['running']} H{summary['held']}"
        )

    if summary:
        eta = f" | ETA {eta_label}" if eta_label else ""
        return f"{prefix} {summary['percent']:.1f}% | {summary['done']}/{summary['total']} rows{eta}"

    return f"{prefix} status - {now}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-prefix", default="CAISc EXP-02 overnight")
    args = parser.parse_args()

    now_dt = datetime.now().astimezone()
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    host = socket.gethostname()
    progress = run_progress()
    summary = parse_progress_summary(progress)
    eta_label: str | None = None
    eta_note: str | None = None
    if summary:
        current = {
            "ts": now_dt.isoformat(),
            "scope": summary["scope"],
            "done": summary["done"],
            "total": summary["total"],
            "percent": summary["percent"],
        }
        history = load_eta_history()
        eta_label, eta_note = eta_from_history(history, current)
        append_eta_history(current)

    subject = subject_from_progress(args.subject_prefix, progress, now, eta_label)
    eta_text = f"\nETA: {eta_label} ({eta_note})\n" if eta_label and eta_note else ""
    text = f"Host: {host}\nRoot: {ROOT}\nGenerated: {now}{eta_text}\n{progress}\n"
    send_email(subject, text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
