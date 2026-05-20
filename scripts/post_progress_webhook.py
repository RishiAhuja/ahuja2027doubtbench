#!/usr/bin/env python3
"""Post compact CAISc cluster progress to a portfolio webhook."""

from __future__ import annotations

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

from scripts.email_progress import (
    append_eta_history,
    eta_from_history,
    load_eta_history,
    parse_progress_summary,
)

ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
DEFAULT_URL = "https://rishia.in/api/cluster-progress/ingest"


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


def parse_queue_summary(progress: str) -> dict[str, int | None]:
    match = re.search(r"PBS \(all\): running=(\d+) queued=(\d+) total=(\d+)", progress)
    if not match:
        return {"pbs_running": None, "queued": None, "pbs_total": None}
    running, queued, total = match.groups()
    return {"pbs_running": int(running), "queued": int(queued), "pbs_total": int(total)}


def build_payload(progress: str) -> dict[str, Any]:
    now = datetime.now().astimezone()
    summary = parse_progress_summary(progress)
    queue = parse_queue_summary(progress)
    eta_label = None
    eta_note = None

    payload: dict[str, Any] = {
        "source": "caisc-cluster",
        "host": socket.gethostname(),
        "generated_at": now.isoformat(),
        "progress_text": progress,
        "queued": queue["queued"],
    }

    if summary:
        current = {
            "ts": now.isoformat(),
            "scope": summary["scope"],
            "done": summary["done"],
            "total": summary["total"],
            "percent": summary["percent"],
        }
        eta_label, eta_note = eta_from_history(load_eta_history(), current)
        append_eta_history(current)
        payload.update(
            {
                "done": summary["done"],
                "total": summary["total"],
                "percent": summary["percent"],
                "running": summary.get("running", queue["pbs_running"]),
                "held": summary.get("held"),
                "eta_label": eta_label,
                "eta_note": eta_note,
            }
        )

    return payload


def post_payload(payload: dict[str, Any]) -> None:
    url = os.environ.get("PORTFOLIO_PROGRESS_URL", DEFAULT_URL).strip()
    token = (
        os.environ.get("PORTFOLIO_PROGRESS_TOKEN")
        or os.environ.get("CLUSTER_PROGRESS_TOKEN")
        or ""
    ).strip()
    if not token:
        raise SystemExit("Missing PORTFOLIO_PROGRESS_TOKEN or CLUSTER_PROGRESS_TOKEN")

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "caisc-progress-webhook/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Webhook accepted: HTTP {response.status} {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Webhook HTTP {exc.code}: {body}") from exc


def main() -> int:
    progress = run_progress()
    payload = build_payload(progress)
    post_payload(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
