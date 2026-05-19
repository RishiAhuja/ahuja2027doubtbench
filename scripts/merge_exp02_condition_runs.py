#!/usr/bin/env python3
"""Merge EXP-02 one-condition run directories and recompute metrics."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from core.json_utils import write_json, write_jsonl
from experiments.exp02.common import finalize_run


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("run_dirs", nargs="+")
    args = parser.parse_args()

    out_dir = Path(args.out)
    source_dirs = [Path(item) for item in args.run_dirs if Path(item).is_dir()]
    source_dirs = [path for path in source_dirs if (path / "raw_outputs.jsonl").exists()]
    if not source_dirs:
        raise SystemExit("No run directories with raw_outputs.jsonl found.")

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    configs: list[dict] = []
    seen_samples = False
    for run_dir in sorted(source_dirs):
        rows.extend(load_jsonl(run_dir / "raw_outputs.jsonl"))
        config_path = run_dir / "config.json"
        if config_path.exists():
            configs.append(json.loads(config_path.read_text(encoding="utf-8")))
        samples_path = run_dir / "samples.jsonl"
        if samples_path.exists() and not seen_samples:
            shutil.copy2(samples_path, out_dir / "samples.jsonl")
            seen_samples = True

    write_json(out_dir / "config.json", {"merged_from": [str(path) for path in source_dirs], "configs": configs})
    write_jsonl(out_dir / "raw_outputs.jsonl", rows)
    finalize_run(out_dir, rows)
    print(f"Merged {len(rows)} rows from {len(source_dirs)} runs into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
