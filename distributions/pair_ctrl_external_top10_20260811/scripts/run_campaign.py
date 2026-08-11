#!/usr/bin/env python3
"""Run the external campaign sequentially in authoritative priority order."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_orders(value: str | None, available: list[int]) -> list[int]:
    if value is None:
        return available
    selected = [int(item.strip()) for item in value.split(",") if item.strip()]
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise SystemExit(f"Unknown external orders: {unknown}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--campaign", type=Path, default=None)
    parser.add_argument("--orders", default=None, help="Comma-separated external orders")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    campaign_path = (args.campaign or root / "campaign.json").resolve()
    with campaign_path.open(encoding="utf-8") as handle:
        campaign = json.load(handle)
    available = sorted(int(job["external_order"]) for job in campaign["jobs"])
    orders = parse_orders(args.orders, available)

    failures = []
    for order in orders:
        command = [
            sys.executable,
            str(root / "scripts" / "run_job.py"),
            "--root",
            str(root),
            "--campaign",
            str(campaign_path),
            "--external-order",
            str(order),
        ]
        if args.preflight_only:
            command.append("--preflight-only")
        print(f"\n=== external order {order} ===", flush=True)
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode not in {0, 3}:
            failures.append((order, result.returncode))
            if not args.continue_on_failure:
                print(f"stopping after order {order} exit={result.returncode}", file=sys.stderr)
                return result.returncode or 1

    if failures:
        print(f"campaign finished with failures: {failures}", file=sys.stderr)
        return 1
    print("campaign sequence complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

