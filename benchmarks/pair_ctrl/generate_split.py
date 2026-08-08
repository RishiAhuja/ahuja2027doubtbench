#!/usr/bin/env python3
"""Generate versioned PAIR-CTRL task splits from the EXP-16 task generators.

Unlike the historical EXP-16 generator, this wrapper gives every task a globally
unique split-qualified ID and derives a separate deterministic RNG stream for
each family.  Adding or reordering a family therefore cannot silently change the
instances generated for another family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

from experiments.exp16.generate_tasks import (
    TASK_GENERATORS as LEGACY_TASK_GENERATORS,
    allocate,
    difficulty_for_index,
)
from experiments.exp16.scoring import score_output

from benchmarks.pair_ctrl.task_generators_v1 import PAIR_CTRL_ADDITIONAL_GENERATORS


BENCHMARK = "PAIR-CTRL"
SCHEMA_VERSION = "1.0-candidate"
TASK_GENERATORS = {**LEGACY_TASK_GENERATORS, **PAIR_CTRL_ADDITIONAL_GENERATORS}
DEFAULT_FAMILIES = list(TASK_GENERATORS)


def parse_families(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return DEFAULT_FAMILIES[:]
    families = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(families) - set(TASK_GENERATORS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown families: {unknown}")
    if not families:
        raise argparse.ArgumentTypeError("at least one family is required")
    if len(families) != len(set(families)):
        raise argparse.ArgumentTypeError("families must be unique")
    return families


def split_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise argparse.ArgumentTypeError("split id must contain a letter or digit")
    return slug


def derived_seed(seed: int, family: str) -> int:
    digest = hashlib.sha256(f"{BENCHMARK}:{seed}:{family}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate_rows(split_id: str, seed: int, families: list[str], per_family: int) -> list[dict]:
    rows: list[dict] = []
    for family in families:
        family_rng_seed = derived_seed(seed, family)
        generators = TASK_GENERATORS[family]
        per_type = allocate(per_family, len(generators))
        tasks = []
        local_index = 0
        family_rng = random.Random(family_rng_seed)
        for generator, n_items in zip(generators, per_type, strict=True):
            for item_index in range(n_items):
                difficulty = difficulty_for_index(item_index)
                tasks.append(generator(family_rng, difficulty, local_index))
                local_index += 1
        for task in tasks:
            legacy_id = task.task_id
            metadata = dict(task.metadata)
            metadata["pair_ctrl"] = {
                "benchmark": BENCHMARK,
                "schema_version": SCHEMA_VERSION,
                "split_id": split_id,
                "base_seed": seed,
                "family_seed": family_rng_seed,
                "legacy_task_id": legacy_id,
            }
            qualified = replace(
                task,
                task_id=f"pairctrl_{split_id}_{legacy_id.removeprefix('exp16_')}",
                dataset="pair_ctrl",
                metadata=metadata,
            )
            rows.append(asdict(qualified))
    return rows


def validate_rows(rows: list[dict], families: list[str], per_family: int) -> dict[str, dict[str, int]]:
    expected = len(families) * per_family
    if len(rows) != expected:
        raise SystemExit(f"generated {len(rows)} rows; expected {expected}")

    ids = [str(row["task_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("generated duplicate task IDs")

    for row in rows:
        if row["dataset"] != "pair_ctrl":
            raise SystemExit(f"wrong dataset for {row['task_id']}")
        if "Final answer:" not in row["prompt"]:
            raise SystemExit(f"missing final-answer instruction for {row['task_id']}")
        if not score_output(
            f"Final answer: {row['gold']}", row["gold"], row["answer_type"]
        ):
            raise SystemExit(f"gold answer does not self-score for {row['task_id']}")

    counts = {}
    for field in ["family", "task_type", "difficulty", "answer_type"]:
        counts[field] = dict(sorted(Counter(str(row[field]) for row in rows).items()))
    expected_families = {family: per_family for family in families}
    if counts["family"] != expected_families:
        raise SystemExit(
            f"family counts {counts['family']} do not match expected {expected_families}"
        )
    return counts


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-id", required=True, type=split_slug)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--families", type=parse_families, default=DEFAULT_FAMILIES)
    parser.add_argument("--per-family", type=int, default=200)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()

    if args.per_family <= 0:
        raise SystemExit("--per-family must be positive")
    if args.seed < 0:
        raise SystemExit("--seed must be non-negative")

    rows = generate_rows(args.split_id, args.seed, args.families, args.per_family)
    counts = validate_rows(rows, args.families, args.per_family)
    write_jsonl(args.out, rows)

    manifest_path = args.manifest_out or args.out.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "benchmark": BENCHMARK,
        "schema_version": SCHEMA_VERSION,
        "status": "candidate_not_frozen",
        "split_id": args.split_id,
        "base_seed": args.seed,
        "family_seeds": {family: derived_seed(args.seed, family) for family in args.families},
        "families": args.families,
        "per_family": args.per_family,
        "task_count": len(rows),
        "counts": counts,
        "data_file": str(args.out),
        "data_sha256": file_sha256(args.out),
        "generator": "benchmarks/pair_ctrl/generate_split.py",
        "source_generators": "experiments/exp16/generate_tasks.py",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {len(rows)} tasks to {args.out}")
    print(f"Wrote manifest to {manifest_path}")
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
