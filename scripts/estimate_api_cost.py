#!/usr/bin/env python3
"""Estimate API spend for an EXP-02 count profile and model list."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.sample_loading import expected_rows, load_counts_file, total_samples
DEFAULT_PROFILE = REPO / "configs/counts_api_dev.json"
DEFAULT_MODELS = REPO / "configs/api_models.json"

# Fallback if api_models.json entry missing (USD per 1M tokens)
DEFAULT_INPUT_TOKENS = 900
DEFAULT_OUTPUT_TOKENS = 350


def load_models(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["ref"]: item for item in payload.get("models", [])}


def estimate_one_model(
    *,
    n_calls: int,
    input_per_mtok: float,
    output_per_mtok: float,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> dict[str, float]:
    total_in = n_calls * avg_input_tokens
    total_out = n_calls * avg_output_tokens
    cost_in = (total_in / 1_000_000) * input_per_mtok
    cost_out = (total_out / 1_000_000) * output_per_mtok
    return {
        "calls": n_calls,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "cost_input_usd": round(cost_in, 4),
        "cost_output_usd": round(cost_out, 4),
        "cost_total_usd": round(cost_in + cost_out, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts-file", default=str(DEFAULT_PROFILE))
    parser.add_argument("--conditions", type=int, default=3)
    parser.add_argument("--models-file", default=str(DEFAULT_MODELS))
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated model refs (default: default_local_suite from models file)",
    )
    parser.add_argument("--avg-input-tokens", type=int, default=DEFAULT_INPUT_TOKENS)
    parser.add_argument("--avg-output-tokens", type=int, default=DEFAULT_OUTPUT_TOKENS)
    args = parser.parse_args()

    counts = load_counts_file(Path(args.counts_file))
    n_calls = expected_rows(counts, args.conditions)
    registry = load_models(Path(args.models_file))

    if args.models:
        model_refs = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        suite = json.loads(Path(args.models_file).read_text(encoding="utf-8"))
        model_refs = suite.get("default_local_suite", [])

    print(f"Profile: {args.counts_file}")
    print(f"Samples: {total_samples(counts)} | Conditions: {args.conditions} | Calls per model: {n_calls}")
    print(f"Assumed tokens/call: {args.avg_input_tokens} in, {args.avg_output_tokens} out")
    print()

    grand = 0.0
    for ref in model_refs:
        meta = registry.get(ref, {})
        est = estimate_one_model(
            n_calls=n_calls,
            input_per_mtok=float(meta.get("input_per_mtok", 1.0)),
            output_per_mtok=float(meta.get("output_per_mtok", 5.0)),
            avg_input_tokens=args.avg_input_tokens,
            avg_output_tokens=args.avg_output_tokens,
        )
        grand += est["cost_total_usd"]
        label = meta.get("label", ref)
        print(f"{label} ({ref})")
        print(f"  ~${est['cost_total_usd']:.4f}  (in ${est['cost_input_usd']:.4f} + out ${est['cost_output_usd']:.4f})")
        if meta.get("reasoning_native"):
            print("  Note: reasoning models bill extra reasoning tokens; add ~30-50% buffer")
        print()

    print(f"Estimated total ({len(model_refs)} models): ~${grand:.4f} USD")
    print("Prices from configs/api_models.json — verify on provider pricing pages before budgeting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
