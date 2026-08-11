"""Benchmark loaders and parsers for EXP-02 (GSM8K, MMLU, MATH, TriviaQA, BIG-Bench, creative)."""

from __future__ import annotations

import csv
import io
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "experiments" / "data"

GSM8K_TEST_URL = (
    "https://raw.githubusercontent.com/openai/grade-school-math/master/"
    "grade_school_math/data/test.jsonl"
)
MMLU_SIMPLE_EVALS_URL = "https://openaipublic.blob.core.windows.net/simple-evals/mmlu.csv"
MATH_SUBSET_PATH = DATA_DIR / "math_level3_subset.jsonl"
MATH_HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=EleutherAI%2Fhendrycks_math&config={config}&split=test"
    "&offset={offset}&length={length}"
)
MATH_HF_CONFIGS = (
    "algebra",
    "counting_and_probability",
    "geometry",
    "intermediate_algebra",
    "number_theory",
    "prealgebra",
    "precalculus",
)
BIGBENCH_SUBSET_PATH = DATA_DIR / "bigbench_subset.jsonl"
BBH_DATASET = "lukaemon%2Fbbh"
BBH_CONFIGS = (
    "date_understanding",
    "disambiguation_qa",
    "geometric_shapes",
    "hyperbaton",
    "logical_deduction_three_objects",
    "logical_deduction_five_objects",
    "logical_deduction_seven_objects",
    "movie_recommendation",
    "penguins_in_a_table",
    "reasoning_about_colored_objects",
    "ruin_names",
    "salient_translation_error_detection",
    "snarks",
    "temporal_sequences",
    "tracking_shuffled_objects_three_objects",
    "tracking_shuffled_objects_five_objects",
    "tracking_shuffled_objects_seven_objects",
)
BBH_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    f"?dataset={BBH_DATASET}&config={{config}}&split=test"
    "&offset={{offset}}&length={{length}}"
)
TRIVIAQA_SUBSET_PATH = DATA_DIR / "triviaqa_subset.jsonl"
CREATIVE_PROMPTS_PATH = DATA_DIR / "creative_prompts.json"


@dataclass(frozen=True)
class BenchmarkSample:
    dataset: str
    sample_id: str
    question: str
    gold: str
    choices: dict[str, str] | None = None
    subject: str | None = None
    metadata: dict[str, Any] | None = None


def _fetch_text(url: str, timeout: int = 120) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _fetch_json(url: str, timeout: int = 120) -> Any:
    return json.loads(_fetch_text(url, timeout=timeout))


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
    text = _fetch_text(MMLU_SIMPLE_EVALS_URL, timeout=60)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[BenchmarkSample] = []
    for row_index, row in enumerate(reader):
        if row_index < offset:
            continue
        if len(rows) >= limit:
            break
        rows.append(_mmlu_row_to_sample(row, row_index))
    return rows


def _mmlu_row_to_sample(row: dict[str, str], row_index: int) -> BenchmarkSample:
    return BenchmarkSample(
        dataset="mmlu",
        sample_id=f"mmlu_{row_index:05d}",
        question=row["Question"],
        choices={label: row[label] for label in ["A", "B", "C", "D"]},
        gold=row["Answer"].strip().upper(),
        subject=row.get("Subject"),
    )


