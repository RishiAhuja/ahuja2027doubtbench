#!/usr/bin/env python3
"""Build dependency-free vector figures from the audited result tables."""

from __future__ import annotations

import csv
import html
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

MECH = ROOT / "outputs/analysis/exp16_final_mechanism_20260529/pooled_mechanism_condition_summary.csv"
QWEN_FIELD = ROOT / "outputs/EXP-02/fieldtest/gsm8k_mech_qwen_20260530_010016/tables/accuracy_by_condition.csv"
LLAMA_FIELD = ROOT / "outputs/EXP-02/fieldtest/gsm8k_mech_llama_20260530_010016/tables/accuracy_by_condition.csv"

C = {
    "blue": "#2D6CDF", "red": "#D94B4B", "green": "#1F9D78",
    "amber": "#D88916", "ink": "#18212B", "muted": "#65717E",
    "grid": "#DCE2E8", "pale_blue": "#EAF1FD", "pale_red": "#FCECEC",
    "pale_green": "#E8F6F1", "pale_gray": "#F3F5F7", "white": "#FFFFFF",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class SVG:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" '
            'orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#65717E"/></marker></defs>',
        ]

    def line(self, x1, y1, x2, y2, stroke=C["grid"], width=1, dash=None, arrow=False):
        attrs = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{width}"{attrs}{marker}/>'
        )

    def rect(self, x, y, w, h, fill, stroke, radius=10, width=1.4):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
        )

    def circle(self, x, y, radius, fill, stroke=None, width=1):
        stroke_attr = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}"{stroke_attr}/>' )

    def square(self, x, y, size, fill):
        self.parts.append(
            f'<rect x="{x-size/2}" y="{y-size/2}" width="{size}" height="{size}" rx="1.5" fill="{fill}"/>'
        )

    def text(self, x, y, value, size=12, fill=C["ink"], weight="normal", anchor="start"):
        value = html.escape(str(value))
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{value}</text>'
        )

    def multiline(self, x, y, lines, size=11, fill=C["ink"], leading=16, weight="normal"):
        safe = [html.escape(str(line)) for line in lines]
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else leading}">{line}</tspan>' for i, line in enumerate(safe)
        )
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}">{spans}</text>'
        )

    def finish(self) -> str:
        return "\n".join(self.parts + ["</svg>"])


def write_and_convert(name: str, svg: SVG) -> None:
    svg_path = FIG / f"{name}.svg"
    svg_path.write_text(svg.finish(), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(FIG / f"{name}.pdf"), str(svg_path)], check=True)
    subprocess.run(
        ["rsvg-convert", "-f", "png", "-w", str(svg.width * 2), "-h", str(svg.height * 2),
         "-o", str(FIG / f"{name}.png"), str(svg_path)], check=True
    )


def box(s: SVG, x, y, w, h, title, lines, face, edge, title_color=None):
    s.rect(x, y, w, h, face, edge)
    s.text(x + 14, y + 25, title, 13, title_color or C["ink"], "bold")
    s.multiline(x + 14, y + 49, lines, 10.5, C["ink"], 15)


def teaser() -> None:
    s = SVG(1000, 350)
    box(s, 15, 55, 225, 235, "Prompt components", [
        "PURE AFFECT", "“You feel melancholic”", "", "SELF-EVALUATION",
        "uncertain + check work", "", "CAPABILITY DENIAL", "“reasoning is unreliable”",
    ], C["pale_gray"], C["muted"])
    box(s, 300, 95, 200, 150, "Policy selection", [
        "Same task, different", "model and instruction", "context can elicit", "different behaviors."
    ], "#FFF7E8", C["amber"])
    box(s, 575, 20, 410, 90, "CHECK  |  Qwen2.5 on under-elicited tasks",
        ["self-evaluation +29.2 pp; direct checking +37.4 pp"], C["pale_green"], C["green"], C["green"])
    box(s, 575, 130, 410, 90, "COLLAPSE  |  base Llama under capability denial",
        ["synthetic −16.6 pp; GSM8K −57.3 pp"], C["pale_red"], C["red"], C["red"])
    box(s, 575, 240, 410, 90, "RESIST / NULL  |  Tulu-DPO and API models",
        ["self-evaluation and pure affect are mostly small"], C["pale_blue"], C["blue"], C["blue"])
    s.line(240, 172, 297, 172, C["muted"], 1.5, arrow=True)
    for y in (65, 175, 285):
        s.line(500, 170, 568, y, C["muted"], 1.35, arrow=True)
    s.text(16, 320, "Boundary condition:", 11.5, C["blue"], "bold")
    s.text(132, 320, "GSM8K already asks for visible reasoning; Qwen's +29 pp gain becomes −0.7 pp.", 11.5)
    write_and_convert("teaser_policy_selection", s)


def xmap(value: float, lo: float, hi: float, left: float, right: float) -> float:
    return left + (value - lo) / (hi - lo) * (right - left)


