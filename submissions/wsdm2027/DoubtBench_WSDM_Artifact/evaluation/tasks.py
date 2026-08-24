"""Load DoubtBench JSONL tasks and score generated answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doubtbench.scoring import extract_final_answer, score_task_row_output


def load_tasks(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"No DoubtBench tasks found in {path}")
    return rows


def score_generation(task: dict[str, Any], text: str) -> tuple[str, bool, str | None]:
    try:
        parsed = extract_final_answer(text)
        score = score_task_row_output(task, text)
        return parsed, score, None
    except Exception as exc:  # noqa: BLE001
        return "", False, f"{type(exc).__name__}: {exc}"
