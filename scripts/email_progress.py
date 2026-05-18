#!/usr/bin/env python3
"""Email compact CAISc cluster progress through Resend.

Required env: RESEND_API_KEY, RESEND_FROM, RESEND_TO
Optional: ROOT (default /Data3/it_FA0571/caisc)
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("ROOT", "/Data3/it_FA0571/caisc"))
RESEND_URL = "https://api.resend.com/emails"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-prefix", default="CAISc EXP-02 overnight")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    host = socket.gethostname()
    progress = run_progress()
    subject = f"{args.subject_prefix} - {now}"
    text = f"Host: {host}\nRoot: {ROOT}\nGenerated: {now}\n\n{progress}\n"
    send_email(subject, text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
