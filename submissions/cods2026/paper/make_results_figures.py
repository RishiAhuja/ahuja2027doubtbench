#!/usr/bin/env python3
"""Build publication-ready CODS result figures from the inclusive tables."""

from __future__ import annotations

import csv
import html
import math
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANALYSIS = ROOT / "submissions" / "cods2026" / "results" / "analysis" / "inclusive"
FIG = HERE / "figures" / "results"
FIG.mkdir(parents=True, exist_ok=True)

C = {
    "blue": "#355C9A",
    "orange": "#C66A1B",
    "teal": "#16827C",
    "red": "#A63D4D",
    "ink": "#1D2733",
    "muted": "#677381",
    "grid": "#D9DEE5",
    "pale": "#F5F6F8",
    "white": "#FFFFFF",
}

MODEL_ORDER = [
    "qwen2.5-7b",
    "mistral7b",
    "llama3.1-8b",
    "phi3.5-mini",
    "tulu3-sft-8b",
    "tulu3-dpo-8b",
]
MODEL_LABELS = {
    "qwen2.5-7b": "Qwen 2.5 7B",
    "mistral7b": "Mistral 7B",
    "llama3.1-8b": "Llama 3.1 8B",
    "phi3.5-mini": "Phi 3.5 Mini",
    "tulu3-sft-8b": "Tulu 3 SFT 8B",
    "tulu3-dpo-8b": "Tulu 3 DPO 8B",
}
FAMILY_ORDER = [
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
    "working_memory": "Working\nmemory",
    "inhibition": "Inhibition",
    "flexibility": "Rule\nswitching",
    "rule_learning": "Novel-rule\nlearning",
    "monitoring": "Error\nmonitoring",
    "planning": "Planning",
    "relational_integration": "Relational\nintegration",
    "goal_management": "Goal\nmanagement",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class SVG:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        ]

    def line(self, x1, y1, x2, y2, stroke=C["grid"], width=1, dash=None, opacity=1):
        attrs = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{width}" opacity="{opacity}"{attrs}/>'
        )

    def rect(self, x, y, w, h, fill, stroke="none", width=1, radius=0, opacity=1):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"/>'
        )

    def circle(self, x, y, r, fill, stroke="none", width=1, opacity=1):
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" opacity="{opacity}"/>'
        )

    def text(self, x, y, value, size=12, fill=C["ink"], weight="normal", anchor="start", style="normal"):
        safe = html.escape(str(value))
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
            f'fill="{fill}" text-anchor="{anchor}">{safe}</text>'
        )

    def multiline(self, x, y, value, size=11, fill=C["ink"], leading=13, weight="normal", anchor="middle"):
        lines = str(value).split("\n")
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else leading}">{html.escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{spans}</text>'
        )

    def finish(self) -> str:
        return "\n".join(self.parts + ["</svg>"])


def write_and_convert(name: str, svg: SVG) -> None:
    svg_path = FIG / f"{name}.svg"
    svg_path.write_text(svg.finish(), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(FIG / f"{name}.pdf"), str(svg_path)], check=True)
    subprocess.run(
        [
            "rsvg-convert",
            "-f",
            "png",
            "-w",
            str(svg.width * 2),
            "-h",
            str(svg.height * 2),
            "-o",
            str(FIG / f"{name}.png"),
            str(svg_path),
        ],
        check=True,
    )


def xmap(value: float, lo: float, hi: float, left: float, right: float) -> float:
    return left + (value - lo) / (hi - lo) * (right - left)


