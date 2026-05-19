#!/usr/bin/env python3
"""Download local benchmark subsets (TriviaQA) for offline/cluster use."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
TRIVIA_OUT = REPO_ROOT / "experiments" / "data" / "triviaqa_subset.jsonl"
MATH_OUT = REPO_ROOT / "experiments" / "data" / "math_level3_subset.jsonl"
BIGBENCH_OUT = REPO_ROOT / "experiments" / "data" / "bigbench_subset.jsonl"
OPENTDB_URL = "https://opentdb.com/api.php?amount={limit}&type=multiple"
MATH_HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=EleutherAI%2Fhendrycks_math&config={config}&split=test"
    "&offset={offset}&length={length}"
)
BBH_CONFIGS = (
    "logical_deduction_three_objects",
    "navigate",
    "date_understanding",
    "disambiguation_qa",
    "snarks",
)
BBH_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=lukaemon%2Fbbh&config={config}&split=test"
    "&offset={offset}&length={length}"
)
MATH_CONFIGS = (
    "algebra",
    "counting_and_probability",
    "geometry",
    "intermediate_algebra",
    "number_theory",
    "prealgebra",
    "precalculus",
)


def normalize_answer(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s]", "", value)
    return " ".join(value.split())


def _decode_html(text: str) -> str:
    import html

    return html.unescape(text)


def download_triviaqa(limit: int = 200) -> int:
    url = OPENTDB_URL.format(limit=min(limit, 50))
    with urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload.get("results", [])

    TRIVIA_OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with TRIVIA_OUT.open("w", encoding="utf-8") as handle:
        for index, item in enumerate(items):
            question = _decode_html(item.get("question") or "")
            answer = _decode_html(item.get("correct_answer") or "")
            if not question or not answer:
                continue
            row = {
                "id": f"triviaqa_{index:05d}",
                "question": question.strip(),
                "answer": normalize_answer(answer),
                "source": "opentdb",
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def extract_math_gold(solution: str) -> str:
    import re

    boxed = re.findall(r"\\boxed\{([^}]+)\}", solution)
    if boxed:
        return boxed[-1].strip()
    return ""


def download_math_level3(limit: int = 200) -> int:
    written = 0
    page_size = 100
    MATH_OUT.parent.mkdir(parents=True, exist_ok=True)
    with MATH_OUT.open("w", encoding="utf-8") as handle:
        for config in MATH_CONFIGS:
            if written >= limit:
                break
            offset = 0
            while written < limit:
                url = MATH_HF_ROWS_URL.format(config=config, offset=offset, length=page_size)
                with urlopen(url, timeout=120) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                batch = payload.get("rows") or []
                if not batch:
                    break
                for item in batch:
                    row = item.get("row") or item
                    if row.get("level") != "Level 3":
                        continue
                    gold = extract_math_gold(row.get("solution", ""))
                    if not gold:
                        continue
                    record = {
                        "id": f"math_{config}_{written:05d}",
                        "problem": row["problem"],
                        "gold": gold,
                        "subject": config,
                        "metadata": {"level": row.get("level"), "type": row.get("type")},
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    if written >= limit:
                        break
                offset += len(batch)
                if len(batch) < page_size:
                    break
    return written


def download_bigbench(limit: int = 200) -> int:
    import re

    written = 0
    per_task = max(1, limit // len(BBH_CONFIGS))
    BIGBENCH_OUT.parent.mkdir(parents=True, exist_ok=True)
    with BIGBENCH_OUT.open("w", encoding="utf-8") as handle:
        for config in BBH_CONFIGS:
            if written >= limit:
                break
            offset = 0
            taken = 0
            while taken < per_task and written < limit:
                url = BBH_ROWS_URL.format(config=config, offset=offset, length=50)
                with urlopen(url, timeout=120) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                batch = payload.get("rows") or []
                if not batch:
                    break
                for item in batch:
                    row = item.get("row") or item
                    question = row.get("input", "").strip()
                    target = row.get("target", "").strip()
                    if not question or not target:
                        continue
                    gold = re.sub(r"[()\\s]", "", target).upper()
                    if not re.fullmatch(r"[A-D]", gold):
                        continue
                    choices = {
                        m.group(1): m.group(2).strip()
                        for m in re.finditer(r"\(([A-D])\)\s*([^\n]+)", question)
                    }
                    record = {
                        "id": f"bigbench_{config}_{written:05d}",
                        "question": question,
                        "choices": choices,
                        "gold": gold,
                        "subject": config,
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    taken += 1
                    if taken >= per_task or written >= limit:
                        break
                offset += len(batch)
                if len(batch) < 50:
                    break
    return written


def main() -> int:
    trivia_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    math_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    bigbench_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    trivia_count = download_triviaqa(limit=trivia_limit)
    math_count = download_math_level3(limit=math_limit)
    bigbench_count = download_bigbench(limit=bigbench_limit)
    print(f"Wrote {trivia_count} rows to {TRIVIA_OUT}")
    print(f"Wrote {math_count} rows to {MATH_OUT}")
    print(f"Wrote {bigbench_count} rows to {BIGBENCH_OUT}")
    return 0 if trivia_count and math_count and bigbench_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
