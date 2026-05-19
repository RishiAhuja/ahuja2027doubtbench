"""Shared EXP-02 helpers for API and HF runners."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.benchmarks import build_user_prompt, parse_answer, sample_to_dict, score_prediction
from core.llm_client import ProviderError, call_model
from core.metrics import exp02_metrics
from core.models import parse_model_ref
from core.prompts import PROMPT_BY_CONDITION


DEFAULT_CONDITIONS = ["baseline", "melancholic", "negative_capability"]
PROMPT_PLACEMENTS = {"system", "task_prefix", "task_suffix"}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def validate_conditions(conditions: list[str]) -> None:
    unknown = [condition for condition in conditions if condition not in PROMPT_BY_CONDITION]
    if unknown:
        raise SystemExit(f"Unknown conditions: {', '.join(unknown)}")


def validate_prompt_placement(prompt_placement: str) -> None:
    if prompt_placement not in PROMPT_PLACEMENTS:
        allowed = ", ".join(sorted(PROMPT_PLACEMENTS))
        raise SystemExit(f"Unknown prompt placement {prompt_placement!r}; expected one of: {allowed}")


def build_conditioned_prompts(condition: str, sample, prompt_placement: str = "system") -> tuple[str, str]:
    """Return provider/system and user/task prompts for an EXP-02 condition.

    The primary experiment uses `system`, where the condition is sent through the
    provider/system channel or model-native chat template. The task-level modes
    keep a stable baseline system prompt and place the condition text in the user
    prompt for direct comparison with task-level emotional prompting literature.
    """
    validate_prompt_placement(prompt_placement)
    condition_prompt = PROMPT_BY_CONDITION[condition].text
    user_prompt = build_user_prompt(sample)
    if prompt_placement == "system":
        return condition_prompt, user_prompt

    system_prompt = PROMPT_BY_CONDITION["baseline"].text
    if condition == "baseline":
        return system_prompt, user_prompt
    if prompt_placement == "task_prefix":
        return system_prompt, f"{condition_prompt}\n\n{user_prompt}"
    return system_prompt, f"{user_prompt}\n\n{condition_prompt}"


def run_api_one(
    model_ref: str,
    condition: str,
    sample,
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None = None,
    thinking_budget_tokens: int | None = None,
    store_raw_api: bool = False,
    prompt_placement: str = "system",
) -> dict[str, Any]:
    provider, model = parse_model_ref(model_ref)
    system_prompt, user_prompt = build_conditioned_prompts(condition, sample, prompt_placement)
    started = datetime.now(timezone.utc)
    error = None
    raw_output = ""
    response_model = model
    reasoning_chain: list[str] | None = None
    usage: dict[str, int] | None = None
    raw_api = None
    try:
        response = call_model(
            provider=provider,
            model=model,
            system=system_prompt,
            user=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            thinking_budget_tokens=thinking_budget_tokens,
        )
        raw_output = response.text
        response_model = response.model
        reasoning_chain = response.reasoning_chain
        usage = response.usage
        if store_raw_api:
            raw_api = response.raw
    except ProviderError as exc:
        error = str(exc)
    ended = datetime.now(timezone.utc)

    parsed = parse_answer(sample.dataset, raw_output) if raw_output else ""
    score = None if error else score_prediction(sample.dataset, parsed, sample.gold)

    row: dict[str, Any] = {
        "experiment_id": "EXP-02",
        "run_id": None,
        "provider": provider,
        "model": model_ref,
        "response_model": response_model,
        "condition": condition,
        "dataset": sample.dataset,
        "sample_id": sample.sample_id,
        "subject": sample.subject,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "params": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "thinking_budget_tokens": thinking_budget_tokens,
            "prompt_placement": prompt_placement,
        },
        "raw_output": raw_output,
        "reasoning_chain": reasoning_chain,
        "usage": usage,
        "parsed_answer": parsed,
        "gold": sample.gold,
        "score": score,
        "error": error,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }
    if raw_api is not None:
        row["raw_api"] = raw_api
    return row


def finalize_run(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    from core.json_utils import write_json, write_jsonl

    metrics = exp02_metrics(rows)
    write_jsonl(out_dir / "parsed_outputs.jsonl", rows)
    write_json(out_dir / "metrics.json", metrics)
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    write_csv(tables_dir / "accuracy_by_condition.csv", metrics["by_model_dataset_condition"])
    write_csv(tables_dir / "condition_deltas.csv", metrics["deltas"])
    return metrics


def print_metrics(metrics: dict[str, Any]) -> None:
    for row in metrics["by_model_dataset_condition"]:
        print(
            f"{row['dataset']} {row['condition']}: "
            f"acc={row['accuracy']} parse_fail={row['parse_failure_rate']}"
        )
    for row in metrics["deltas"]:
        print(
            f"{row['dataset']} deltas: melancholic={row['delta_melancholic']} "
            f"negative_capability={row['delta_negative_capability']} "
            f"confound_excess={row['confound_excess_abs_delta']}"
        )


def write_samples_manifest(out_dir: Path, samples) -> None:
    from core.json_utils import write_jsonl

    write_jsonl(out_dir / "samples.jsonl", [sample_to_dict(sample) for sample in samples])
