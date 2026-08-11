#!/usr/bin/env python3
"""Post compact status to the portfolio endpoint; never upload run content."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from status_report import ROOT, collect_status


DEFAULT_URL = "https://rishia.in/api/cluster-progress/ingest"
DEFAULT_ENV = Path.home() / ".config" / "pair-ctrl-external" / "progress.env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def post(payload: dict, url: str, token: str) -> None:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "pair-ctrl-external-status/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Status accepted: HTTP {response.status} {body}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Status endpoint returned HTTP {exc.code}: {body}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    campaign = (args.campaign or root / "campaign.json").resolve()
    load_env_file(args.env_file.expanduser())
    payload = collect_status(root, campaign)
    payload.pop("jobs", None)

    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    token = (
        os.environ.get("PORTFOLIO_PROGRESS_TOKEN")
        or os.environ.get("CLUSTER_PROGRESS_TOKEN")
        or ""
    ).strip()
    url = os.environ.get("PORTFOLIO_PROGRESS_URL", DEFAULT_URL).strip()
    post(payload, url, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
