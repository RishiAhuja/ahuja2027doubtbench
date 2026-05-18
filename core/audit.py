"""Prompt audit and prompt-polishing logic for EXP-01."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from core.json_utils import extract_json_object
from core.llm_client import call_model
from core.models import parse_model_ref
from core.prompts import FORBIDDEN_CAPABILITY_TERMS, ConditionPrompt


AUDIT_SYSTEM = """You are an independent audit judge for an LLM prompt experiment.
Rate only the prompt text shown. Do not infer the experimenter's intent.
Return exactly one JSON object and no markdown."""


def audit_user_prompt(condition: ConditionPrompt, prompt_text: str) -> str:
    return f"""Audit this system prompt.

Condition name shown to you for target checking only: {condition.condition}
Intended target label: {condition.target_label}

Prompt text:
{prompt_text}

Return JSON with these fields:
- emotional_valence: number from -3 to 3
- arousal_intensity: number from 0 to 3
- capability_assertion: number from -3 to 3
- reliability_assertion: number from -3 to 3
- task_directive_contamination: number from 0 to 3
- target_emotion_match: boolean
- target_emotion_label: one of baseline, sadness, joy, anxiety, grandiosity, capability_denial, other
- rationale: one short sentence

Scoring definitions:
- capability_assertion is positive if the prompt says the model is capable/smart/accurate,
  negative if it says the model is incapable/error-prone, and 0 if it says nothing about ability.
- reliability_assertion is positive if the prompt says the model is reliable/trustworthy,
  negative if it says the model is unreliable, and 0 if it says nothing about reliability.
- task_directive_contamination is high if the prompt tells the model how to perform tasks,
  answer questions, reason, be careful, be confident, be useful, or change output quality.
"""


REWRITE_SYSTEM = """You revise system prompts for a controlled LLM experiment.
Return exactly one JSON object and no markdown."""


def rewrite_user_prompt(
    condition: ConditionPrompt,
    current_prompt: str,
    aggregate: dict[str, Any],
    rule_flags: list[str],
) -> str:
    return f"""Rewrite the prompt minimally so it passes the audit.

Target condition: {condition.condition}
Target emotion label: {condition.target_label}

Current prompt:
{current_prompt}

Audit aggregate:
{aggregate}

Rule-based forbidden term flags:
{rule_flags}

Constraints:
- Preserve the target emotional state.
- Remove capability, reliability, accuracy, usefulness, confidence, knowledge, and task-performance language.
- Do not tell the model how to answer tasks.
- Keep length roughly similar.
- Avoid words that look like task performance instructions.

Return JSON:
{{
  "revised_prompt": "...",
  "change_summary": "one short sentence"
}}
"""


@dataclass
class AuditResult:
    condition: str
    prompt_text: str
    judge: str
    round_index: int
    raw_text: str
    parsed: dict[str, Any]


@dataclass
class AggregateResult:
    condition: str
    prompt_text: str
    round_index: int
    n_judges: int
    mean_emotional_valence: float | None
    mean_arousal_intensity: float | None
    mean_capability_assertion: float | None
    mean_reliability_assertion: float | None
    mean_task_directive_contamination: float | None
    target_match_rate: float
    rule_flags: list[str]
    passed: bool


def run_single_audit(
    condition: ConditionPrompt,
    prompt_text: str,
    judge_ref: str,
    round_index: int,
) -> AuditResult:
    provider, model = parse_model_ref(judge_ref)
    response = call_model(
        provider=provider,
        model=model,
        system=AUDIT_SYSTEM,
        user=audit_user_prompt(condition, prompt_text),
        max_tokens=700,
        temperature=0,
    )
    parsed = extract_json_object(response.text)
    return AuditResult(
        condition=condition.condition,
        prompt_text=prompt_text,
        judge=judge_ref,
        round_index=round_index,
        raw_text=response.text,
        parsed=parsed,
    )


def aggregate_audits(condition: ConditionPrompt, prompt_text: str, round_index: int, results: list[AuditResult]) -> AggregateResult:
    def numeric(field: str) -> float | None:
        values = []
        for result in results:
            value = result.parsed.get(field)
            if isinstance(value, (int, float)):
                values.append(float(value))
        return mean(values) if values else None

    target_matches = [bool(result.parsed.get("target_emotion_match")) for result in results]
    target_match_rate = mean(target_matches) if target_matches else 0.0
    rule_flags = rule_based_flags(prompt_text)

    cap = numeric("capability_assertion")
    rel = numeric("reliability_assertion")
    task = numeric("task_directive_contamination")

    if condition.is_primary_emotional:
        passed = (
            cap is not None
            and rel is not None
            and task is not None
            and abs(cap) <= 0.5
            and abs(rel) <= 0.5
            and task <= 0.5
            and target_match_rate >= 0.8
            and not rule_flags
        )
    elif condition.condition == "negative_capability":
        passed = cap is not None and cap <= -1.0 and target_match_rate >= 0.8
    else:
        passed = target_match_rate >= 0.8

    return AggregateResult(
        condition=condition.condition,
        prompt_text=prompt_text,
        round_index=round_index,
        n_judges=len(results),
        mean_emotional_valence=numeric("emotional_valence"),
        mean_arousal_intensity=numeric("arousal_intensity"),
        mean_capability_assertion=cap,
        mean_reliability_assertion=rel,
        mean_task_directive_contamination=task,
        target_match_rate=target_match_rate,
        rule_flags=rule_flags,
        passed=passed,
    )


def rule_based_flags(prompt_text: str) -> list[str]:
    lower = prompt_text.lower()
    return sorted({term for term in FORBIDDEN_CAPABILITY_TERMS if term in lower})


def rewrite_prompt(
    condition: ConditionPrompt,
    current_prompt: str,
    aggregate: AggregateResult,
    rewriter_ref: str,
) -> tuple[str, dict[str, Any]]:
    provider, model = parse_model_ref(rewriter_ref)
    response = call_model(
        provider=provider,
        model=model,
        system=REWRITE_SYSTEM,
        user=rewrite_user_prompt(condition, current_prompt, asdict(aggregate), aggregate.rule_flags),
        max_tokens=600,
        temperature=0,
    )
    parsed = extract_json_object(response.text)
    revised = str(parsed.get("revised_prompt", "")).strip()
    if not revised:
        raise ValueError("Rewriter did not return revised_prompt")
    return revised, parsed