def diverging_color(value: float, limit: float) -> str:
    value = max(-limit, min(limit, value)) / limit
    neutral = (247, 247, 247)
    negative = (53, 92, 154)
    positive = (166, 61, 77)
    target = positive if value >= 0 else negative
    weight = abs(value) ** 0.72
    rgb = tuple(round(neutral[i] * (1 - weight) + target[i] * weight) for i in range(3))
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def cde_context_forest() -> None:
    cards = {row["model_slug"]: row for row in read_csv(ANALYSIS / "scorecard_by_model.csv")}
    seeds = read_csv(ANALYSIS / "scorecard_by_model_seed.csv")
    s = SVG(980, 420)
    left, right, top, bottom = 235, 950, 75, 355
    lo, hi = -6.5, 7.0
    for tick in [-6, -4, -2, 0, 2, 4, 6]:
        x = xmap(tick, lo, hi, left, right)
        s.line(x, top, x, bottom, C["ink"] if tick == 0 else C["grid"], 1.3 if tick == 0 else 1)
        s.text(x, 383, f"{tick:+d}" if tick else "0", 10.5, C["muted"], anchor="middle")
    s.text(left, 47, "Doubt hurts beyond checking", 11, C["blue"])
    s.text(right, 47, "Doubt helps beyond checking", 11, C["red"], anchor="end")
    offsets = {"minimal": -8, "reasoning_requested": 8}
    colors = {"minimal": C["orange"], "reasoning_requested": C["teal"]}
    for i, slug in enumerate(MODEL_ORDER):
        y = top + 26 + i * 45
        s.text(left - 18, y + 4, MODEL_LABELS[slug], 11.5, anchor="end")
        if i % 2:
            s.rect(left, y - 20, right - left, 41, C["pale"])
        card = cards[slug]
        for template, endpoint in [("minimal", "cde_minimal"), ("reasoning_requested", "cde_reasoning")]:
            yy = y + offsets[template]
            color = colors[template]
            vals = [100 * float(row[endpoint]) for row in seeds if row["model_slug"] == slug]
            for value in vals:
                s.circle(xmap(value, lo, hi, left, right), yy, 2.8, C["white"], color, 1.2, 0.9)
            mean = 100 * float(card[endpoint])
            low = 100 * float(card[f"{endpoint}_ci_low"])
            high = 100 * float(card[f"{endpoint}_ci_high"])
            s.line(xmap(low, lo, hi, left, right), yy, xmap(high, lo, hi, left, right), yy, color, 2.5)
            s.circle(xmap(mean, lo, hi, left, right), yy, 4.6, color, C["white"], 1)
    for x, template, label in [(510, "minimal", "Minimal task request"), (680, "reasoning_requested", "Reasoning already requested")]:
        s.circle(x, 25, 4.5, colors[template])
        s.text(x + 10, 29, label, 10.5)
    s.text((left + right) / 2, 410, "Conditional Doubt Effect (percentage points)", 11.5, anchor="middle")
    write_and_convert("cde_context_forest", s)


def scorecard_heatmap() -> None:
    cards = {row["model_slug"]: row for row in read_csv(ANALYSIS / "scorecard_by_model.csv")}
    endpoints = [
        ("neutral_accuracy", "Neutral\naccuracy", False),
        ("doubt_gain", "Self-doubt\ngain", True),
        ("checking_gain", "Checking\ngain", True),
        ("cde", "Doubt beyond\nchecking", True),
        ("context_modulation", "Context\nmodulation", True),
        ("concision_effect", "Concision\neffect", True),
    ]
    s = SVG(980, 395)
    left, top, cw, rh = 235, 92, 116, 42
    for j, (_, label, _) in enumerate(endpoints):
        s.multiline(left + j * cw + cw / 2, 43, label, 10.5, leading=12, weight="bold")
    for i, slug in enumerate(MODEL_ORDER):
        y = top + i * rh
        s.text(left - 16, y + 26, MODEL_LABELS[slug], 11.5, anchor="end")
        for j, (endpoint, _, signed) in enumerate(endpoints):
            value = 100 * float(cards[slug][endpoint])
            fill = diverging_color(value, 10 if endpoint != "concision_effect" else 30) if signed else C["pale"]
            s.rect(left + j * cw + 2, y + 2, cw - 4, rh - 4, fill, C["white"], 1)
            text_color = C["white"] if signed and abs(value) > (5 if endpoint != "concision_effect" else 15) else C["ink"]
            s.text(left + j * cw + cw / 2, y + 27, f"{value:+.1f}" if signed else f"{value:.1f}", 11.5, text_color, "bold", "middle")
    s.text(left + 2.95 * cw, 365, "All entries in percentage points; neutral accuracy is a percentage.", 10.5, C["muted"], anchor="middle")
    # Compact color key.
    for index, value in enumerate([-10, -5, 0, 5, 10]):
        x = 785 + index * 31
        s.rect(x, 338, 31, 12, diverging_color(value, 10))
    s.text(780, 348, "−", 11, C["blue"], anchor="end")
    s.text(947, 348, "+", 11, C["red"])
    write_and_convert("inclusive_scorecard_heatmap", s)


def family_heatmap() -> None:
    rows = read_csv(ANALYSIS / "family_effects_by_model.csv")
    lookup = {(row["model_slug"], row["family"]): 100 * float(row["cde"]) for row in rows}
    s = SVG(1100, 430)
    left, top, cw, rh = 224, 105, 103, 42
    for j, family in enumerate(FAMILY_ORDER):
        s.multiline(left + j * cw + cw / 2, 48, FAMILY_SHORT[family], 9.5, leading=11, weight="bold")
    for i, slug in enumerate(MODEL_ORDER):
        y = top + i * rh
        s.text(left - 16, y + 26, MODEL_LABELS[slug], 11.5, anchor="end")
        for j, family in enumerate(FAMILY_ORDER):
            value = lookup[(slug, family)]
            fill = diverging_color(value, 9)
            s.rect(left + j * cw + 2, y + 2, cw - 4, rh - 4, fill, C["white"])
            text_color = C["white"] if abs(value) > 4.5 else C["ink"]
            s.text(left + j * cw + cw / 2, y + 27, f"{value:+.1f}", 10.5, text_color, "bold", "middle")
    s.text(left, 392, "Family-level CDE (percentage points), averaged across four task seeds and both contexts", 10.5, C["muted"])
    write_and_convert("family_cde_heatmap", s)


