"""Small benchmark loaders and parsers for EXP-02 smoke tests."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.request import urlopen


GSM8K_TEST_URL = (
    "https://raw.githubusercontent.com/openai/grade-school-math/master/"
    "grade_school_math/data/test.jsonl"
)
MMLU_SIMPLE_EVALS_URL = "https://openaipublic.blob.core.windows.net/simple-evals/mmlu.csv"


@dataclass(frozen=True)
class BenchmarkSample:
    dataset: str
    sample_id: str
    question: str
    gold: str
    choices: dict[str, str] | None = None
    subject: str | None = None


def load_gsm8k(limit: int, offset: int = 0) -> list[BenchmarkSample]:
    rows: list[BenchmarkSample] = []
    with urlopen(GSM8K_TEST_URL, timeout=60) as response:
        for line_index, raw_line in enumerate(response):
            if line_index < offset:
                continue
            if len(rows) >= limit:
                break
            payload = json.loads(raw_line.decode("utf-8"))
            gold = extract_gsm8k_gold(payload["answer"])
            rows.append(
                BenchmarkSample(
                    dataset="gsm8k",
                    sample_id=f"gsm8k_test_{line_index:05d}",
                    question=payload["question"],
                    gold=gold,
                )
            )
    return rows


def load_mmlu(limit: int, offset: int = 0) -> list[BenchmarkSample]:
    with urlopen(MMLU_SIMPLE_EVALS_URL, timeout=60) as response:
        text = response.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[BenchmarkSample] = []
    for row_index, row in enumerate(reader):
        if row_index < offset:
            continue
        if len(rows) >= limit:
            break
        rows.append(
            BenchmarkSample(
                dataset="mmlu",
                sample_id=f"mmlu_{row_index:05d}",
                question=row["Question"],
                choices={label: row[label] for label in ["A", "B", "C", "D"]},
                gold=row["Answer"].strip().upper(),
                subject=row.get("Subject"),
            )
        )
    return rows


def extract_gsm8k_gold(answer: str) -> str:
    if "####" in answer:
        answer = answer.split("####")[-1]
    return normalize_number(answer)


def gsm8k_user_prompt(sample: BenchmarkSample) -> str:
    return (
        "Solve the following grade-school math problem. Show concise reasoning, then end with "
        "a line exactly in the form `Final answer: <number>`.\n\n"
        f"Problem:\n{sample.question}"
    )


def mmlu_user_prompt(sample: BenchmarkSample) -> str:
    if not sample.choices:
        raise ValueError("MMLU sample missing choices")
    choices = "\n".join(f"{label}. {text}" for label, text in sample.choices.items())
    return (
        "Answer the following multiple-choice question. End with a line exactly in the form "
        "`Final answer: <A/B/C/D>`.\n\n"
        f"Question:\n{sample.question}\n\n"
        f"Choices:\n{choices}"
    )


def build_user_prompt(sample: BenchmarkSample) -> str:
    if sample.dataset == "gsm8k":
        return gsm8k_user_prompt(sample)
    if sample.dataset == "mmlu":
        return mmlu_user_prompt(sample)
    raise ValueError(f"Unsupported dataset: {sample.dataset}")


def parse_answer(dataset: str, output: str) -> str:
    if dataset == "gsm8k":
        return parse_gsm8k_answer(output)
    if dataset == "mmlu":
        return parse_mmlu_answer(output)
    raise ValueError(f"Unsupported dataset: {dataset}")


def parse_gsm8k_answer(output: str) -> str:
    boxed = re.findall(r"\\boxed\{([^}]+)\}", output)
    if boxed:
        parsed = normalize_number(boxed[-1])
        if parsed:
            return parsed
    final = re.findall(r"final answer\s*:\s*([^\n]+)", output, flags=re.IGNORECASE)
    if final:
        parsed = normalize_number(final[-1])
        if parsed:
            return parsed
    numbers = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", output)
    return normalize_number(numbers[-1]) if numbers else ""


def parse_mmlu_answer(output: str) -> str:
    final = re.findall(r"final answer\s*:\s*([ABCD])\b", output, flags=re.IGNORECASE)
    if final:
        return final[-1].upper()
    standalone = re.findall(r"\b([ABCD])\b", output, flags=re.IGNORECASE)
    return standalone[-1].upper() if standalone else ""


def normalize_number(value: str) -> str:
    value = value.strip()
    value = value.replace(",", "")
    value = value.replace("$", "")
    if value:
        parts = re.sub(r"[^0-9+\-./]", " ", value).strip().split()
        value = parts[0] if parts else ""
    if not value:
        return ""
    if "/" in value and value.count("/") == 1:
        numerator, denominator = value.split("/")
        try:
            number = Decimal(numerator) / Decimal(denominator)
            return decimal_to_str(number)
        except (InvalidOperation, ZeroDivisionError):
            return value
    try:
        return decimal_to_str(Decimal(value))
    except InvalidOperation:
        return value


def decimal_to_str(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f").rstrip("0").rstrip(".")


def score_prediction(dataset: str, parsed: str, gold: str) -> bool:
    if dataset == "gsm8k":
        return normalize_number(parsed) == normalize_number(gold)
    if dataset == "mmlu":
        return parsed.strip().upper() == gold.strip().upper()
    raise ValueError(f"Unsupported dataset: {dataset}")


def sample_to_dict(sample: BenchmarkSample) -> dict[str, Any]:
    return {
        "dataset": sample.dataset,
        "sample_id": sample.sample_id,
        "question": sample.question,
        "choices": sample.choices,
        "gold": sample.gold,
        "subject": sample.subject,
    }
