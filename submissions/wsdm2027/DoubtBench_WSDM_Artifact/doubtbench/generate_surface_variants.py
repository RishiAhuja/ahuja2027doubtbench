#!/usr/bin/env python3
"""Create paired structured and scenario wording variants for held-out tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from doubtbench.scoring import score_output


FINAL_MARKER = "\n\nEnd with exactly one line in the form:\nFinal answer: <answer>"
VARIANTS = ("structured", "scenario")
DIFFICULTY_COUNTS = {"easy": 4, "medium": 4, "hard": 2}

FAMILY_PREAMBLES = {
    "working_memory": "You are maintaining a temporary operations record.",
    "inhibition": "You are extracting the relevant signal from a noisy control log.",
    "flexibility": "A controller changes which response rule is active during the sequence.",
    "rule_learning": "A local encoding scheme must be inferred from the supplied examples.",
    "monitoring": "You are auditing an execution report for consistency.",
    "planning": "You are selecting an operational plan under explicit constraints.",
    "relational_integration": "Several records describe linked entities or relations.",
    "goal_management": "You are managing pending goals, triggers, and interruptions.",
}


def stable_rank(task_id: str) -> str:
    return hashlib.sha256(f"DoubtBench:surface:{task_id}".encode()).hexdigest()


def rephrase(text: str) -> str:
    replacements = [
        ("Give the", "Return the"),
        ("Give their", "Return their"),
        ("Give them", "Return them"),
        ("Apply", "Execute"),
        ("Ignore", "Disregard"),
        ("Start at", "Use the initial value"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def render_variant(prompt: str, family: str, variant: str) -> str:
    if not prompt.endswith(FINAL_MARKER):
        raise ValueError("Prompt does not end in the canonical final-answer instruction")
    body = prompt[: -len(FINAL_MARKER)]
    if variant == "structured":
        rendered = "[TASK SPECIFICATION]\n" + rephrase(body)
    elif variant == "scenario":
        rendered = (
            FAMILY_PREAMBLES[family]
            + "\n\n[CASE]\n"
            + rephrase(body)
        )
    else:
        raise ValueError(variant)
    return rendered + FINAL_MARKER


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-id", default="surface_forms")
    args = parser.parse_args()

    source_rows = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line]
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        buckets[(str(row["task_type"]), str(row["difficulty"]))].append(row)

    selected: list[dict[str, Any]] = []
    task_types = sorted({str(row["task_type"]) for row in source_rows})
    for task_type in task_types:
        for difficulty, count in DIFFICULTY_COUNTS.items():
            candidates = sorted(
                buckets[(task_type, difficulty)], key=lambda row: stable_rank(str(row["task_id"]))
            )
            if len(candidates) < count:
                raise ValueError(f"Not enough {task_type}/{difficulty} tasks")
            selected.extend(candidates[:count])

    generation_seed = 19003
    rows: list[dict[str, Any]] = []
    for source_row in selected:
        for variant in VARIANTS:
            row = dict(source_row)
            source_task_id = str(source_row["task_id"])
            row["task_id"] = f"doubtbench_{args.split_id}_{variant}_{source_task_id}"
            row["prompt"] = render_variant(str(source_row["prompt"]), str(source_row["family"]), variant)
            metadata = dict(source_row.get("metadata") or {})
            doubtbench = dict(metadata.get("doubtbench") or {})
            metadata["doubtbench"] = {
                **doubtbench,
                "benchmark": "DoubtBench",
                "task_set": args.split_id,
                "generation_seed": generation_seed,
                "source_task_set": doubtbench.get("task_set"),
                "source_task_id": source_task_id,
                "surface_variant": variant,
                "latent_task_id": source_task_id,
            }
            row["metadata"] = metadata
            if not score_output(f"Final answer: {row['gold']}", str(row["gold"]), str(row["answer_type"])):
                raise ValueError(f"Gold does not self-score: {row['task_id']}")
            rows.append(row)

    ids = [str(row["task_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate surface-variant task IDs")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    counts = {
        field: dict(sorted(Counter(str(row[field]) for row in rows).items()))
        for field in ("family", "task_type", "difficulty", "answer_type")
    }
    surface_variant_counts = dict(
        sorted(Counter(row["metadata"]["doubtbench"]["surface_variant"] for row in rows).items())
    )
    manifest = {
        "benchmark": "DoubtBench",
        "task_set": args.split_id,
        "generation_seed": generation_seed,
        "source_file": str(args.source),
        "source_sha256": file_hash(args.source),
        "task_count": len(rows),
        "latent_task_count": len(selected),
        "surface_variants": list(VARIANTS),
        "task_types": len(task_types),
        "data_file": str(args.out),
        "data_sha256": file_hash(args.out),
        "counts": counts,
        "surface_variant_counts": surface_variant_counts,
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(rows)} surface variants for {len(selected)} latent tasks and "
        f"{len(task_types)} task types"
    )


if __name__ == "__main__":
    main()