def surface_robustness() -> None:
    rows = read_csv(ANALYSIS / "surface_effects.csv")
    lookup = {(row["model_slug"], row["task_template"], row["surface_form"]): 100 * float(row["cde"]) for row in rows}
    s = SVG(980, 430)
    panel_specs = [
        ("minimal", "Minimal task request", 150, 470),
        ("reasoning_requested", "Reasoning already requested", 575, 935),
    ]
    forms = [("canonical", "Canonical", C["ink"]), ("structured", "Structured", C["orange"]), ("scenario", "Scenario", C["teal"])]
    lo, hi = -7.5, 8.0
    for template, title, left, right in panel_specs:
        s.text((left + right) / 2, 32, title, 12.5, weight="bold", anchor="middle")
        for tick in [-6, -3, 0, 3, 6]:
            x = xmap(tick, lo, hi, left, right)
            s.line(x, 65, x, 350, C["ink"] if tick == 0 else C["grid"], 1.2 if tick == 0 else 1)
            s.text(x, 375, f"{tick:+d}" if tick else "0", 10, C["muted"], anchor="middle")
        for i, slug in enumerate(MODEL_ORDER):
            y = 90 + i * 42
            if left == 150:
                s.text(left - 13, y + 4, MODEL_LABELS[slug], 10.5, anchor="end")
            xs = [xmap(lookup[(slug, template, form)], lo, hi, left, right) for form, _, _ in forms]
            s.line(min(xs), y, max(xs), y, C["grid"], 2)
            for x, (_, _, color) in zip(xs, forms):
                s.circle(x, y, 4.2, color, C["white"], 0.8)
    for x, (_, label, color) in zip([360, 465, 565], forms):
        s.circle(x, 406, 4.2, color)
        s.text(x + 9, 410, label, 10.5)
    write_and_convert("surface_cde_robustness", s)


def concision_tradeoff() -> None:
    rows = read_csv(ANALYSIS / "condition_accuracy_by_model.csv")
    lookup = {(row["model_slug"], row["task_template"], row["condition"]): row for row in rows}
    s = SVG(760, 470)
    left, right, top, bottom = 105, 720, 45, 390
    xlo, xhi, ylo, yhi = -180, 5, -45, 8
    for tick in [-150, -100, -50, 0]:
        x = xmap(tick, xlo, xhi, left, right)
        s.line(x, top, x, bottom, C["ink"] if tick == 0 else C["grid"], 1)
        s.text(x, 416, tick, 10, C["muted"], anchor="middle")
    for tick in [-40, -30, -20, -10, 0]:
        y = bottom - (tick - ylo) / (yhi - ylo) * (bottom - top)
        s.line(left, y, right, y, C["ink"] if tick == 0 else C["grid"], 1)
        s.text(left - 12, y + 4, tick, 10, C["muted"], anchor="end")
    colors = {"minimal": C["orange"], "reasoning_requested": C["teal"]}
    for slug in MODEL_ORDER:
        for template in ["minimal", "reasoning_requested"]:
            check = lookup[(slug, template, "common_check")]
            concise = lookup[(slug, template, "common_check_concise")]
            dx = float(concise["mean_generated_tokens"]) - float(check["mean_generated_tokens"])
            dy = 100 * (float(concise["accuracy_macro"]) - float(check["accuracy_macro"]))
            x = xmap(dx, xlo, xhi, left, right)
            y = bottom - (dy - ylo) / (yhi - ylo) * (bottom - top)
            s.circle(x, y, 5, colors[template], C["white"], 0.8)
            if slug in {"qwen2.5-7b", "tulu3-sft-8b"} and template == "minimal":
                s.text(x + 7, y - 6, MODEL_LABELS[slug], 9.5, C["muted"])
    s.text((left + right) / 2, 453, "Change in generated tokens: check + concise minus check", 11, anchor="middle")
    s.text(18, (top + bottom) / 2, "Accuracy effect (pp)", 11, anchor="middle")
    for x, template, label in [(430, "minimal", "Minimal"), (530, "reasoning_requested", "Reasoning requested")]:
        s.circle(x, 22, 4.5, colors[template])
        s.text(x + 9, 26, label, 10.5)
    write_and_convert("concision_accuracy_token_tradeoff", s)


if __name__ == "__main__":
    required = [
        ANALYSIS / "scorecard_by_model.csv",
        ANALYSIS / "scorecard_by_model_seed.csv",
        ANALYSIS / "family_effects_by_model.csv",
        ANALYSIS / "surface_effects.csv",
        ANALYSIS / "condition_accuracy_by_model.csv",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    cde_context_forest()
    scorecard_heatmap()
    family_heatmap()
    surface_robustness()
    concision_tradeoff()
    print(f"Wrote five result figures (SVG/PDF/PNG) to {FIG}")
