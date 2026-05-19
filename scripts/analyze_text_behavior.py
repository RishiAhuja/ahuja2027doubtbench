#!/usr/bin/env python3
"""Analyze output text behavior for EXP-02/EXP-02B runs.

This complements accuracy metrics with simple lexical/style measures:
hedging, self-doubt language, refusal language, affect leakage, output length,
reasoning-before-final-answer length, and format compliance.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


WORD_RE = re.compile(r"[A-Za-z0-9_']+")
FINAL_ANSWER_RE = re.compile(r"final\s+answer\s*:", re.IGNORECASE)

HEDGE_PATTERNS = [
    r"\bi think\b",
    r"\bi believe\b",
    r"\bi guess\b",
    r"\bmaybe\b",
    r"\bperhaps\b",
    r"\bpossibly\b",
    r"\bprobably\b",
    r"\blikely\b",
    r"\bseems?\b",
    r"\bmight\b",
    r"\bcould\b",
    r"\bnot sure\b",
    r"\buncertain\b",
]
SELF_DOUBT_PATTERNS = [
    r"\bi may be wrong\b",
    r"\bi might be wrong\b",
    r"\bi could be wrong\b",
    r"\bi'?m not confident\b",
    r"\bnot confident\b",
    r"\bsecond-guess\b",
    r"\bdouble-check\b",
    r"\bcheck my work\b",
    r"\bquestion my\b",
    r"\buncertain about\b",
]
REFUSAL_PATTERNS = [
    r"\bi can'?t\b",
    r"\bi cannot\b",
    r"\bi'?m unable\b",
    r"\bi am unable\b",
    r"\bnot able to\b",
    r"\bas an ai\b",
    r"\bnot appropriate\b",
    r"\bcan'?t help\b",
    r"\bcannot help\b",
]
AFFECT_LEAK_PATTERNS = [
    r"\bsad\b",
    r"\bsadness\b",
    r"\bsorrow\b",
    r"\bmelanchol",
    r"\bworthless\b",
    r"\bincapable\b",
    r"\bunreliable\b",
    r"\bwrong\b",
    r"\bincorrect\b",
    r"\bdoubt\b",
]


def compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


HEDGES = compile_patterns(HEDGE_PATTERNS)
SELF_DOUBT = compile_patterns(SELF_DOUBT_PATTERNS)
REFUSALS = compile_patterns(REFUSAL_PATTERNS)
AFFECT_LEAKS = compile_patterns(AFFECT_LEAK_PATTERNS)


def count_patterns(text: str, patterns: list[re.Pattern[str]]) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def reasoning_prefix(text: str) -> str:
    matches = list(FINAL_ANSWER_RE.finditer(text))
    if not matches:
        return text
    return text[: matches[-1].start()].strip()


def iter_jsonl_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_file():
            paths.append(path)
            continue
        if not path.is_dir():
            raise SystemExit(f"Input does not exist: {path}")
        parsed = sorted(path.glob("**/parsed_outputs.jsonl"))
        if parsed:
            paths.extend(parsed)
        else:
            paths.extend(sorted(path.glob("**/raw_outputs.jsonl")))
    return sorted(dict.fromkeys(paths))


def read_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
                row["_source_path"] = str(path)
                rows.append(row)
    return rows


def infer_source_run(path_text: str) -> str:
    path = Path(path_text)
    parts = path.parts
    if "outputs" not in parts:
        return str(path.parent)
    idx = parts.index("outputs")
    if len(parts) <= idx + 2:
        return str(path.parent)
    exp = parts[idx + 1]
    run = parts[idx + 2]
    label_parts = [parts[idx], exp, run]
    if run.startswith("api_parallel") and len(parts) > idx + 4:
        label_parts.append(parts[idx + 3])
        if len(parts) > idx + 5 and parts[idx + 4] == "merged":
            label_parts.append("merged")
    return "/".join(label_parts)


def enrich(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("raw_output") or "")
    prefix = reasoning_prefix(text)
    score = row.get("score")
    words = word_count(text)
    hedges = count_patterns(text, HEDGES)
    self_doubt = count_patterns(text, SELF_DOUBT)
    refusals = count_patterns(text, REFUSALS)
    affect_leaks = count_patterns(text, AFFECT_LEAKS)
    return {
        **row,
        "_output_words": words,
        "_reasoning_words": word_count(prefix),
        "_has_final_answer": bool(FINAL_ANSWER_RE.search(text)),
        "_hedge_count": hedges,
        "_self_doubt_count": self_doubt,
        "_refusal_count": refusals,
        "_affect_leak_count": affect_leaks,
        "_has_hedge": hedges > 0,
        "_has_self_doubt": self_doubt > 0,
        "_has_refusal": refusals > 0,
        "_has_affect_leak": affect_leaks > 0,
        "_is_correct": score is True,
        "_is_wrong": score is False,
        "_is_scored": isinstance(score, bool),
        "_source_run": infer_source_run(str(row.get("_source_path") or "")),
    }


def avg(values: list[float]) -> float:
    return mean(values) if values else 0.0


def proportion(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0


def group_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("_source_run") or ""),
        str(row.get("model") or ""),
        str(row.get("dataset") or ""),
        str(row.get("condition") or ""),
        str(row.get("params", {}).get("prompt_placement") or "system"),
    )


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)

    summaries: list[dict[str, Any]] = []
    for (source_run, model, dataset, condition, placement), group in sorted(grouped.items()):
        scored = [row for row in group if row["_is_scored"]]
        total_words = sum(row["_output_words"] for row in group)
        total_words = max(total_words, 1)
        summaries.append(
            {
                "model": model,
                "source_run": source_run,
                "dataset": dataset,
                "condition": condition,
                "prompt_placement": placement,
                "n": len(group),
                "accuracy": proportion([row["_is_correct"] for row in scored]) if scored else "",
                "wrong_rate": proportion([row["_is_wrong"] for row in scored]) if scored else "",
                "error_rate": proportion([bool(row.get("error")) for row in group]),
                "final_answer_rate": proportion([row["_has_final_answer"] for row in group]),
                "avg_output_words": avg([row["_output_words"] for row in group]),
                "avg_reasoning_words": avg([row["_reasoning_words"] for row in group]),
                "hedge_rate": proportion([row["_has_hedge"] for row in group]),
                "self_doubt_rate": proportion([row["_has_self_doubt"] for row in group]),
                "refusal_rate": proportion([row["_has_refusal"] for row in group]),
                "affect_leak_rate": proportion([row["_has_affect_leak"] for row in group]),
                "hedges_per_100_words": 100 * sum(row["_hedge_count"] for row in group) / total_words,
                "self_doubt_per_100_words": 100 * sum(row["_self_doubt_count"] for row in group) / total_words,
                "refusals_per_100_words": 100 * sum(row["_refusal_count"] for row in group) / total_words,
                "affect_leaks_per_100_words": 100 * sum(row["_affect_leak_count"] for row in group) / total_words,
            }
        )
    return summaries


def deltas_vs_baseline(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {
        (row["source_run"], row["model"], row["dataset"], row["prompt_placement"], row["condition"]): row
        for row in summaries
    }
    metric_names = [
        "accuracy",
        "wrong_rate",
        "final_answer_rate",
        "avg_output_words",
        "avg_reasoning_words",
        "hedge_rate",
        "self_doubt_rate",
        "refusal_rate",
        "affect_leak_rate",
        "hedges_per_100_words",
        "self_doubt_per_100_words",
    ]
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        condition = summary["condition"]
        if condition == "baseline":
            continue
        baseline = by_key.get(
            (
                summary["source_run"],
                summary["model"],
                summary["dataset"],
                summary["prompt_placement"],
                "baseline",
            )
        )
        if not baseline:
            continue
        delta = {
            "model": summary["model"],
            "source_run": summary["source_run"],
            "dataset": summary["dataset"],
            "condition": condition,
            "prompt_placement": summary["prompt_placement"],
            "n": summary["n"],
        }
        for metric in metric_names:
            value = summary.get(metric)
            base = baseline.get(metric)
            if value == "" or base == "":
                delta[f"delta_{metric}"] = ""
            else:
                delta[f"delta_{metric}"] = float(value) - float(base)
        rows.append(delta)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_examples(path: Path, rows: list[dict[str, Any]], limit_per_group: int) -> None:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)
    with path.open("w", encoding="utf-8") as handle:
        for key, group in sorted(grouped.items()):
            ranked = sorted(
                group,
                key=lambda row: (
                    row["_hedge_count"] + row["_self_doubt_count"] + row["_refusal_count"],
                    row["_output_words"],
                ),
                reverse=True,
            )
            for row in ranked[:limit_per_group]:
                snippet = str(row.get("raw_output") or "").replace("\n", " ")[:800]
                handle.write(
                    json.dumps(
                        {
                            "source_run": key[0],
                            "model": key[1],
                            "dataset": key[2],
                            "condition": key[3],
                            "prompt_placement": key[4],
                            "sample_id": row.get("sample_id"),
                            "score": row.get("score"),
                            "output_words": row["_output_words"],
                            "hedge_count": row["_hedge_count"],
                            "self_doubt_count": row["_self_doubt_count"],
                            "refusal_count": row["_refusal_count"],
                            "snippet": snippet,
                            "source_path": row.get("_source_path"),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="Run directories or JSONL output files.")
    parser.add_argument("--out", default=None)
    parser.add_argument("--examples-per-group", type=int, default=3)
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"outputs/analysis/text_behavior_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = iter_jsonl_paths(args.inputs)
    rows = [enrich(row) for row in read_rows(paths)]
    summaries = summarize(rows)
    deltas = deltas_vs_baseline(summaries)

    write_csv(out_dir / "summary_by_condition.csv", summaries)
    write_csv(out_dir / "deltas_vs_baseline.csv", deltas)
    write_examples(out_dir / "examples_high_behavior_counts.jsonl", rows, args.examples_per_group)
    (out_dir / "sources.txt").write_text("\n".join(str(path) for path in paths) + "\n", encoding="utf-8")

    print(f"Analyzed {len(rows)} rows from {len(paths)} file(s)")
    print(f"Wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
