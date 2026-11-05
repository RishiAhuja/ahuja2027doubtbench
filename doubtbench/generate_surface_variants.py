#!/usr/bin/env python3
"""Write structured and scenario wordings for a fixed sample of existing tasks.

Gold answers and answer types are copied from the source file. For every task
type, the sample is 4 easy tasks, 4 medium tasks, and 2 hard tasks. Tasks are
ordered by the hex SHA-256 of DoubtBench:surface:<task id>, lowest digest
first. Each selected task is written twice, once in each wording.

The structured wording places the task body under a specification heading.
The scenario wording adds the opening sentence for the family and a case heading.
Both wordings apply the same fixed word swaps and keep the final-answer
instruction. The written id is doubtbench, the task-set name, the wording
name, and then the full source task id. The source id is not shortened.

The manifest records generation seed 19003. That number is constant. This
script reads task content from the source file and does not draw new items.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from doubtbench.scoring import score_output


# This must stay identical to the instruction appended by make_task.
FINAL_MARKER = "\n\nEnd with exactly one line in the form:\nFinal answer: <answer>"
# Each selected source task is written once in each of these wordings, in this order.
VARIANTS = ("structured", "scenario")
# How many source tasks to keep from each task type.
DIFFICULTY_COUNTS = {"easy": 4, "medium": 4, "hard": 2}

# Opening sentence used by the scenario wording of each family.
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
    """Sort key for choosing source tasks: the hex SHA-256 of DoubtBench:surface:<task id>."""
    return hashlib.sha256(f"DoubtBench:surface:{task_id}".encode()).hexdigest()


def rephrase(text: str) -> str:
    """Apply the fixed word swaps shared by the structured and scenario wordings."""
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
    """Return the structured or scenario prompt, still ending with the final-answer instruction."""
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
    """SHA-256 of a file, read in 1 MiB blocks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    """Select the sample, write both wordings, and write a manifest next to the output."""
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

    # Stored in the manifest. The tasks themselves come from the source file.
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
