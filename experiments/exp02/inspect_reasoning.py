#!/usr/bin/env python3
"""Print reasoning chains from an EXP-02 API run (raw_outputs.jsonl)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_latest_run(base: Path) -> Path | None:
    candidates = sorted(base.glob("smoke_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--condition", default=None)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else None
    if args.latest or run_dir is None:
        run_dir = find_latest_run(Path("outputs/EXP-02"))
    if run_dir is None or not run_dir.exists():
        print("No run directory found.", file=sys.stderr)
        return 1

    raw_path = run_dir / "raw_outputs.jsonl"
    if not raw_path.exists():
        print(f"Missing {raw_path}", file=sys.stderr)
        return 1

    print(f"Run: {run_dir}")
    print(f"Model: {(run_dir / 'config.json').read_text() if (run_dir / 'config.json').exists() else '?'}")
    shown = 0
    for line in raw_path.open(encoding="utf-8"):
        row = json.loads(line)
        if args.dataset and row.get("dataset") != args.dataset:
            continue
        if args.condition and row.get("condition") != args.condition:
            continue
        if shown >= args.limit:
            break
        shown += 1
        print()
        print("=" * 72)
        print(
            f"{row.get('model')} | {row.get('condition')} | {row.get('dataset')} | {row.get('sample_id')}"
        )
        print(f"score={row.get('score')} parsed={row.get('parsed_answer')!r} gold={row.get('gold')!r}")
        if row.get("usage"):
            print(f"usage: {row['usage']}")
        chain = row.get("reasoning_chain") or []
        if chain:
            print("--- reasoning_chain ---")
            for i, block in enumerate(chain, 1):
                preview = block if len(block) <= 1200 else block[:1200] + "…"
                print(f"[{i}] {preview}")
        else:
            print("--- raw_output (no separate chain) ---")
            text = row.get("raw_output", "")
            preview = text if len(text) <= 1200 else text[:1200] + "…"
            print(preview)
        if row.get("error"):
            print(f"ERROR: {row['error']}")

    print()
    print(f"Showed {shown} rows (limit {args.limit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
