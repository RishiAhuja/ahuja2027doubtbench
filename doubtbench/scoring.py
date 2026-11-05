"""Compare a model response with a DoubtBench gold answer.

The comparison uses the last line of the form "Final answer: ...". When that
label is missing, it uses the last non-empty line. Both sides are normalized
for the answer type and then compared exactly. A missing or malformed
answer does not match.

The answer types are integer, string, list, comma_list, and assignment_list.
list and comma_list share one normalizer.
"""

from __future__ import annotations

import json
import re
from typing import Any


# The last match is the answer. The label match is case-insensitive.
FINAL_RE = re.compile(r"final answer\s*:\s*(.+)", flags=re.IGNORECASE)


def extract_final_answer(output: str) -> str:
    """Text after the last Final answer label, or the last non-empty line when that label is absent."""
    matches = FINAL_RE.findall(output or "")
    if matches:
        return matches[-1].strip()
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def normalize_integer(value: str) -> str:
    """The first integer in the text, or an empty string when there is none.

    A leading sign is accepted, and commas inside the number are removed.
    The result is the plain decimal form, so 007 and 7 match.
    """
    match = re.search(r"[-+]?\d[\d,]*", value)
    if not match:
        return ""
    return str(int(match.group(0).replace(",", "")))


def normalize_string(value: str) -> str:
    """Trim the text, drop a leading Final answer label, strip quotes, collapse whitespace, and lowercase."""
    value = value.strip()
    value = re.sub(r"^final answer\s*:\s*", "", value, flags=re.IGNORECASE)
    value = value.strip().strip("`'\"")
    value = re.sub(r"\s+", " ", value)
    return value.lower()


def normalize_list(value: str) -> str:
    """Ordered comma-separated items as a JSON list of normalized strings.

    Surrounding brackets are optional. Empty pieces are dropped.
    """
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    parts = [normalize_string(part) for part in value.split(",")]
    parts = [part for part in parts if part]
    return json.dumps(parts, separators=(",", ":"))


def normalize_assignment_list(value: str) -> str:
    """key=value pairs as a JSON list sorted by key.

    Keys are uppercased. Values go through the string normalizer, so they are
    lowercased. Pieces without an equals sign are dropped.
    """
    parts = []
    for raw_part in value.split(","):
        if "=" not in raw_part:
            continue
        key, val = raw_part.split("=", 1)
        parts.append((normalize_string(key).upper(), normalize_string(val)))
    return json.dumps(sorted(parts), separators=(",", ":"))


def normalize_answer(value: str, answer_type: str) -> str:
    """Normalize gold text or a parsed response.

    list and comma_list use the same normalizer.
    """
    if answer_type == "integer":
        return normalize_integer(value)
    if answer_type in {"list", "comma_list"}:
        return normalize_list(value)
    if answer_type == "assignment_list":
        return normalize_assignment_list(value)
    if answer_type == "string":
        return normalize_string(value)
    raise ValueError(f"Unsupported DoubtBench answer_type: {answer_type}")


def score_output(output: str, gold: str, answer_type: str) -> bool:
    """True when the parsed response and the gold answer match after normalization."""
    parsed = extract_final_answer(output)
    return normalize_answer(parsed, answer_type) == normalize_answer(gold, answer_type)


def score_task_row_output(row: dict[str, Any], output: str) -> bool:
    """Score a response against the gold and answer_type fields of one task row."""
    return score_output(output, str(row["gold"]), str(row["answer_type"]))
