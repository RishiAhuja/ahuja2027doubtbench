#!/usr/bin/env python3
"""Compute the inclusive, paper-facing analysis for the CODS submission.

The canonical archive has already established structural completeness.  This
analysis therefore retains every complete factorial and surface cell, including
cells whose diagnostic parse/truncation rates exceeded the original alert
threshold.  Protocol and diagnostic flags remain attached to the tables; they
are annotations, not post-hoc exclusion rules.
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "submissions" / "cods2026" / "results"
OUT = RESULTS / "analysis" / "inclusive"
SURFACE_DATA = ROOT / "benchmarks" / "pair_ctrl" / "data" / "pair_ctrl_heldout_19003_surface_robustness.jsonl"

CONDITIONS = [
    "common_neutral",
    "common_self_doubt",
    "common_check",
    "common_self_doubt_check",
    "common_check_concise",
]
TEMPLATES = ["minimal", "reasoning_requested"]
CONDITION_LABELS = {
    "common_neutral": "Neutral",
    "common_self_doubt": "Self-doubt",
    "common_check": "Check",
    "common_self_doubt_check": "Doubt + check",
    "common_check_concise": "Check + concise",
}
TEMPLATE_LABELS = {"minimal": "Minimal", "reasoning_requested": "Reasoning requested"}
MODEL_LABELS = {
    "qwen2.5-7b": "Qwen 2.5 7B",
    "mistral7b": "Mistral 7B",
    "llama3.1-8b": "Llama 3.1 8B",
    "phi3.5-mini": "Phi 3.5 Mini",
    "tulu3-sft-8b": "Tulu 3 SFT 8B",
    "tulu3-dpo-8b": "Tulu 3 DPO 8B",
}
MODEL_ORDER = list(MODEL_LABELS)
FAMILY_LABELS = {
    "working_memory": "Working memory",
    "inhibition": "Inhibition",
    "flexibility": "Rule switching",
    "rule_learning": "Novel-rule learning",
    "monitoring": "Error monitoring",
    "planning": "Planning",
    "relational_integration": "Relational integration",
    "goal_management": "Goal management",
}
FAMILY_ORDER = list(FAMILY_LABELS)
DIFFICULTY_ORDER = ["easy", "medium", "hard"]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        raise ValueError(f"Cannot infer columns for empty table: {path}")
    fields = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def percentile(values: Iterable[float], probability: float) -> float:
    return float(np.quantile(np.asarray(list(values), dtype=float), probability))


def source_rows(cell: dict[str, Any]) -> list[dict[str, Any]]:
    """Load one canonical cell and enforce its response-key uniqueness again."""

    cell_dir = RESULTS / cell["canonical_path"] / "sources"
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sorted(cell_dir.iterdir()):
        raw = source / "raw_outputs.jsonl"
        with raw.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                key = (str(row["task_template"]), str(row["sample_id"]), str(row["condition"]))
                if key in seen:
                    raise RuntimeError(f"Duplicate response key in {cell_dir}: {key}")
                seen.add(key)
                rows.append(row)
    if len(rows) != int(cell["expected_rows"]):
        raise RuntimeError(f"{cell_dir}: observed {len(rows)}, expected {cell['expected_rows']}")
    return rows


def task_matrix(rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return task metadata and task x template x condition response matrices."""

    tasks: dict[str, dict[str, str]] = {}
    scores: dict[tuple[str, str, str], float] = {}
    tokens: dict[tuple[str, str, str], float] = {}
    parse_failures: dict[tuple[str, str, str], float] = {}
    truncations: dict[tuple[str, str, str], float] = {}
    for row in rows:
        task_id = str(row["sample_id"])
        tasks[task_id] = {
            "sample_id": task_id,
            "family": str(row["family"]),
            "task_type": str(row["task_type"]),
            "difficulty": str(row["difficulty"]),
            "answer_type": str(row["answer_type"]),
        }
        key = (task_id, str(row["task_template"]), str(row["condition"]))
        scores[key] = float(row.get("score") is True)
        tokens[key] = float(row.get("generated_token_count") or 0)
        parse_failures[key] = float(bool(row.get("error")))
        truncations[key] = float(bool(row.get("truncated")))

    ordered = [tasks[key] for key in sorted(tasks)]
    shape = (len(ordered), len(TEMPLATES), len(CONDITIONS))
    arrays = [np.full(shape, np.nan, dtype=float) for _ in range(4)]
    for i, task in enumerate(ordered):
        for j, template in enumerate(TEMPLATES):
            for k, condition in enumerate(CONDITIONS):
                key = (task["sample_id"], template, condition)
                arrays[0][i, j, k] = scores[key]
                arrays[1][i, j, k] = tokens[key]
                arrays[2][i, j, k] = parse_failures[key]
                arrays[3][i, j, k] = truncations[key]
    for array in arrays:
        if np.isnan(array).any():
            raise RuntimeError("Incomplete task factorial encountered in structurally complete cell")
    return ordered, arrays[0], arrays[1], arrays[2], arrays[3]


