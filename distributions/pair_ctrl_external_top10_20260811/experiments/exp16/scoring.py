"""Scoring helpers for EXP-16 cognitive battery tasks."""

from __future__ import annotations

import json
import re
from typing import Any


FINAL_RE = re.compile(r"final answer\s*:\s*(.+)", flags=re.IGNORECASE)


def extract_final_answer(output: str) -> str:
    matches = FINAL_RE.findall(output or "")
    if matches:
        return matches[-1].strip()
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def normalize_integer(value: str) -> str:
    match = re.search(r"[-+]?\d[\d,]*", value)
    if not match:
        return ""
    return str(int(match.group(0).replace(",", "")))


def normalize_string(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^final answer\s*:\s*", "", value, flags=re.IGNORECASE)
    value = value.strip().strip("`'\"")
    value = re.sub(r"\s+", " ", value)
    return value.lower()


def normalize_list(value: str) -> str:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    parts = [normalize_string(part) for part in value.split(",")]
    parts = [part for part in parts if part]
    return json.dumps(parts, separators=(",", ":"))


def normalize_assignment_list(value: str) -> str:
    parts = []
    for raw_part in value.split(","):
        if "=" not in raw_part:
            continue
        key, val = raw_part.split("=", 1)
        parts.append((normalize_string(key).upper(), normalize_string(val)))
    return json.dumps(sorted(parts), separators=(",", ":"))


def normalize_answer(value: str, answer_type: str) -> str:
    if answer_type == "integer":
        return normalize_integer(value)
    if answer_type in {"list", "comma_list"}:
        return normalize_list(value)
    if answer_type == "assignment_list":
        return normalize_assignment_list(value)
    if answer_type == "string":
        return normalize_string(value)
    raise ValueError(f"Unsupported EXP-16 answer_type: {answer_type}")


def score_output(output: str, gold: str, answer_type: str) -> bool:
    parsed = extract_final_answer(output)
    return normalize_answer(parsed, answer_type) == normalize_answer(gold, answer_type)


def score_task_row_output(row: dict[str, Any], output: str) -> bool:
    return score_output(output, str(row["gold"]), str(row["answer_type"]))
