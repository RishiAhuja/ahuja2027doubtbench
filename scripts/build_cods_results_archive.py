#!/usr/bin/env python3
"""Build a provenance-preserving, paper-facing CODS result archive.

Raw runs remain immutable. Canonical cells contain relative symlinks to their
source run directories plus compact recomputed summaries. A composed cell is
accepted only if its response keys are disjoint and exactly cover the expected
factorial size.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.exp18.run_open_factorial import accuracy_rows, paired_contrasts


DEFAULT_RESULTS = ROOT / "submissions" / "cods2026" / "results"
FA = ROOT / "outputs" / "hpc_snapshots" / "it_FA0571_20260809_1609"
LOCAL_EXP18 = ROOT / "outputs" / "EXP-18"
LOCAL_PAIR = ROOT / "outputs" / "PAIR-CTRL"


MODELS = {
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
    "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
    "mistral7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "phi3.5-mini": "microsoft/Phi-3.5-mini-instruct",
    "tulu3-sft-8b": "allenai/Llama-3.1-Tulu-3-8B-SFT",
    "tulu3-dpo-8b": "allenai/Llama-3.1-Tulu-3-8B-DPO",
}


def fa(name: str, experiment: str = "PAIR-CTRL") -> Path:
    return FA / experiment / name


def medha(name: str, results_root: Path) -> Path:
    return results_root / "raw_sources" / "medha_external_top10_20260812" / "outputs" / "PAIR-CTRL" / name


def canonical_cells(results_root: Path) -> list[dict]:
    """Exact non-overlapping compositions for the 24 primary cells."""

    cells: list[dict] = []

    def add(model: str, seed: str, sources: list[Path], note: str = "") -> None:
        cells.append(
            {
                "kind": "factorial",
                "model_slug": model,
                "model": MODELS[model],
                "seed": seed,
                "expected_tasks": 1600,
                "expected_rows": 16000,
                "sources": sources,
                "note": note,
            }
        )

    # Qwen: seed 16061 was completed as base + extension + remaining 800-task tail.
    add("qwen2.5-7b", "16061", [LOCAL_EXP18 / "qwen25_full_26384.master", LOCAL_PAIR / "qwen_ext16061_26474.master", fa("qwen_rem_16061_tail_26992.master")], "400 base + 400 extension + 800 tail")
    add("qwen2.5-7b", "16101", [fa("qwen_rem_16101_full_26993.master")], "single full run")
    add("qwen2.5-7b", "16102", [fa("qwen_rem_16102_full_26994.master")], "single full run")
    add("qwen2.5-7b", "19003-heldout", [fa("qwen_rem_held19003_26920.master")], "single held-out full run")

    # Mistral development seeds ran on Medha; held-out ran on FA0571.
    add("mistral7b", "16061", [medha("mistral_rem_16061_full", results_root)], "Medha full run")
    add("mistral7b", "16101", [medha("mistral_rem_16101_full", results_root)], "Medha full run")
    add("mistral7b", "16102", [medha("mistral_rem_16102_full", results_root)], "Medha full run")
    add("mistral7b", "19003-heldout", [fa("mistral_rem_held19003_26921.master")], "FA0571 held-out full run")

    # Tulu-DPO development seed 16061 ran on Medha; the rest ran on FA0571.
    add("tulu3-dpo-8b", "16061", [medha("tuludpo_rem_16061_full", results_root)], "Medha full run")
    add("tulu3-dpo-8b", "16101", [fa("tuludpo_rem_16101_full_27070.master")], "single full run")
    add("tulu3-dpo-8b", "16102", [fa("tuludpo_rem_16102_full_27090.master")], "single full run")
    add("tulu3-dpo-8b", "19003-heldout", [fa("tuludpo_rem_held19003_27143.master")], "single held-out full run")

    # Llama: the three development seeds were completed by non-overlapping suffix runs.
    add("llama3.1-8b", "16061", [fa("llama31_full_26403.master", "EXP-18"), medha("llama_rem_16061_tail", results_root)], "400 base + 1200 Medha tail")
    add("llama3.1-8b", "16101", [fa("llama31_s16101_26706.master", "EXP-18"), fa("llama31_ext16101_26707.master"), fa("llama31_breadth16101_26708.master"), medha("llama_rem_16101_final", results_root)], "four 400-task segments")
    add("llama3.1-8b", "16102", [fa("llama31_s16102_26710.master", "EXP-18"), fa("llama_rem_16102_tail_27215.master")], "400 base + 1200 FA0571 tail; replaces Medha gated-access failure")
    add("llama3.1-8b", "19003-heldout", [fa("llama_held19003_26687.master"), fa("llama_breadth19003_26688.master"), fa("llama_finalbreadth19003_26689.master")], "800 held + 400 breadth + 400 final-breadth")

    # Phi used four 400-task development segments and an 800+400+400 held-out split.
    for seed, base in (("16061", "phi35_full_gpu_26699.master"), ("16101", "phi35_s16101_26714.master"), ("16102", "phi35_s16102_26718.master")):
        add("phi3.5-mini", seed, [fa(base, "EXP-18"), fa(f"phi35_ext{seed}_{26700 if seed == '16061' else 26715 if seed == '16101' else 26719}.master"), fa(f"phi35_breadth{seed}_{26701 if seed == '16061' else 26716 if seed == '16101' else 26720}.master"), fa(f"phi35_finalbreadth{seed}_{26702 if seed == '16061' else 26717 if seed == '16101' else 26721}.master")], "four 400-task segments")
    add("phi3.5-mini", "19003-heldout", [fa("phi35_held19003_26690.master"), fa("phi35_breadth19003_26691.master"), fa("phi35_finalbreadth19003_26692.master")], "800 held + 400 breadth + 400 final-breadth")

    # Tulu-SFT used the 768-token base plus tails; held-out is 800+800.
    add("tulu3-sft-8b", "16061", [fa("tulu3_sft_full_budget768_26703.master", "EXP-18"), fa("tulusft_ext16061_26705.master"), medha("tulusft_rem_16061_tail", results_root)], "400 base + 400 extension + 800 Medha tail")
    add("tulu3-sft-8b", "16101", [fa("tulu3_sft_s16101_26722.master", "EXP-18"), medha("tulusft_rem_16101_tail", results_root)], "400 base + 1200 Medha tail")
    add("tulu3-sft-8b", "16102", [fa("tulu3_sft_s16102_26723.master", "EXP-18"), medha("tulusft_rem_16102_tail", results_root)], "400 base + 1200 Medha tail")
    add("tulu3-sft-8b", "19003-heldout", [fa("tulusft_held19003_26704.master"), fa("tulusft_rem_held19003_tail_26979.master")], "800 held + 800 tail")

    return cells


def surface_cells() -> list[dict]:
    names = {
        "qwen2.5-7b": "qwen_rem_surface19003_27148.master",
        "mistral7b": "mistral_rem_surface19003_27157.master",
        "tulu3-sft-8b": "tulusft_rem_surface19003_27158.master",
        "tulu3-dpo-8b": "tuludpo_rem_surface19003_27159.master",
        "llama3.1-8b": "llama_surface19003_26693.master",
        "phi3.5-mini": "phi35_surface19003_26694.master",
    }
    return [
        {
            "kind": "surface-robustness",
            "model_slug": slug,
            "model": MODELS[slug],
            "seed": "19003-heldout",
            "expected_tasks": 660,
            "expected_rows": 6600,
            "sources": [fa(name)],
            "note": "330 canonical tasks with 660 answer-preserving surface variants",
        }
        for slug, name in names.items()
    ]


def load_rows(run: Path) -> list[dict]:
    raw = run / "raw_outputs.jsonl"
    if not raw.exists():
        raise FileNotFoundError(raw)
    rows = []
    with raw.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise RuntimeError(f"Invalid JSON at {raw}:{number}: {error}") from error
    return rows


def response_key(row: dict) -> tuple[str, str, str]:
    return str(row["task_template"]), str(row["sample_id"]), str(row["condition"])


def task_key(row: dict) -> str:
    return str(row["sample_id"])


def safe_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        if destination.resolve() != source.resolve():
            raise RuntimeError(f"Refusing to replace mismatched link: {destination}")
        return
    if destination.exists():
        raise RuntimeError(f"Refusing to overwrite: {destination}")
    destination.symlink_to(os.path.relpath(source.resolve(), destination.parent.resolve()), target_is_directory=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text() == text:
        return
    path.write_text(text)


def summarize_cell(cell: dict, results_root: Path, bootstrap_resamples: int) -> dict:
    rows: list[dict] = []
    source_info = []
    seen: set[tuple[str, str, str]] = set()
    overlap = []
    for index, source in enumerate(cell["sources"], 1):
        source_rows = load_rows(source)
        keys = {response_key(row) for row in source_rows}
        overlap.extend(sorted(seen.intersection(keys))[:10])
        seen.update(keys)
        rows.extend(source_rows)
        source_info.append(
            {
                "order": index,
                "run_name": source.name,
                "source_path": str(source),
                "observed_rows": len(source_rows),
                "metrics_present": (source / "metrics.json").is_file() and (source / "metrics.json").stat().st_size > 0,
                "config_present": (source / "config.json").is_file(),
            }
        )

    models = sorted({str(row.get("model")) for row in rows})
    token_budgets = sorted(
        {
            int((row.get("params") or {}).get("max_new_tokens"))
            for row in rows
            if (row.get("params") or {}).get("max_new_tokens") is not None
        }
    )
    unique_tasks = {task_key(row) for row in rows}
    unique_responses = {response_key(row) for row in rows}
    errors = []
    if overlap:
        errors.append(f"overlapping response keys: {overlap[:3]}")
    if len(rows) != cell["expected_rows"]:
        errors.append(f"rows={len(rows)} expected={cell['expected_rows']}")
    if len(unique_responses) != cell["expected_rows"]:
        errors.append(f"unique_response_keys={len(unique_responses)} expected={cell['expected_rows']}")
    if len(unique_tasks) != cell["expected_tasks"]:
        errors.append(f"unique_tasks={len(unique_tasks)} expected={cell['expected_tasks']}")
    if models != [cell["model"]]:
        errors.append(f"models={models} expected={[cell['model']]}")
    if errors:
        raise RuntimeError(f"Invalid canonical cell {cell['model_slug']}/{cell['seed']}: {'; '.join(errors)}")

    parse_rate = sum(bool(row.get("error")) for row in rows) / len(rows)
    truncation_rate = sum(bool(row.get("truncated")) for row in rows) / len(rows)
    status = "quality_gate_pass" if parse_rate <= 0.02 and truncation_rate <= 0.02 else "quality_gate_failure"
    protocol_status = "homogeneous" if len(token_budgets) == 1 else "mixed_token_budget"
    canonical = results_root / "canonical_runs" / cell["kind"] / cell["model_slug"] / cell["seed"]
    for index, source in enumerate(cell["sources"], 1):
        safe_link(source, canonical / "sources" / f"{index:02d}_{source.name}")
    composition = {
        **{key: cell[key] for key in ("kind", "model_slug", "model", "seed", "expected_tasks", "expected_rows", "note")},
        "observed_tasks": len(unique_tasks),
        "observed_rows": len(rows),
        "unique_response_keys": len(unique_responses),
        "segments_are_disjoint": not overlap,
        "sources": source_info,
        "max_new_token_budgets": token_budgets,
        "protocol_status": protocol_status,
    }
    summary = {
        "model": cell["model"],
        "seed": cell["seed"],
        "kind": cell["kind"],
        "tasks": len(unique_tasks),
        "rows": len(rows),
        "quality_status": status,
        "parse_failure_rate": parse_rate,
        "truncation_rate": truncation_rate,
        "by_model_template_condition": accuracy_rows(rows),
        "paired_contrasts": paired_contrasts(rows, bootstrap_resamples, 18001),
    }
    write_json(canonical / "composition.json", composition)
    write_json(canonical / "summary.json", summary)
    return {**composition, "canonical_path": str(canonical.relative_to(results_root)), "quality_status": status, "parse_failure_rate": parse_rate, "truncation_rate": truncation_rate}


def inventory_run(run: Path, source: str) -> dict:
    config = {}
    if (run / "config.json").is_file():
        try:
            config = json.loads((run / "config.json").read_text())
        except json.JSONDecodeError:
            config = {"invalid": True}
    raw = run / "raw_outputs.jsonl"
    rows = 0
    if raw.is_file():
        with raw.open(encoding="utf-8", errors="replace") as handle:
            rows = sum(1 for line in handle if line.strip())
    return {
        "source": source,
        "run_name": run.name,
        "path": str(run),
        "model": config.get("model"),
        "data_file": config.get("data_file"),
        "max_new_tokens": config.get("max_new_tokens"),
        "batch_size": config.get("batch_size"),
        "observed_rows": rows,
        "metrics_present": (run / "metrics.json").is_file() and (run / "metrics.json").stat().st_size > 0,
        "raw_present": raw.is_file(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--bootstrap-resamples", type=int, default=300)
    args = parser.parse_args()
    results_root = args.results_root.resolve()
    medha_root = results_root / "raw_sources" / "medha_external_top10_20260812"
    if not (medha_root / "campaign.json").is_file():
        raise SystemExit(f"Extract the Medha archive at {medha_root} before running this builder")

    safe_link(FA, results_root / "raw_sources" / "fa0571_snapshot_20260809")
    safe_link(ROOT / "benchmarks" / "pair_ctrl" / "campaigns" / "fa0571_remaining_21.json", results_root / "raw_sources" / "fa0571_campaign_ledger.json.link")
    safe_link(LOCAL_EXP18, results_root / "raw_sources" / "local_exp18")
    safe_link(LOCAL_PAIR, results_root / "raw_sources" / "local_pair_ctrl")

    cells = canonical_cells(results_root) + surface_cells()
    summaries = [summarize_cell(cell, results_root, args.bootstrap_resamples) for cell in cells]
    write_json(results_root / "manifests" / "canonical_cells.json", summaries)

    inventory = []
    sources = [
        (FA / "EXP-18", "fa0571/EXP-18"),
        (FA / "PAIR-CTRL", "fa0571/PAIR-CTRL"),
        (LOCAL_EXP18, "local/EXP-18"),
        (LOCAL_PAIR, "local/PAIR-CTRL"),
        (medha_root / "outputs" / "PAIR-CTRL", "medha/PAIR-CTRL"),
    ]
    for source_root, source_name in sources:
        if source_root.is_dir():
            inventory.extend(inventory_run(run, source_name) for run in sorted(source_root.iterdir()) if run.is_dir())
    write_json(results_root / "manifests" / "all_raw_runs.json", inventory)

    with (results_root / "manifests" / "canonical_cells.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["kind", "model_slug", "model", "seed", "observed_tasks", "observed_rows", "protocol_status", "max_new_token_budgets", "quality_status", "parse_failure_rate", "truncation_rate", "canonical_path", "note"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)

    digest = hashlib.sha256((medha_root / "MANIFEST.txt").read_bytes()).hexdigest()
    write_json(
        results_root / "manifests" / "build_info.json",
        {
            "schema": 1,
            "canonical_factorial_cells": sum(item["kind"] == "factorial" for item in summaries),
            "protocol_homogeneous_factorial_cells": sum(item["kind"] == "factorial" and item["protocol_status"] == "homogeneous" for item in summaries),
            "mixed_protocol_factorial_cells": sum(item["kind"] == "factorial" and item["protocol_status"] != "homogeneous" for item in summaries),
            "canonical_surface_cells": sum(item["kind"] == "surface-robustness" for item in summaries),
            "models": MODELS,
            "medha_manifest_sha256": digest,
            "raw_runs_inventoried": len(inventory),
            "summary_bootstrap_resamples": args.bootstrap_resamples,
            "warning": "Canonical source links are local links; preserve raw_sources when relocating the archive.",
        },
    )
    print(f"Built {len(summaries)} validated canonical cells at {results_root}")


if __name__ == "__main__":
    main()