def mechanism_effects() -> None:
    rows = read_csv(MECH)
    conditions = [
        ("self_doubt_only", "Self-evaluation (+ checking)"),
        ("check_your_work", "Check your work"),
        ("think_step_by_step", "Think step by step"),
        ("capability_denial_only", "Capability denial"),
        ("answer_concisely", "Answer concisely"),
    ]
    models = [
        ("Qwen/Qwen2.5-7B-Instruct", "Qwen2.5", C["green"]),
        ("meta-llama/Llama-3.1-8B-Instruct", "Llama 3.1", C["red"]),
        ("allenai/Llama-3.1-Tulu-3-8B-DPO", "Tulu-DPO", C["blue"]),
    ]
    lookup = {(r["model"], r["condition"]): r for r in rows}
    s = SVG(1000, 365)
    left, right, top, bottom = 255, 975, 68, 310
    lo_x, hi_x = -27, 44
    for tick in range(-20, 41, 10):
        x = xmap(tick, lo_x, hi_x, left, right)
        s.line(x, top, x, bottom, C["grid"], 1)
        s.text(x, 334, tick, 10, C["muted"], anchor="middle")
    s.line(xmap(0, lo_x, hi_x, left, right), top, xmap(0, lo_x, hi_x, left, right), bottom, C["ink"], 1.3)
    offsets = [-10, 0, 10]
    for i, (_, label) in enumerate(conditions):
        y = top + 25 + i * 50
        s.text(left - 15, y + 4, label, 11, anchor="end")
        for (model, _, color), offset in zip(models, offsets):
            row = lookup[(model, conditions[i][0])]
            val = 100 * float(row["delta_vs_baseline"])
            low = 100 * float(row["ci_low"])
            high = 100 * float(row["ci_high"])
            yy = y + offset
            s.line(xmap(low, lo_x, hi_x, left, right), yy, xmap(high, lo_x, hi_x, left, right), yy, color, 2)
            s.line(xmap(low, lo_x, hi_x, left, right), yy - 3, xmap(low, lo_x, hi_x, left, right), yy + 3, color, 1.3)
            s.line(xmap(high, lo_x, hi_x, left, right), yy - 3, xmap(high, lo_x, hi_x, left, right), yy + 3, color, 1.3)
            s.circle(xmap(val, lo_x, hi_x, left, right), yy, 4.3, color)
    for x, (_, label, color) in zip((390, 500, 610), models):
        s.circle(x, 28, 4.5, color)
        s.text(x + 10, 32, label, 11)
    s.text((left + right) / 2, 358, "Accuracy change from each model's baseline (percentage points)", 11, anchor="middle")
    s.text(left, 55, "harm", 10, C["red"])
    s.text(right, 55, "help", 10, C["green"], anchor="end")
    write_and_convert("mechanism_cross_model", s)


def field_boundary() -> None:
    mech_rows = read_csv(MECH)
    conditions = [
        ("self_doubt_only", "Self-evaluation"),
        ("check_your_work", "Check work"),
        ("think_step_by_step", "Step by step"),
        ("capability_denial_only", "Capability denial"),
    ]
    specs = [
        ("Qwen2.5", "Qwen/Qwen2.5-7B-Instruct", QWEN_FIELD, -22, 43),
        ("Llama 3.1", "meta-llama/Llama-3.1-8B-Instruct", LLAMA_FIELD, -61, 6),
    ]
    mech = {(r["model"], r["condition"]): 100 * float(r["delta_vs_baseline"]) for r in mech_rows}
    s = SVG(1000, 365)
    panel_lefts = [220, 620]
    panel_rights = [560, 960]
    top, bottom = 70, 290
    for p, (title, model, path, lo, hi) in enumerate(specs):
        left, right = panel_lefts[p], panel_rights[p]
        field_rows = read_csv(path)
        baseline = next(float(r["accuracy"]) for r in field_rows if r["condition"] == "baseline")
        field = {r["condition"]: 100 * (float(r["accuracy"]) - baseline) for r in field_rows}
        s.text((left + right) / 2, 35, title, 13, weight="bold", anchor="middle")
        step = 10
        first = int(lo / step) * step
        for tick in range(first, int(hi) + 1, step):
            if tick < lo:
                continue
            x = xmap(tick, lo, hi, left, right)
            s.line(x, top, x, bottom, C["grid"], 1)
            s.text(x, 315, tick, 10, C["muted"], anchor="middle")
        zero = xmap(0, lo, hi, left, right)
        s.line(zero, top, zero, bottom, C["ink"], 1.3)
        for i, (cond, label) in enumerate(conditions):
            y = top + 28 + i * 52
            if p == 0:
                s.text(left - 18, y + 4, label, 11, anchor="end")
            syn_x = xmap(mech[(model, cond)], lo, hi, left, right)
            gsm_x = xmap(field[cond], lo, hi, left, right)
            s.line(syn_x, y - 6, gsm_x, y + 6, C["grid"], 2)
            s.square(syn_x, y - 6, 9, C["amber"])
            s.circle(gsm_x, y + 6, 4.8, C["blue"])
        s.text((left + right) / 2, 345, "Accuracy change (pp)", 11, anchor="middle")
    s.square(715, 52, 9, C["amber"])
    s.text(727, 56, "Synthetic", 10.5)
    s.circle(805, 52, 4.8, C["blue"])
    s.text(817, 56, "GSM8K", 10.5)
    write_and_convert("synthetic_to_gsm8k", s)


if __name__ == "__main__":
    for required in (MECH, QWEN_FIELD, LLAMA_FIELD):
        if not required.exists():
            raise FileNotFoundError(required)
    teaser()
    mechanism_effects()
    field_boundary()
    print(f"Wrote SVG, PDF, and PNG figures to {FIG}")