def endpoint_vectors(scores: np.ndarray) -> tuple[list[str], np.ndarray]:
    """Create per-task contributions for the frozen benchmark scorecard."""

    n, d, c, dc, cq = (CONDITIONS.index(name) for name in CONDITIONS)
    mn, rs = (TEMPLATES.index(name) for name in TEMPLATES)
    neutral = scores[:, :, n].mean(axis=1)
    doubt_gain = (scores[:, :, d] - scores[:, :, n]).mean(axis=1)
    check_gain = (scores[:, :, c] - scores[:, :, n]).mean(axis=1)
    cde_min = scores[:, mn, dc] - scores[:, mn, c]
    cde_reason = scores[:, rs, dc] - scores[:, rs, c]
    cde = (cde_min + cde_reason) / 2
    check_over_doubt = (scores[:, :, dc] - scores[:, :, d]).mean(axis=1)
    concision = (scores[:, :, cq] - scores[:, :, c]).mean(axis=1)
    context_modulation = cde_reason - cde_min
    check_context_modulation = (
        (scores[:, rs, c] - scores[:, rs, n])
        - (scores[:, mn, c] - scores[:, mn, n])
    )
    names = [
        "neutral_accuracy",
        "doubt_gain",
        "checking_gain",
        "cde",
        "checking_beyond_doubt",
        "concision_effect",
        "context_modulation",
        "cde_minimal",
        "cde_reasoning",
        "checking_context_modulation",
    ]
    return names, np.column_stack(
        [
            neutral,
            doubt_gain,
            check_gain,
            cde,
            check_over_doubt,
            concision,
            context_modulation,
            cde_min,
            cde_reason,
            check_context_modulation,
        ]
    )


