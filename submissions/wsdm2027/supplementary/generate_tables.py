#!/usr/bin/env python3
"""Generate reviewer-facing LaTeX tables for the DoubtBench supplement.

The source CSV files are the frozen inclusive analysis tables.  This script
changes labels and formatting only; it does not recompute experiment metrics.
"""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / "submissions" / "cods2026" / "results" / "analysis" / "inclusive"
OUT = Path(__file__).resolve().parent / "tables"

MODELS = [
    "qwen2.5-7b",
    "mistral7b",
    "llama3.1-8b",
    "phi3.5-mini",
    "tulu3-sft-8b",
    "tulu3-dpo-8b",
]
MODEL_LABEL = {
    "qwen2.5-7b": "Qwen 2.5 7B",
    "mistral7b": "Mistral 7B",
    "llama3.1-8b": "Llama 3.1 8B",
    "phi3.5-mini": "Phi 3.5 Mini",
    "tulu3-sft-8b": "Tulu 3 SFT 8B",
    "tulu3-dpo-8b": "Tulu 3 DPO 8B",
}
FAMILIES = [
    "working_memory",
    "inhibition",
    "flexibility",
    "rule_learning",
    "monitoring",
    "planning",
    "relational_integration",
    "goal_management",
]
FAMILY_SHORT = {
    "working_memory": "Memory",
    "inhibition": "Inhibition",
    "flexibility": "Switching",
    "rule_learning": "Rule learn.",
    "monitoring": "Monitoring",
    "planning": "Planning",
    "relational_integration": "Relations",
    "goal_management": "Goals",
}
CONDITIONS = [
    "common_neutral",
    "common_self_doubt",
    "common_check",
    "common_self_doubt_check",
    "common_check_concise",
]
CONDITION_SHORT = {
    "common_neutral": "Neutral",
    "common_self_doubt": "Doubt",
    "common_check": "Check",
    "common_self_doubt_check": "Doubt+check",
    "common_check_concise": "Check+concise",
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (ANALYSIS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def esc(value: str) -> str:
    return (
        value.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def pp(value: str, signed: bool = False) -> str:
    number = (Decimal(value) * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{number:+.2f}" if signed else f"{number:.2f}"


def write(name: str, lines: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def scorecard() -> None:
    rows = {row["model_slug"]: row for row in read_csv("scorecard_by_model.csv")}
    lines = [
        r"\begin{table*}[t]",
        r"\centering\scriptsize",
        r"\caption{Complete checkpoint scorecard. Neutral is exact accuracy in percent; all other numerical entries are percentage-point effects. CDE intervals are paired task-bootstrap intervals.}",
        r"\label{tab:scorecard}",
        r"\begin{tabular}{@{}lrrrrrrr@{}}",
        r"\toprule",
        r"Checkpoint & Neutral & Check gain & CDE [95\% CI] & CDE$_{\min}$ & CDE$_{\mathrm{reason}}$ & Context mod. & Concision \\",
        r"\midrule",
    ]
    for model in MODELS:
        row = rows[model]
        ci = (
            f"{pp(row['cde'], True)} "
            f"[{pp(row['cde_ci_low'], True)}, {pp(row['cde_ci_high'], True)}]"
        )
        lines.append(
            " & ".join(
                [
                    MODEL_LABEL[model],
                    pp(row["neutral_accuracy"]),
                    pp(row["checking_gain"], True),
                    ci,
                    pp(row["cde_minimal"], True),
                    pp(row["cde_reasoning"], True),
                    pp(row["context_modulation"], True),
                    pp(row["concision_effect"], True),
                ]
            )
            + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    write("scorecard.tex", lines)


def condition_accuracy() -> None:
    raw = read_csv("condition_accuracy_by_model.csv")
    lookup = {
        (r["model_slug"], r["task_template"], r["condition"]): r for r in raw
    }
    lines = [
        r"\begin{table*}[t]",
        r"\centering\scriptsize",
        r"\caption{Macro exact accuracy (percent) in every prompt-condition and task-context cell, averaged equally over four task seeds and eight families.}",
        r"\label{tab:condition-accuracy}",
        r"\begin{tabular}{@{}llrrrrr@{}}",
        r"\toprule",
        r"Checkpoint & Task context & Neutral & Doubt & Check & Doubt+check & Check+concise \\",
        r"\midrule",
    ]
    for model in MODELS:
        for template, label in [("minimal", "Minimal"), ("reasoning_requested", "Reasoning requested")]:
            values = [pp(lookup[(model, template, c)]["accuracy_macro"]) for c in CONDITIONS]
            lines.append(" & ".join([MODEL_LABEL[model], label, *values]) + r" \\")
        if model != MODELS[-1]:
            lines.append(r"\addlinespace[1.5pt]")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    write("condition_accuracy.tex", lines)


def by_seed() -> None:
    raw = read_csv("scorecard_by_model_seed.csv")
    lookup = {(r["model_slug"], r["seed"]): r for r in raw}
    seed_keys = ["16061", "16101", "16102", "19003-heldout"]
    lines = [
        r"\begin{table}[t]",
        r"\centering\scriptsize",
        r"\caption{Overall CDE (percentage points) in each independently seeded task set. The final column is the four-set mean.}",
        r"\label{tab:seed-cde}",
        r"\begin{tabular}{@{}lrrrrr@{}}",
        r"\toprule",
        r"Checkpoint & 16061 & 16101 & 16102 & 19003 & Mean \\",
        r"\midrule",
    ]
    for model in MODELS:
        vals = [pp(lookup[(model, seed)]["cde"], True) for seed in seed_keys]
        mean = sum(float(lookup[(model, seed)]["cde"]) for seed in seed_keys) / 4
        lines.append(" & ".join([MODEL_LABEL[model], *vals, f"{100*mean:+.2f}"]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("cde_by_seed.tex", lines)


def by_family() -> None:
    raw = read_csv("family_effects_by_model.csv")
    lookup = {(r["model_slug"], r["family"]): r for r in raw}
    lines = [
        r"\begin{table*}[t]",
        r"\centering\scriptsize",
        r"\caption{Task-family CDE in percentage points, averaged over four task seeds and both task contexts.}",
        r"\label{tab:family-cde}",
        r"\setlength{\tabcolsep}{3.4pt}",
        r"\begin{tabular}{@{}lrrrrrrrr@{}}",
        r"\toprule",
        "Checkpoint & " + " & ".join(FAMILY_SHORT[f] for f in FAMILIES) + r" \\",
        r"\midrule",
    ]
    for model in MODELS:
        vals = [pp(lookup[(model, family)]["cde"], True) for family in FAMILIES]
        lines.append(" & ".join([MODEL_LABEL[model], *vals]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    write("family_cde.tex", lines)


def by_difficulty() -> None:
    raw = read_csv("difficulty_effects_by_model.csv")
    lookup = {(r["model_slug"], r["difficulty"]): r for r in raw}
    lines = [
        r"\begin{table}[t]",
        r"\centering\scriptsize",
        r"\caption{CDE by generated difficulty (percentage points), averaged over four task seeds and both contexts.}",
        r"\label{tab:difficulty-cde}",
        r"\begin{tabular}{@{}lrrr@{}}",
        r"\toprule",
        r"Checkpoint & Easy & Medium & Hard \\",
        r"\midrule",
    ]
    for model in MODELS:
        vals = [pp(lookup[(model, d)]["cde"], True) for d in ["easy", "medium", "hard"]]
        lines.append(" & ".join([MODEL_LABEL[model], *vals]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("difficulty_cde.tex", lines)


def diagnostics() -> None:
    raw = read_csv("included_cell_diagnostics.csv")
    rows = [r for r in raw if r["diagnostic_status"] == "quality_gate_failure"]
    lines = [
        r"\begin{table}[t]",
        r"\centering\scriptsize",
        r"\caption{Structurally complete factorial evaluations exceeding the 2\% diagnostic threshold. Rates are percentages over all 16,000 responses in the checkpoint--task-set evaluation.}",
        r"\label{tab:alerts}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Checkpoint & Task seed & Output limit & Parse failure & Truncation \\",
        r"\midrule",
    ]
    for r in rows:
        budget = "384/768" if "384" in r["max_new_token_budgets"] else "768"
        seed = r["seed"].replace("-heldout", "")
        lines.append(
            " & ".join(
                [
                    r["model_label"],
                    seed,
                    budget,
                    pp(r["parse_failure_rate"]) + r"\%",
                    pp(r["truncation_rate"]) + r"\%",
                ]
            )
            + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("diagnostic_alerts.tex", lines)


def complete_pair_sensitivity() -> None:
    raw = read_csv("paired_diagnostic_sensitivity.csv")
    lines = [
        r"\begin{table*}[t]",
        r"\centering\scriptsize",
        r"\caption{CDE sensitivity to retaining only complete checking and self-doubt-plus-checking response pairs. CDE and differences are percentage points.}",
        r"\label{tab:complete-pairs}",
        r"\begin{tabular}{@{}llrrrr@{}}",
        r"\toprule",
        r"Checkpoint & Context & All tasks & Complete pairs & Difference & Retained \\",
        r"\midrule",
    ]
    for model in MODELS:
        for r in [x for x in raw if x["model_slug"] == model]:
            label = "Minimal" if r["task_template"] == "minimal" else "Reasoning requested"
            lines.append(
                " & ".join(
                    [
                        MODEL_LABEL[model],
                        label,
                        pp(r["all_tasks_cde"], True),
                        pp(r["diagnostic_complete_pair_cde"], True),
                        pp(r["complete_pair_minus_all_tasks"], True),
                        f"{int(r['retained_pairs']):,}/{int(r['total_pairs']):,}",
                    ]
                )
                + r" \\"
            )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    write("complete_pair_sensitivity.tex", lines)


def budget_sensitivity() -> None:
    raw = read_csv("mixed_budget_protocol_sensitivity.csv")
    rows = [r for r in raw if r["inclusive_seeds"] != r["homogeneous_only_seeds"]]
    lines = [
        r"\begin{table}[t]",
        r"\centering\scriptsize",
        r"\caption{Overall CDE with all four task sets and with only homogeneous 768-token task sets. Values are percentage points.}",
        r"\label{tab:budget}",
        r"\begin{tabular}{@{}lrrr@{}}",
        r"\toprule",
        r"Checkpoint & All four sets & 768-token sets & Difference \\",
        r"\midrule",
    ]
    for r in rows:
        lines.append(
            " & ".join(
                [
                    r["model_label"],
                    pp(r["inclusive_cde"], True),
                    pp(r["homogeneous_only_cde"], True),
                    pp(r["inclusive_minus_homogeneous_cde"], True),
                ]
            )
            + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("budget_sensitivity.tex", lines)


def surface_cde() -> None:
    raw = read_csv("surface_effects.csv")
    lookup = {
        (r["model_slug"], r["task_template"], r["surface_form"]): r for r in raw
    }
    lines = [
        r"\begin{table}[t]",
        r"\centering\scriptsize",
        r"\caption{Surface-form CDE in percentage points on the same 330 latent tasks.}",
        r"\label{tab:surface-cde}",
        r"\begin{tabular}{@{}llrrr@{}}",
        r"\toprule",
        r"Checkpoint & Context & Canonical & Structured & Scenario \\",
        r"\midrule",
    ]
    for model in MODELS:
        for template, label in [("minimal", "Minimal"), ("reasoning_requested", "Reasoning")]:
            vals = [pp(lookup[(model, template, s)]["cde"], True) for s in ["canonical", "structured", "scenario"]]
            lines.append(" & ".join([MODEL_LABEL[model], label, *vals]) + r" \\")
        if model != MODELS[-1]:
            lines.append(r"\addlinespace[1.5pt]")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("surface_cde.tex", lines)


def main() -> None:
    scorecard()
    condition_accuracy()
    by_seed()
    by_family()
    by_difficulty()
    diagnostics()
    complete_pair_sensitivity()
    budget_sensitivity()
    surface_cde()


if __name__ == "__main__":
    main()
