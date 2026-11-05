#!/usr/bin/env python3
"""Verify the released task files, manifests, pairings, and result inventories."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from doubtbench.scoring import score_output  # noqa: E402


TASK_SETS = (
    "task_set_16061",
    "task_set_16101",
    "task_set_16102",
    "task_set_19003",
)
EXPECTED_FAMILIES = {
    "working_memory",
    "inhibition",
    "flexibility",
    "rule_learning",
    "monitoring",
    "planning",
    "relational_integration",
    "goal_management",
}
EXPECTED_MODELS = {
    "qwen2.5-7b",
    "mistral7b",
    "llama3.1-8b",
    "phi3.5-mini",
    "tulu3-sft-8b",
    "tulu3-dpo-8b",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_main_tasks() -> set[str]:
    """Check task files, manifests, family balance, and gold-answer scoring."""
    all_ids: set[str] = set()
    all_types: set[str] = set()
    for task_set in TASK_SETS:
        path = ROOT / "data" / f"{task_set}.jsonl"
        manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        rows = read_jsonl(path)
        assert manifest["benchmark"] == "DoubtBench"
        assert manifest["task_count"] == len(rows) == 1600
        assert manifest["sha256"] == sha256(path)
        ids = [row["task_id"] for row in rows]
        assert len(ids) == len(set(ids))
        assert not (all_ids & set(ids))
        all_ids.update(ids)
        families = Counter(row["family"] for row in rows)
        difficulties = Counter(row["difficulty"] for row in rows)
        assert set(families) == EXPECTED_FAMILIES
        assert set(families.values()) == {200}
        assert difficulties == {"easy": 640, "medium": 640, "hard": 320}
        for row in rows:
            assert row["dataset"] == "doubtbench"
            assert score_output(f"Final answer: {row['gold']}", row["gold"], row["answer_type"])
            all_types.add(row["task_type"])
    assert len(all_ids) == 6400
    assert len(all_types) == 33
    return all_ids


def verify_surface(main_ids: set[str]) -> None:
    """Check that each surface task has three answer-preserving renderings."""
    path = ROOT / "data" / "surface_forms.jsonl"
    manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    rows = read_jsonl(path)
    assert manifest["sha256"] == sha256(path)
    assert manifest["latent_task_count"] == 330
    assert manifest["rendering_count"] == len(rows) == 990
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        metadata = row["metadata"]["doubtbench"]
        assert metadata["main_task_id"] in main_ids
        grouped.setdefault(metadata["latent_task_id"], []).append(row)
    assert len(grouped) == 330
    for group in grouped.values():
        assert {row["metadata"]["doubtbench"]["surface_form"] for row in group} == {
            "canonical",
            "structured",
            "scenario",
        }
        assert len({(row["gold"], row["answer_type"]) for row in group}) == 1


def verify_results() -> None:
    """Check that the result tables exist and cover the released models."""
    required = {
        "scorecard_by_model.csv",
        "scorecard_by_model_seed.csv",
        "condition_accuracy_by_model.csv",
        "family_effects_by_model.csv",
        "difficulty_effects_by_model.csv",
        "surface_effects.csv",
        "surface_consistency.csv",
        "tulu_posttraining_case_study.csv",
    }
    assert required <= {path.name for path in (ROOT / "results").glob("*.csv")}
    with (ROOT / "results" / "scorecard_by_model.csv").open(newline="", encoding="utf-8") as handle:
        models = {row["model_slug"] for row in csv.DictReader(handle)}
    assert models == EXPECTED_MODELS


def verify_public_surface() -> None:
    """Reject retired internal names in released text files."""
    # This check rejects retired internal names. Tokens are concatenated so
    # this source file does not contain the forbidden literals.
    forbidden = [
        "_".join(("pair", "ctrl")),
        "".join(("pair", "ctrl")),
        "-".join(("PAIR", "CTRL")),
        "".join(("exp", "02")),
        "".join(("exp", "14")),
        "".join(("exp", "16")),
        "".join(("exp", "18")),
        "-".join(("EXP", "02")),
        "-".join(("EXP", "14")),
        "-".join(("EXP", "16")),
        "-".join(("EXP", "18")),
        "CAI" + "Sc",
        "-".join(("identity", "emotion")),
        "melanch" + "olic",
        "GSM" + "8K",
        "19003-" + "heldout",
        "inclusive_" + "scorecard",
        "load_" + "dotenv",
    ]
    import subprocess

    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    for rel in tracked:
        if not rel:
            continue
        path = ROOT / rel.decode()
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pdf", ".png", ".svg", ".jsonl", ".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                raise AssertionError(
                    f"Internal token {token!r} found in {path.relative_to(ROOT)}"
                )


def main() -> int:
    main_ids = verify_main_tasks()
    verify_surface(main_ids)
    verify_results()
    verify_public_surface()
    print("PASS: 6,400 unique tasks across four task sets")
    print("PASS: 330 latent surface tasks and 990 paired renderings")
    print("PASS: gold-answer self-checks and file hashes")
    print("PASS: compact result tables for six checkpoints")
    print("PASS: no internal package names in released text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
