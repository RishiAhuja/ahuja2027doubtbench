#!/usr/bin/env python3
"""Create CAISc paper figures from final EXP-16 analysis tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = ROOT / "outputs" / "analysis" / "exp16_final_mechanism_20260529"
FIG_DIR = Path(__file__).resolve().parent / "figures"

MODEL_LABELS = {
    "Qwen/Qwen2.5-7B-Instruct": "Qwen2.5-7B",
    "meta-llama/Llama-3.1-8B-Instruct": "Llama-3.1-8B",
    "allenai/Llama-3.1-Tulu-3-8B-DPO": "Tulu-3-DPO-8B",
}

CONDITION_LABELS = {
    "baseline": "Baseline",
    "self_doubt_only": "Self-doubt",
    "check_your_work": "Check work",
    "think_step_by_step": "Step-by-step",
    "be_careful": "Careful",
    "answer_concisely": "Concise",
    "self_doubt_but_answer_concisely": "Doubt+concise",
    "capability_denial_only": "Capability denial",
    "explicit_sabotage": "Sabotage",
    "baseline_forced_step_by_step": "Forced steps",
    "check_your_work_concise": "Check+concise",
    "think_step_by_step_concise": "Steps+concise",
}

COLORS = {
    "Qwen2.5-7B": "#0072B2",
    "Llama-3.1-8B": "#D55E00",
    "Tulu-3-DPO-8B": "#009E73",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def mechanism_delta_by_model() -> None:
    df = pd.read_csv(ANALYSIS_DIR / "pooled_mechanism_condition_summary.csv")
    conditions = [
        "self_doubt_only",
        "check_your_work",
        "think_step_by_step",
        "be_careful",
        "answer_concisely",
        "self_doubt_but_answer_concisely",
        "capability_denial_only",
        "explicit_sabotage",
    ]
    models = [
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "allenai/Llama-3.1-Tulu-3-8B-DPO",
    ]

    x = np.arange(len(conditions))
    width = 0.24
    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    for idx, model in enumerate(models):
        sub = df[(df["model"] == model) & (df["condition"].isin(conditions))]
        sub = sub.set_index("condition").loc[conditions].reset_index()
        y = sub["delta_vs_baseline"].to_numpy() * 100
        lower = (sub["delta_vs_baseline"] - sub["ci_low"]).to_numpy() * 100
        upper = (sub["ci_high"] - sub["delta_vs_baseline"]).to_numpy() * 100
        label = MODEL_LABELS[model]
        ax.bar(
            x + (idx - 1) * width,
            y,
            width=width,
            label=label,
            color=COLORS[label],
            alpha=0.88,
            edgecolor="black",
            linewidth=0.25,
        )
        ax.errorbar(
            x + (idx - 1) * width,
            y,
            yerr=[lower, upper],
            fmt="none",
            ecolor="black",
            elinewidth=0.55,
            capsize=1.8,
            capthick=0.55,
        )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Accuracy delta vs. baseline (pp)")
    ax.set_xticks(x)
    ax.set_xticklabels([CONDITION_LABELS[c] for c in conditions], rotation=25, ha="right")
    ax.set_ylim(-30, 45)
    ax.grid(axis="y", color="#cccccc", linewidth=0.4, alpha=0.65)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    save(fig, "mechanism_delta_by_model")


def qwen_budget_control() -> None:
    df = pd.read_csv(ANALYSIS_DIR / "budget_control_qwen_summary.csv")
    conditions = [
        "baseline",
        "self_doubt_only",
        "check_your_work",
        "think_step_by_step",
        "baseline_forced_step_by_step",
        "answer_concisely",
        "self_doubt_but_answer_concisely",
        "check_your_work_concise",
        "think_step_by_step_concise",
    ]
    df = df.set_index("condition").loc[conditions].reset_index()
    labels = [CONDITION_LABELS[c] for c in conditions]
    x = np.arange(len(conditions))

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), sharex=True)

    axes[0].bar(x, df["accuracy"] * 100, color="#0072B2", alpha=0.88, edgecolor="black", linewidth=0.25)
    axes[0].set_ylabel("Accuracy (%)")
    axes[0].set_ylim(0, 95)
    axes[0].axhline(df.loc[df["condition"] == "baseline", "accuracy"].item() * 100, color="black", linewidth=0.8, linestyle="--")
    axes[0].grid(axis="y", color="#cccccc", linewidth=0.4, alpha=0.65)

    axes[1].bar(x, df["mean_generated_tokens"], color="#CC79A7", alpha=0.88, edgecolor="black", linewidth=0.25)
    axes[1].set_ylabel("Mean generated tokens")
    axes[1].set_ylim(0, 175)
    axes[1].axhline(df.loc[df["condition"] == "baseline", "mean_generated_tokens"].item(), color="black", linewidth=0.8, linestyle="--")
    axes[1].grid(axis="y", color="#cccccc", linewidth=0.4, alpha=0.65)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right")
    save(fig, "qwen_budget_control")


def qwen_seed_robustness() -> None:
    df = pd.read_csv(ANALYSIS_DIR / "seed_mechanism_summary.csv")
    df = df[df["model"] == "Qwen/Qwen2.5-7B-Instruct"].copy()
    conditions = [
        "self_doubt_only",
        "check_your_work",
        "think_step_by_step",
        "answer_concisely",
        "self_doubt_but_answer_concisely",
    ]
    seeds = sorted(df["seed"].unique())
    x = np.arange(len(seeds))
    fig, ax = plt.subplots(figsize=(6.0, 3.1))
    palette = ["#0072B2", "#009E73", "#D55E00", "#CC79A7", "#999999"]

    for color, condition in zip(palette, conditions, strict=True):
        sub = df[df["condition"] == condition].set_index("seed").loc[seeds]
        ax.plot(
            x,
            sub["delta_vs_baseline"] * 100,
            marker="o",
            linewidth=1.4,
            markersize=4,
            color=color,
            label=CONDITION_LABELS[condition],
        )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["seed 1", "seed 2", "seed 3"])
    ax.set_ylabel("Qwen2.5 delta (pp)")
    ax.set_ylim(-22, 43)
    ax.grid(axis="y", color="#cccccc", linewidth=0.4, alpha=0.65)
    ax.legend(
        ncol=3,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        handlelength=2.2,
        columnspacing=1.4,
    )
    save(fig, "qwen_seed_robustness")


def main() -> int:
    set_style()
    mechanism_delta_by_model()
    qwen_budget_control()
    qwen_seed_robustness()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