def load_mmlu_stratified(limit: int, seed: int = 42) -> list[BenchmarkSample]:
    text = _fetch_text(MMLU_SIMPLE_EVALS_URL, timeout=60)
    reader = csv.DictReader(io.StringIO(text))
    by_subject: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for row_index, row in enumerate(reader):
        subject = row.get("Subject") or "unknown"
        by_subject[subject].append((row_index, row))

    rng = random.Random(seed)
    subjects = sorted(by_subject)
    if not subjects:
        return []

    per_subject = max(1, limit // len(subjects))
    selected: list[tuple[int, dict[str, str]]] = []
    selected_ids: set[int] = set()
    for subject in subjects:
        pool = by_subject[subject][:]
        rng.shuffle(pool)
        for item in pool[:per_subject]:
            selected.append(item)
            selected_ids.add(item[0])

    if len(selected) < limit:
        remainder = [item for subject in subjects for item in by_subject[subject] if item[0] not in selected_ids]
        rng.shuffle(remainder)
        selected.extend(remainder[: limit - len(selected)])

    rng.shuffle(selected)
    selected = selected[:limit]
    return [_mmlu_row_to_sample(row, idx) for idx, row in selected]


def load_math_level3(limit: int) -> list[BenchmarkSample]:
    if MATH_SUBSET_PATH.exists():
        return _load_math_from_jsonl(MATH_SUBSET_PATH, limit)
    rows = _fetch_math_level3_hf(limit)
    if rows:
        return rows
    raise FileNotFoundError(
        f"MATH Level-3 subset missing at {MATH_SUBSET_PATH}. "
        "Run: python scripts/download_benchmark_data.py"
    )


def _load_math_from_jsonl(path: Path, limit: int) -> list[BenchmarkSample]:
    rows: list[BenchmarkSample] = []
    with path.open(encoding="utf-8") as handle:
        for line_index, line in enumerate(handle):
            if len(rows) >= limit:
                break
            payload = json.loads(line)
            rows.append(
                BenchmarkSample(
                    dataset="math",
                    sample_id=payload.get("id", f"math_{line_index:05d}"),
                    question=payload["problem"],
                    gold=payload["gold"],
                    subject=payload.get("subject"),
                    metadata=payload.get("metadata"),
                )
            )
    return rows


def _fetch_math_level3_hf(limit: int) -> list[BenchmarkSample]:
    rows: list[BenchmarkSample] = []
    page_size = min(100, max(limit, 1))
    for config in MATH_HF_CONFIGS:
        if len(rows) >= limit:
            break
        offset = 0
        while len(rows) < limit:
            url = MATH_HF_ROWS_URL.format(config=config, offset=offset, length=page_size)
            payload = _fetch_json(url)
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
                rows.append(
                    BenchmarkSample(
                        dataset="math",
                        sample_id=f"math_{config}_{len(rows):04d}",
                        question=row["problem"],
                        gold=gold,
                        subject=config,
                        metadata={"level": row.get("level"), "type": row.get("type")},
                    )
                )
                if len(rows) >= limit:
                    break
            offset += len(batch)
            if len(batch) < page_size:
                break
    return rows[:limit]


def extract_math_gold(solution: str) -> str:
    boxed = re.findall(r"\\boxed\{([^}]+)\}", solution)
    if boxed:
        inner = boxed[-1].strip()
        if re.fullmatch(r"[A-D]", inner, flags=re.IGNORECASE):
            return inner.upper()
        return normalize_number(inner) or inner
    return ""


def load_bigbench(limit: int) -> list[BenchmarkSample]:
    if BIGBENCH_SUBSET_PATH.exists():
        return _load_bigbench_from_jsonl(BIGBENCH_SUBSET_PATH, limit)
    rows = _fetch_bigbench_bbh(limit)
    if rows:
        return rows
    raise FileNotFoundError(
        f"BIG-Bench subset missing at {BIGBENCH_SUBSET_PATH}. "
        "Run: python scripts/download_benchmark_data.py"
    )


def _load_bigbench_from_jsonl(path: Path, limit: int) -> list[BenchmarkSample]:
    rows: list[BenchmarkSample] = []
    with path.open(encoding="utf-8") as handle:
        for line_index, line in enumerate(handle):
            if len(rows) >= limit:
                break
            payload = json.loads(line)
            rows.append(
                BenchmarkSample(
                    dataset="bigbench",
                    sample_id=payload.get("id", f"bigbench_{line_index:05d}"),
                    question=payload["question"],
                    choices=payload.get("choices"),
                    gold=payload["gold"],
                    subject=payload.get("subject"),
                )
            )
    return rows


def _bbh_row_to_sample(config: str, example_index: int, row: dict[str, Any]) -> BenchmarkSample | None:
    question = row.get("input", "").strip()
    target = row.get("target", "").strip()
    if not question or not target:
        return None
    gold = re.sub(r"[()\\s]", "", target).upper()
    choices = {match.group(1): match.group(2).strip() for match in re.finditer(r"\(([A-Z])\)\s*([^\n]+)", question)}
    if not re.fullmatch(r"[A-Z]", gold) or gold not in choices:
        return None
    return BenchmarkSample(
        dataset="bigbench",
        sample_id=f"bigbench_{config}_{example_index:04d}",
        question=question,
        choices=choices or None,
        gold=gold,
        subject=config,
    )


def _fetch_bigbench_bbh(limit: int) -> list[BenchmarkSample]:
    rows: list[BenchmarkSample] = []
    for config in BBH_CONFIGS:
        if len(rows) >= limit:
            break
        offset = 0
        while len(rows) < limit:
            url = BBH_ROWS_URL.format(config=config, offset=offset, length=50)
            payload = _fetch_json(url)
            batch = payload.get("rows") or []
            if not batch:
                break
            for batch_index, item in enumerate(batch):
                sample = _bbh_row_to_sample(config, offset + batch_index, item.get("row") or item)
                if sample is None:
                    continue
                rows.append(sample)
                if len(rows) >= limit:
                    break
            offset += len(batch)
            if len(batch) < 50:
                break
    return rows[:limit]


def load_triviaqa(limit: int) -> list[BenchmarkSample]:
    if not TRIVIAQA_SUBSET_PATH.exists():
        raise FileNotFoundError(
            f"TriviaQA subset missing at {TRIVIAQA_SUBSET_PATH}. "
            "Run: python scripts/download_benchmark_data.py"
        )
    rows: list[BenchmarkSample] = []
    with TRIVIAQA_SUBSET_PATH.open(encoding="utf-8") as handle:
        for line_index, line in enumerate(handle):
            if len(rows) >= limit:
                break
            payload = json.loads(line)
            rows.append(
                BenchmarkSample(
                    dataset="triviaqa",
                    sample_id=payload.get("id", f"triviaqa_{line_index:05d}"),
                    question=payload["question"],
                    gold=normalize_text(payload["answer"]),
                )
            )
    return rows


def load_creative(limit: int) -> list[BenchmarkSample]:
    if not CREATIVE_PROMPTS_PATH.exists():
        raise FileNotFoundError(f"Creative prompts missing: {CREATIVE_PROMPTS_PATH}")
    items = json.loads(CREATIVE_PROMPTS_PATH.read_text(encoding="utf-8"))
    rows: list[BenchmarkSample] = []
    for item in items[:limit]:
        rows.append(
            BenchmarkSample(
                dataset="creative",
                sample_id=item["id"],
                question=item["prompt"],
                gold="",
                metadata={"scored": False},
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


def math_user_prompt(sample: BenchmarkSample) -> str:
    return (
        "Solve the following competition math problem. Show concise reasoning, then end with "
        "either `Final answer: <number>` or `Final answer: <A/B/C/D>` if multiple choice.\n\n"
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


def bigbench_user_prompt(sample: BenchmarkSample) -> str:
    if not sample.choices:
        raise ValueError("BIG-Bench sample missing choices")
    labels = "/".join(sample.choices.keys())
    choices = "\n".join(f"{label}. {text}" for label, text in sample.choices.items())
    return (
        "Answer the following multiple-choice question. End with a line exactly in the form "
        f"`Final answer: <{labels}>`.\n\n"
        f"Question:\n{sample.question}\n\n"
        f"Choices:\n{choices}"
    )


def triviaqa_user_prompt(sample: BenchmarkSample) -> str:
    return (
        "Answer the following trivia question as briefly as possible. "
        "End with a line exactly in the form `Final answer: <short answer>`.\n\n"
        f"Question:\n{sample.question}"
    )


def creative_user_prompt(sample: BenchmarkSample) -> str:
    return sample.question


def build_user_prompt(sample: BenchmarkSample) -> str:
    builders = {
        "gsm8k": gsm8k_user_prompt,
        "mmlu": mmlu_user_prompt,
        "math": math_user_prompt,
        "triviaqa": triviaqa_user_prompt,
        "bigbench": bigbench_user_prompt,
        "creative": creative_user_prompt,
    }
    builder = builders.get(sample.dataset)
    if builder is None:
        raise ValueError(f"Unsupported dataset: {sample.dataset}")
    return builder(sample)


def parse_answer(dataset: str, output: str) -> str:
    if dataset in {"gsm8k", "math"}:
        return parse_gsm8k_answer(output)
    if dataset == "mmlu":
        return parse_mmlu_answer(output)
    if dataset == "bigbench":
        return parse_bigbench_answer(output)
    if dataset == "triviaqa":
        return parse_triviaqa_answer(output)
    if dataset == "creative":
        return ""
    raise ValueError(f"Unsupported dataset: {dataset}")


def parse_gsm8k_answer(output: str) -> str:
    boxed = re.findall(r"\\boxed\{([^}]+)\}", output)
    if boxed:
        inner = boxed[-1].strip()
        if re.fullmatch(r"[A-D]", inner, flags=re.IGNORECASE):
            return inner.upper()
        parsed = normalize_number(inner)
        if parsed:
            return parsed
    final = re.findall(r"final answer\s*:\s*([^\n]+)", output, flags=re.IGNORECASE)
    if final:
        token = final[-1].strip()
        if re.fullmatch(r"[A-D]", token, flags=re.IGNORECASE):
            return token.upper()
        parsed = normalize_number(token)
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


def parse_bigbench_answer(output: str) -> str:
    final = re.findall(r"final answer\s*:\s*\(?([A-Z])\)?\b", output, flags=re.IGNORECASE)
    if final:
        return final[-1].upper()
    standalone = re.findall(r"\b([A-Z])\b", output)
    return standalone[-1].upper() if standalone else ""


def parse_triviaqa_answer(output: str) -> str:
    final = re.findall(r"final answer\s*:\s*([^\n]+)", output, flags=re.IGNORECASE)
    if final:
        return normalize_text(final[-1])
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    return normalize_text(lines[-1]) if lines else ""


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s]", "", value)
    value = re.sub(r"\b(a|an|the)\b", " ", value)
    return " ".join(value.split())


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


def score_prediction(dataset: str, parsed: str, gold: str) -> bool | None:
    if dataset == "creative":
        return None
    if dataset == "gsm8k":
        return normalize_number(parsed) == normalize_number(gold)
    if dataset == "math":
        if re.fullmatch(r"[A-D]", gold, flags=re.IGNORECASE):
            return parsed.strip().upper() == gold.strip().upper()
        return normalize_number(parsed) == normalize_number(gold)
    if dataset in {"mmlu", "bigbench"}:
        return parsed.strip().upper() == gold.strip().upper()
    if dataset == "triviaqa":
        return normalize_text(parsed) == normalize_text(gold) or normalize_text(gold) in normalize_text(
            parsed
        )
    raise ValueError(f"Unsupported dataset: {dataset}")


def sample_to_dict(sample: BenchmarkSample) -> dict[str, Any]:
    return {
        "dataset": sample.dataset,
        "sample_id": sample.sample_id,
        "question": sample.question,
        "choices": sample.choices,
        "gold": sample.gold,
        "subject": sample.subject,
        "metadata": sample.metadata,
    }
