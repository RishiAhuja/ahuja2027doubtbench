#!/usr/bin/env python3
"""List account-visible models for configured providers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm_client import ProviderError, list_provider_models, provider_available


def extract_ids(payload):
    data = payload.get("data", payload)
    if isinstance(data, list):
        ids = []
        for item in data:
            if isinstance(item, dict) and "id" in item:
                ids.append(item["id"])
        return sorted(ids)
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--providers",
        default="openai,anthropic,groq,xai",
        help="Comma-separated provider list.",
    )
    parser.add_argument("--raw", action="store_true", help="Print raw provider JSON.")
    args = parser.parse_args()

    providers = [item.strip() for item in args.providers.split(",") if item.strip()]
    for provider in providers:
        print(f"\n## {provider}")
        if not provider_available(provider):
            print("missing API key environment variable")
            continue
        try:
            payload = list_provider_models(provider)
        except ProviderError as exc:
            print(f"error: {exc}")
            continue
        if args.raw:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            ids = extract_ids(payload)
            if not ids:
                print(json.dumps(payload, indent=2, sort_keys=True)[:2000])
            for model_id in ids:
                print(model_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
