#!/usr/bin/env python3
"""Generate focused EXP-16 follow-up batteries."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from experiments.exp16.generate_tasks import DATA_DIR, TASK_GENERATORS, generate_family, write_jsonl


DEFAULT_FAMILIES = ["working_memory", "inhibition"]
DEFAULT_SEED = 16061


def parse_families(value: str) -> list[str]:
    families = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [family for family in families if family not in TASK_GENERATORS]
    if unknown:
        choices = ", ".join(sorted(TASK_GENERATORS))
        raise argparse.ArgumentTypeError(f"unknown families {unknown}; choices: {choices}")
    if not families:
        raise argparse.ArgumentTypeError("at least one family is required")
    return families


def generate_focus(seed: int, families: list[str], per_family: int) -> list:
    rng = random.Random(seed)
    rows = []
    for family in families:
        rows.extend(generate_family(rng, family, per_family))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--families",
        type=parse_families,
        default=DEFAULT_FAMILIES,
        help="Comma-separated EXP-16 families to include.",
    )
    parser.add_argument("--smoke-per-family", type=int, default=10)
    parser.add_argument("--pilot-per-family", type=int, default=200)
    parser.add_argument(
        "--smoke-out",
        type=Path,
        default=DATA_DIR / "exp16_self_doubt_focus_smoke.jsonl",
    )
    parser.add_argument(
        "--pilot-out",
        type=Path,
        default=DATA_DIR / "exp16_self_doubt_focus_pilot.jsonl",
    )
    args = parser.parse_args()

    if args.smoke_per_family <= 0 or args.pilot_per_family <= 0:
        raise SystemExit("--smoke-per-family and --pilot-per-family must be positive")

    smoke = generate_focus(args.seed + 1, args.families, args.smoke_per_family)
    pilot = generate_focus(args.seed, args.families, args.pilot_per_family)
    write_jsonl(args.smoke_out, smoke)
    write_jsonl(args.pilot_out, pilot)
    print(f"Wrote {len(smoke)} smoke tasks to {args.smoke_out}")
    print(f"Wrote {len(pilot)} pilot tasks to {args.pilot_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
