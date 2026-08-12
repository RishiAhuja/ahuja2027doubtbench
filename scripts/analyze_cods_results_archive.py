#!/usr/bin/env python3
"""Create compact paper-facing tables from the canonical CODS archive."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "submissions" / "cods2026" / "results"


def main() -> None:
    cells = json.loads((RESULTS / "manifests" / "canonical_cells.json").read_text())
    rows = []
    for cell in cells:
        summary = json.loads((RESULTS / cell["canonical_path"] / "summary.json").read_text())
        for contrast in summary["paired_contrasts"]:
            if contrast["comparison"] != "self_doubt_increment_over_check":
                continue
            rows.append(
                {
                    "kind": cell["kind"],
                    "model_slug": cell["model_slug"],
                    "model": cell["model"],
                    "seed": cell["seed"],
                    "task_template": contrast["task_template"],
                    "n_pairs": contrast["n_pairs"],
                    "cde": contrast["accuracy_delta"],
                    "ci_low": contrast["ci_low"],
                    "ci_high": contrast["ci_high"],
                    "protocol_status": cell["protocol_status"],
                    "quality_status": cell["quality_status"],
                    "parse_failure_rate": cell["parse_failure_rate"],
                    "truncation_rate": cell["truncation_rate"],
                }
            )

    analysis = RESULTS / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (analysis / "conditional_doubt_effect_by_cell.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    grouped = defaultdict(list)
    for row in rows:
        if row["kind"] == "factorial" and row["protocol_status"] == "homogeneous":
            grouped[(row["model_slug"], row["model"], row["task_template"])].append(row)
    aggregate = []
    for (slug, model, template), values in sorted(grouped.items()):
        cdes = [item["cde"] for item in values]
        aggregate.append(
            {
                "model_slug": slug,
                "model": model,
                "task_template": template,
                "homogeneous_cells": len(values),
                "quality_passing_cells": sum(item["quality_status"] == "quality_gate_pass" for item in values),
                "mean_cde": statistics.mean(cdes),
                "median_cde": statistics.median(cdes),
                "min_cde": min(cdes),
                "max_cde": max(cdes),
                "positive_cells": sum(value > 0 for value in cdes),
                "negative_cells": sum(value < 0 for value in cdes),
            }
        )
    with (analysis / "conditional_doubt_effect_by_model.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate[0]))
        writer.writeheader()
        writer.writerows(aggregate)

    build = json.loads((RESULTS / "manifests" / "build_info.json").read_text())
    failing = [
        cell for cell in cells
        if cell["quality_status"] != "quality_gate_pass" or cell["protocol_status"] != "homogeneous"
    ]
    text = [
        "# CODS result archive audit",
        "",
        "## Validated coverage",
        "",
        f"- `{build['canonical_factorial_cells']}` complete factorial cells: six models crossed with three development seeds and one held-out seed.",
        f"- `{build['protocol_homogeneous_factorial_cells']}` factorial cells use one token budget throughout; `{build['mixed_protocol_factorial_cells']}` historical composites mix budgets and are excluded from clean aggregate claims.",
        f"- `{build['canonical_surface_cells']}` complete surface-robustness cells, one per model.",
        f"- `{build['raw_runs_inventoried']}` raw run directories inventoried across local, FA0571, and Medha sources.",
        "- Every canonical cell was rebuilt from raw response keys and required exact task counts, exact row counts, model consistency, and zero overlap among composed segments.",
        "",
        "## Important protocol and quality flags",
        "",
    ]
    for cell in failing:
        text.append(
            f"- `{cell['kind']}/{cell['model_slug']}/{cell['seed']}`: "
            f"protocol=`{cell['protocol_status']}`, budgets=`{cell['max_new_token_budgets']}`, "
            f"quality=`{cell['quality_status']}`, parse={cell['parse_failure_rate']:.3%}, "
            f"truncation={cell['truncation_rate']:.3%}."
        )
    text.extend(
        [
            "",
            "## Conditional Doubt Effect",
            "",
            "CDE is computed within the same latent task and template as `Accuracy(doubt + check) - Accuracy(check)`. The model table below averages only protocol-homogeneous cells; quality-gate status remains reported separately rather than deleting difficult model outputs.",
            "",
            "| Model | Template | Cells | Passing | Mean CDE | Range | Signs (+/-) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in aggregate:
        text.append(
            f"| {item['model_slug']} | {item['task_template']} | {item['homogeneous_cells']} | "
            f"{item['quality_passing_cells']} | {item['mean_cde']:+.3f} | "
            f"[{item['min_cde']:+.3f}, {item['max_cde']:+.3f}] | "
            f"{item['positive_cells']}/{item['negative_cells']} |"
        )
    text.extend(
        [
            "",
            "## Interpretation constraints",
            "",
            "- Structural completion and quality-gate passage are different. Exit/status 3 runs retain all expected rows and metrics but exceed the predeclared 2% parse or truncation threshold.",
            "- Surface robustness is a separate 660-task evaluation and is never added to the 1,600-task factorial score.",
            "- Segment compositions are not independent replications; they are disjoint pieces of one seed-level cell.",
            "- The two mixed-budget seed-16061 composites are useful historical evidence but should not enter the clean homogeneous-protocol aggregate without a sensitivity analysis.",
            "- Medha's zero-row gated Llama-16102 failure is retained in provenance, while the canonical cell points to the completed FA0571 replacement.",
            "",
        ]
    )
    (analysis / "RESULTS_AUDIT.md").write_text("\n".join(text), encoding="utf-8")
    print(f"Wrote {len(rows)} cell contrasts and {len(aggregate)} model aggregates")


if __name__ == "__main__":
    main()