def stratified_bootstrap(
    values: np.ndarray,
    strata: list[np.ndarray],
    resamples: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap tasks within each seed-family stratum, preserving macro weights."""

    rng = np.random.default_rng(seed)
    p = values.shape[1]
    boot = np.zeros((resamples, p), dtype=float)
    chunk_size = 100
    for start in range(0, resamples, chunk_size):
        size = min(chunk_size, resamples - start)
        chunk_sum = np.zeros((size, p), dtype=float)
        for indices in strata:
            draws = rng.integers(0, len(indices), size=(size, len(indices)))
            chunk_sum += values[indices[draws]].mean(axis=1)
        boot[start : start + size] = chunk_sum / len(strata)
    return np.quantile(boot, 0.025, axis=0), np.quantile(boot, 0.975, axis=0)


def mean_for_indices(values: np.ndarray, indices: np.ndarray) -> np.ndarray:
    return values[indices].mean(axis=0)


def surface_metadata() -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with SURFACE_DATA.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            pc = row["metadata"]["pair_ctrl"]
            mapping[str(row["task_id"])] = {
                "variant": str(pc["surface_variant"]),
                "paired_latent_task_id": str(pc["paired_latent_task_id"]),
                "legacy_task_id": str(row["metadata"]["pair_ctrl"].get("legacy_task_id") or row["task_id"]),
            }
    return mapping


def canonical_heldout_id(paired_id: str, legacy_id: str) -> str:
    suffix = re.sub(r"^exp16_", "", legacy_id)
    if "_final_breadth_extension_" in paired_id:
        return f"pairctrl_heldout_19003_final_breadth_extension_{suffix}"
    if "_breadth_extension_" in paired_id:
        return f"pairctrl_heldout_19003_breadth_extension_{suffix}"
    return f"pairctrl_heldout_19003_{suffix}"


def factorial_analysis(cells: list[dict[str, Any]], bootstrap_resamples: int) -> dict[str, Any]:
    factorial_cells = [cell for cell in cells if cell["kind"] == "factorial"]
    matrices: dict[tuple[str, str], dict[str, Any]] = {}
    condition_rows: list[dict[str, Any]] = []
    seed_scorecards: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    difficulty_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []

    for cell in factorial_cells:
        metadata, scores, tokens, parses, truncs = task_matrix(source_rows(cell))
        names, endpoints = endpoint_vectors(scores)
        matrices[(cell["model_slug"], cell["seed"])] = {
            "metadata": metadata,
            "scores": scores,
            "tokens": tokens,
            "parses": parses,
            "truncs": truncs,
            "endpoints": endpoints,
            "cell": cell,
        }
        means = endpoints.mean(axis=0)
        seed_row: dict[str, Any] = {
            "model_slug": cell["model_slug"],
            "model_label": MODEL_LABELS[cell["model_slug"]],
            "seed": cell["seed"],
            "protocol_status": cell["protocol_status"],
            "diagnostic_status": cell["quality_status"],
        }
        seed_row.update({name: float(value) for name, value in zip(names, means, strict=True)})
        seed_scorecards.append(seed_row)

        for ti, template in enumerate(TEMPLATES):
            for ci, condition in enumerate(CONDITIONS):
                condition_rows.append(
                    {
                        "model_slug": cell["model_slug"],
                        "model_label": MODEL_LABELS[cell["model_slug"]],
                        "seed": cell["seed"],
                        "task_template": template,
                        "template_label": TEMPLATE_LABELS[template],
                        "condition": condition,
                        "condition_label": CONDITION_LABELS[condition],
                        "n": len(metadata),
                        "accuracy": float(scores[:, ti, ci].mean()),
                        "mean_generated_tokens": float(tokens[:, ti, ci].mean()),
                        "parse_failure_rate": float(parses[:, ti, ci].mean()),
                        "truncation_rate": float(truncs[:, ti, ci].mean()),
                        "protocol_status": cell["protocol_status"],
                        "diagnostic_status": cell["quality_status"],
                    }
                )

        for family in FAMILY_ORDER:
            indices = np.asarray([i for i, task in enumerate(metadata) if task["family"] == family])
            vals = mean_for_indices(endpoints, indices)
            for template_index, template in enumerate(TEMPLATES):
                cde = float((scores[indices, template_index, CONDITIONS.index("common_self_doubt_check")] - scores[indices, template_index, CONDITIONS.index("common_check")]).mean())
                check_gain = float((scores[indices, template_index, CONDITIONS.index("common_check")] - scores[indices, template_index, CONDITIONS.index("common_neutral")]).mean())
                family_rows.append(
                    {
                        "model_slug": cell["model_slug"],
                        "model_label": MODEL_LABELS[cell["model_slug"]],
                        "seed": cell["seed"],
                        "family": family,
                        "family_label": FAMILY_LABELS[family],
                        "task_template": template,
                        "n_tasks": len(indices),
                        "cde": cde,
                        "checking_gain": check_gain,
                    }
                )
            family_rows.append(
                {
                    "model_slug": cell["model_slug"],
                    "model_label": MODEL_LABELS[cell["model_slug"]],
                    "seed": cell["seed"],
                    "family": family,
                    "family_label": FAMILY_LABELS[family],
                    "task_template": "average",
                    "n_tasks": len(indices),
                    "cde": float(vals[names.index("cde")]),
                    "checking_gain": float(vals[names.index("checking_gain")]),
                }
            )

        for difficulty in DIFFICULTY_ORDER:
            indices = np.asarray([i for i, task in enumerate(metadata) if task["difficulty"] == difficulty])
            vals = mean_for_indices(endpoints, indices)
            difficulty_rows.append(
                {
                    "model_slug": cell["model_slug"],
                    "model_label": MODEL_LABELS[cell["model_slug"]],
                    "seed": cell["seed"],
                    "difficulty": difficulty,
                    "n_tasks": len(indices),
                    **{name: float(value) for name, value in zip(names, vals, strict=True)},
                }
            )

        diagnostic_rows.append(
            {
                "model_slug": cell["model_slug"],
                "model_label": MODEL_LABELS[cell["model_slug"]],
                "seed": cell["seed"],
                "protocol_status": cell["protocol_status"],
                "max_new_token_budgets": json.dumps(cell["max_new_token_budgets"]),
                "diagnostic_status": cell["quality_status"],
                "parse_failure_rate": cell["parse_failure_rate"],
                "truncation_rate": cell["truncation_rate"],
                "included_in_primary": True,
            }
        )

    model_scorecards: list[dict[str, Any]] = []
    model_condition_rows: list[dict[str, Any]] = []
    model_family_rows: list[dict[str, Any]] = []
    model_difficulty_rows: list[dict[str, Any]] = []
    seed_stability_rows: list[dict[str, Any]] = []
    paired_diagnostic_rows: list[dict[str, Any]] = []
    protocol_sensitivity_rows: list[dict[str, Any]] = []

    for model_index, slug in enumerate(MODEL_ORDER):
        model_entries = [matrices[(slug, seed)] for seed in ["16061", "16101", "16102", "19003-heldout"]]
        all_endpoints = np.concatenate([entry["endpoints"] for entry in model_entries], axis=0)
        all_metadata = [task for entry in model_entries for task in entry["metadata"]]
        strata = []
        offset = 0
        for entry in model_entries:
            for family in FAMILY_ORDER:
                local = [i for i, task in enumerate(entry["metadata"]) if task["family"] == family]
                strata.append(np.asarray([offset + i for i in local], dtype=int))
            offset += len(entry["metadata"])
        low, high = stratified_bootstrap(
            all_endpoints,
            strata,
            bootstrap_resamples,
            seed=20260813 + 1000 * model_index,
        )
        means = np.asarray([all_endpoints[index].mean(axis=0) for index in strata]).mean(axis=0)
        row: dict[str, Any] = {
            "model_slug": slug,
            "model_label": MODEL_LABELS[slug],
            "n_seeds": 4,
            "n_tasks": len(all_metadata),
            "included_quality_flagged_cells": sum(entry["cell"]["quality_status"] != "quality_gate_pass" for entry in model_entries),
            "included_mixed_budget_cells": sum(entry["cell"]["protocol_status"] != "homogeneous" for entry in model_entries),
        }
        for index, name in enumerate(names):
            row[name] = float(means[index])
            row[f"{name}_ci_low"] = float(low[index])
            row[f"{name}_ci_high"] = float(high[index])
        model_scorecards.append(row)

        homogeneous_entries = [entry for entry in model_entries if entry["cell"]["protocol_status"] == "homogeneous"]
        homogeneous_endpoint_means = []
        for entry in homogeneous_entries:
            for family in FAMILY_ORDER:
                idx = np.asarray([i for i, task in enumerate(entry["metadata"]) if task["family"] == family])
                homogeneous_endpoint_means.append(entry["endpoints"][idx].mean(axis=0))
        homogeneous_mean = np.asarray(homogeneous_endpoint_means).mean(axis=0)
        protocol_row: dict[str, Any] = {
            "model_slug": slug,
            "model_label": MODEL_LABELS[slug],
            "inclusive_seeds": len(model_entries),
            "homogeneous_only_seeds": len(homogeneous_entries),
        }
        for index, endpoint in enumerate(names):
            protocol_row[f"inclusive_{endpoint}"] = float(means[index])
            protocol_row[f"homogeneous_only_{endpoint}"] = float(homogeneous_mean[index])
            protocol_row[f"inclusive_minus_homogeneous_{endpoint}"] = float(means[index] - homogeneous_mean[index])
        protocol_sensitivity_rows.append(protocol_row)

        # Accuracy/token summaries retain equal seed-family weighting for accuracy;
        # tokens and diagnostics are descriptive response-level means.
        for ti, template in enumerate(TEMPLATES):
            for ci, condition in enumerate(CONDITIONS):
                seed_family_accuracy = []
                token_values = []
                parse_values = []
                trunc_values = []
                for entry in model_entries:
                    for family in FAMILY_ORDER:
                        idx = np.asarray([i for i, task in enumerate(entry["metadata"]) if task["family"] == family])
                        seed_family_accuracy.append(float(entry["scores"][idx, ti, ci].mean()))
                    token_values.extend(entry["tokens"][:, ti, ci].tolist())
                    parse_values.extend(entry["parses"][:, ti, ci].tolist())
                    trunc_values.extend(entry["truncs"][:, ti, ci].tolist())
                model_condition_rows.append(
                    {
                        "model_slug": slug,
                        "model_label": MODEL_LABELS[slug],
                        "task_template": template,
                        "template_label": TEMPLATE_LABELS[template],
                        "condition": condition,
                        "condition_label": CONDITION_LABELS[condition],
                        "n_tasks": 6400,
                        "accuracy_macro": statistics.mean(seed_family_accuracy),
                        "mean_generated_tokens": statistics.mean(token_values),
                        "parse_failure_rate": statistics.mean(parse_values),
                        "truncation_rate": statistics.mean(trunc_values),
                    }
                )

            all_family_differences = []
            complete_family_differences = []
            retained = 0
            total = 0
            check_index = CONDITIONS.index("common_check")
            compound_index = CONDITIONS.index("common_self_doubt_check")
            for entry in model_entries:
                for family in FAMILY_ORDER:
                    idx = np.asarray([i for i, task in enumerate(entry["metadata"]) if task["family"] == family])
                    differences = entry["scores"][idx, ti, compound_index] - entry["scores"][idx, ti, check_index]
                    complete = (
                        (entry["parses"][idx, ti, compound_index] == 0)
                        & (entry["parses"][idx, ti, check_index] == 0)
                        & (entry["truncs"][idx, ti, compound_index] == 0)
                        & (entry["truncs"][idx, ti, check_index] == 0)
                    )
                    all_family_differences.append(float(differences.mean()))
                    if complete.any():
                        complete_family_differences.append(float(differences[complete].mean()))
                    retained += int(complete.sum())
                    total += len(complete)
            paired_diagnostic_rows.append(
                {
                    "model_slug": slug,
                    "model_label": MODEL_LABELS[slug],
                    "task_template": template,
                    "all_tasks_cde": statistics.mean(all_family_differences),
                    "diagnostic_complete_pair_cde": statistics.mean(complete_family_differences),
                    "complete_pair_minus_all_tasks": statistics.mean(complete_family_differences) - statistics.mean(all_family_differences),
                    "retained_pairs": retained,
                    "total_pairs": total,
                    "retained_rate": retained / total,
                    "note": "Complete-pair estimate is diagnostic only; inclusive all-task CDE remains primary.",
                }
            )

        for family in FAMILY_ORDER:
            subset = [row for row in family_rows if row["model_slug"] == slug and row["family"] == family and row["task_template"] == "average"]
            model_family_rows.append(
                {
                    "model_slug": slug,
                    "model_label": MODEL_LABELS[slug],
                    "family": family,
                    "family_label": FAMILY_LABELS[family],
                    "n_seeds": len(subset),
                    "cde": statistics.mean(float(row["cde"]) for row in subset),
                    "checking_gain": statistics.mean(float(row["checking_gain"]) for row in subset),
                    "cde_min": min(float(row["cde"]) for row in subset),
                    "cde_max": max(float(row["cde"]) for row in subset),
                }
            )
        for difficulty in DIFFICULTY_ORDER:
            subset = [row for row in difficulty_rows if row["model_slug"] == slug and row["difficulty"] == difficulty]
            model_difficulty_rows.append(
                {
                    "model_slug": slug,
                    "model_label": MODEL_LABELS[slug],
                    "difficulty": difficulty,
                    "n_seeds": len(subset),
                    **{name: statistics.mean(float(row[name]) for row in subset) for name in names},
                }
            )

        for endpoint in ["neutral_accuracy", "checking_gain", "cde", "cde_minimal", "cde_reasoning", "context_modulation", "concision_effect"]:
            values = [float(row[endpoint]) for row in seed_scorecards if row["model_slug"] == slug]
            seed_stability_rows.append(
                {
                    "model_slug": slug,
                    "model_label": MODEL_LABELS[slug],
                    "endpoint": endpoint,
                    "mean": statistics.mean(values),
                    "sample_sd": statistics.stdev(values),
                    "min": min(values),
                    "max": max(values),
                    "positive_seeds": sum(value > 0 for value in values),
                    "negative_seeds": sum(value < 0 for value in values),
                    "zero_seeds": sum(value == 0 for value in values),
                }
            )

    write_csv(OUT / "scorecard_by_model_seed.csv", seed_scorecards)
    write_csv(OUT / "scorecard_by_model.csv", model_scorecards)
    write_csv(OUT / "condition_accuracy_by_cell.csv", condition_rows)
    write_csv(OUT / "condition_accuracy_by_model.csv", model_condition_rows)
    write_csv(OUT / "family_effects_by_cell.csv", family_rows)
    write_csv(OUT / "family_effects_by_model.csv", model_family_rows)
    write_csv(OUT / "difficulty_effects_by_cell.csv", difficulty_rows)
    write_csv(OUT / "difficulty_effects_by_model.csv", model_difficulty_rows)
    write_csv(OUT / "seed_stability.csv", seed_stability_rows)
    write_csv(OUT / "included_cell_diagnostics.csv", diagnostic_rows)
    write_csv(OUT / "paired_diagnostic_sensitivity.csv", paired_diagnostic_rows)
    write_csv(OUT / "mixed_budget_protocol_sensitivity.csv", protocol_sensitivity_rows)

    return {
        "matrices": matrices,
        "model_scorecards": model_scorecards,
        "seed_scorecards": seed_scorecards,
        "model_condition_rows": model_condition_rows,
        "model_family_rows": model_family_rows,
        "model_difficulty_rows": model_difficulty_rows,
        "seed_stability_rows": seed_stability_rows,
        "endpoint_names": names,
    }


def surface_analysis(cells: list[dict[str, Any]], factorial: dict[str, Any]) -> dict[str, Any]:
    metadata_map = surface_metadata()
    surface_cells = [cell for cell in cells if cell["kind"] == "surface-robustness"]
    accuracy_rows: list[dict[str, Any]] = []
    cde_rows: list[dict[str, Any]] = []
    consistency_rows: list[dict[str, Any]] = []

    for cell in sorted(surface_cells, key=lambda item: MODEL_ORDER.index(item["model_slug"])):
        slug = cell["model_slug"]
        surface_meta, surface_scores, _, _, _ = task_matrix(source_rows(cell))
        by_variant_base: dict[tuple[str, str], int] = {}
        canonical_ids: dict[str, str] = {}
        for index, task in enumerate(surface_meta):
            info = metadata_map[task["sample_id"]]
            base = info["paired_latent_task_id"]
            by_variant_base[(info["variant"], base)] = index
            canonical_ids[base] = canonical_heldout_id(base, info["legacy_task_id"])

        heldout = factorial["matrices"][(slug, "19003-heldout")]
        heldout_lookup = {task["sample_id"]: i for i, task in enumerate(heldout["metadata"])}
        bases = sorted(canonical_ids)
        missing = [canonical_ids[base] for base in bases if canonical_ids[base] not in heldout_lookup]
        if missing:
            raise RuntimeError(f"Could not map {len(missing)} surface tasks to held-out canonical tasks: {missing[:3]}")

        forms = {
            "canonical": np.stack([heldout["scores"][heldout_lookup[canonical_ids[base]]] for base in bases]),
            "structured": np.stack([surface_scores[by_variant_base[("structured", base)]] for base in bases]),
            "scenario": np.stack([surface_scores[by_variant_base[("scenario", base)]] for base in bases]),
        }
        for form, scores in forms.items():
            for ti, template in enumerate(TEMPLATES):
                for ci, condition in enumerate(CONDITIONS):
                    accuracy_rows.append(
                        {
                            "model_slug": slug,
                            "model_label": MODEL_LABELS[slug],
                            "surface_form": form,
                            "task_template": template,
                            "condition": condition,
                            "n_tasks": len(bases),
                            "accuracy": float(scores[:, ti, ci].mean()),
                        }
                    )
                cde_rows.append(
                    {
                        "model_slug": slug,
                        "model_label": MODEL_LABELS[slug],
                        "surface_form": form,
                        "task_template": template,
                        "n_tasks": len(bases),
                        "cde": float((scores[:, ti, CONDITIONS.index("common_self_doubt_check")] - scores[:, ti, CONDITIONS.index("common_check")]).mean()),
                        "checking_gain": float((scores[:, ti, CONDITIONS.index("common_check")] - scores[:, ti, CONDITIONS.index("common_neutral")]).mean()),
                    }
                )

        for ti, template in enumerate(TEMPLATES):
            for ci, condition in enumerate(CONDITIONS):
                canonical = forms["canonical"][:, ti, ci]
                structured = forms["structured"][:, ti, ci]
                scenario = forms["scenario"][:, ti, ci]
                consistency_rows.append(
                    {
                        "model_slug": slug,
                        "model_label": MODEL_LABELS[slug],
                        "task_template": template,
                        "condition": condition,
                        "n_tasks": len(bases),
                        "canonical_structured_agreement": float((canonical == structured).mean()),
                        "canonical_scenario_agreement": float((canonical == scenario).mean()),
                        "structured_scenario_agreement": float((structured == scenario).mean()),
                        "all_three_agreement": float(((canonical == structured) & (structured == scenario)).mean()),
                        "robust_all_correct": float(((canonical == 1) & (structured == 1) & (scenario == 1)).mean()),
                    }
                )

    write_csv(OUT / "surface_accuracy.csv", accuracy_rows)
    write_csv(OUT / "surface_effects.csv", cde_rows)
    write_csv(OUT / "surface_consistency.csv", consistency_rows)
    return {"accuracy": accuracy_rows, "effects": cde_rows, "consistency": consistency_rows}


def posttraining_analysis(factorial: dict[str, Any]) -> list[dict[str, Any]]:
    scorecards = {row["model_slug"]: row for row in factorial["model_scorecards"]}
    sft = scorecards["tulu3-sft-8b"]
    dpo = scorecards["tulu3-dpo-8b"]
    endpoints = factorial["endpoint_names"]
    rows = []
    for endpoint in endpoints:
        rows.append(
            {
                "endpoint": endpoint,
                "tulu_sft": sft[endpoint],
                "tulu_dpo": dpo[endpoint],
                "dpo_minus_sft": dpo[endpoint] - sft[endpoint],
            }
        )
    write_csv(OUT / "tulu_posttraining_case_study.csv", rows)
    return rows


def key_observations(factorial: dict[str, Any], surface: dict[str, Any], posttraining: list[dict[str, Any]]) -> dict[str, Any]:
    cards = factorial["model_scorecards"]
    cde_values = [float(row["cde"]) for row in cards]
    minimal = [float(row["cde_minimal"]) for row in cards]
    reasoning = [float(row["cde_reasoning"]) for row in cards]
    check_gains = [float(row["checking_gain"]) for row in cards]
    condition_lookup = {
        (row["model_slug"], row["task_template"], row["condition"]): row
        for row in factorial["model_condition_rows"]
    }
    concise_costs = []
    token_reductions = []
    for slug in MODEL_ORDER:
        for template in TEMPLATES:
            check = condition_lookup[(slug, template, "common_check")]
            concise = condition_lookup[(slug, template, "common_check_concise")]
            concise_costs.append(float(concise["accuracy_macro"]) - float(check["accuracy_macro"]))
            token_reductions.append(float(concise["mean_generated_tokens"]) - float(check["mean_generated_tokens"]))

    family_rows = factorial["model_family_rows"]
    family_cde = defaultdict(list)
    for row in family_rows:
        family_cde[row["family"]].append(float(row["cde"]))
    family_means = {key: statistics.mean(values) for key, values in family_cde.items()}

    surface_effects = surface["effects"]
    surface_lookup = defaultdict(dict)
    for row in surface_effects:
        surface_lookup[(row["model_slug"], row["task_template"])][row["surface_form"]] = float(row["cde"])
    surface_cde_shifts = []
    for forms in surface_lookup.values():
        surface_cde_shifts.extend([forms["structured"] - forms["canonical"], forms["scenario"] - forms["canonical"]])

    consistency = surface["consistency"]
    all_three = [float(row["all_three_agreement"]) for row in consistency]
    pt = {row["endpoint"]: row for row in posttraining}

    return {
        "models_with_positive_overall_cde": sum(value > 0 for value in cde_values),
        "models_with_negative_overall_cde": sum(value < 0 for value in cde_values),
        "overall_cde_range": [min(cde_values), max(cde_values)],
        "models_positive_cde_minimal": sum(value > 0 for value in minimal),
        "models_positive_cde_reasoning": sum(value > 0 for value in reasoning),
        "median_checking_gain": statistics.median(check_gains),
        "checking_gain_range": [min(check_gains), max(check_gains)],
        "median_concision_accuracy_effect": statistics.median(concise_costs),
        "median_concision_token_effect": statistics.median(token_reductions),
        "largest_positive_family_mean_cde": max(family_means.items(), key=lambda item: item[1]),
        "largest_negative_family_mean_cde": min(family_means.items(), key=lambda item: item[1]),
        "surface_cde_shift_abs_median": statistics.median(abs(value) for value in surface_cde_shifts),
        "surface_all_three_correctness_agreement_mean": statistics.mean(all_three),
        "tulu_dpo_minus_sft_cde": pt["cde"]["dpo_minus_sft"],
        "tulu_dpo_minus_sft_cde_minimal": pt["cde_minimal"]["dpo_minus_sft"],
        "tulu_dpo_minus_sft_cde_reasoning": pt["cde_reasoning"]["dpo_minus_sft"],
    }


def build_integrity(cells: list[dict[str, Any]]) -> dict[str, Any]:
    factorial = [cell for cell in cells if cell["kind"] == "factorial"]
    surface = [cell for cell in cells if cell["kind"] == "surface-robustness"]
    return {
        "analysis_policy": "inclusive_all_structurally_complete_cells",
        "factorial_cells": len(factorial),
        "surface_cells": len(surface),
        "factorial_responses": sum(int(cell["observed_rows"]) for cell in factorial),
        "surface_responses": sum(int(cell["observed_rows"]) for cell in surface),
        "total_responses": sum(int(cell["observed_rows"]) for cell in cells),
        "factorial_latent_tasks": 6400,
        "surface_latent_tasks": 330,
        "surface_rendered_tasks": 660,
        "checkpoints": len({cell["model_slug"] for cell in cells}),
        "independent_foundation_families": 4,
        "task_seeds": 4,
        "task_families": 8,
        "task_types": 33,
        "prompt_conditions": 5,
        "task_contexts": 2,
        "mixed_budget_cells_included": sum(cell["protocol_status"] != "homogeneous" for cell in factorial),
        "diagnostic_flagged_cells_included": sum(cell["quality_status"] != "quality_gate_pass" for cell in cells),
    }


def main() -> None:
    parser_resamples = 3000
    OUT.mkdir(parents=True, exist_ok=True)
    cells = json.loads((RESULTS / "manifests" / "canonical_cells.json").read_text())
    integrity = build_integrity(cells)
    factorial = factorial_analysis(cells, bootstrap_resamples=parser_resamples)
    surface = surface_analysis(cells, factorial)
    posttraining = posttraining_analysis(factorial)
    observations = key_observations(factorial, surface, posttraining)
    write_json(OUT / "analysis_summary.json", {"integrity": integrity, "observations": observations})
    print(json.dumps({"integrity": integrity, "observations": observations}, indent=2))


if __name__ == "__main__":
    main()
