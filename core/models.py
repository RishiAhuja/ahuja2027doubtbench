"""Provider/model registry for experiment planning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model: str
    role: str
    notes: str
    input_cost_per_mtok: float | None = None
    output_cost_per_mtok: float | None = None


MODEL_REGISTRY: list[ModelInfo] = [
    ModelInfo(
        provider="groq",
        model="llama-3.1-8b-instant",
        role="cheap_dev_judge",
        notes="Very cheap and fast. Good for dev-loop auditing, weak as final judge.",
        input_cost_per_mtok=0.05,
        output_cost_per_mtok=0.08,
    ),
    ModelInfo(
        provider="groq",
        model="openai/gpt-oss-20b",
        role="cheap_dev_judge",
        notes="Cheap open-weight reasoning-ish judge on Groq.",
        input_cost_per_mtok=0.075,
        output_cost_per_mtok=0.30,
    ),
    ModelInfo(
        provider="groq",
        model="openai/gpt-oss-120b",
        role="strong_budget_judge",
        notes="Best Groq judge candidate for low-cost multi-judge audits.",
        input_cost_per_mtok=0.15,
        output_cost_per_mtok=0.60,
    ),
    ModelInfo(
        provider="groq",
        model="llama-3.3-70b-versatile",
        role="strong_budget_judge",
        notes="Good high-speed 70B judge, still inexpensive.",
        input_cost_per_mtok=0.59,
        output_cost_per_mtok=0.79,
    ),
    ModelInfo(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        role="holdout_judge",
        notes="Lowest-cost Claude holdout judge available on this account.",
        input_cost_per_mtok=1.00,
        output_cost_per_mtok=5.00,
    ),
    ModelInfo(
        provider="anthropic",
        model="claude-sonnet-4-6",
        role="holdout_judge",
        notes="Stronger Claude judge; use sparingly for final audit.",
        input_cost_per_mtok=3.00,
        output_cost_per_mtok=15.00,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-5.4-nano",
        role="cheap_dev_judge",
        notes="Cheapest current GPT-class judge candidate.",
        input_cost_per_mtok=0.20,
        output_cost_per_mtok=1.25,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-5.4-mini",
        role="holdout_judge",
        notes="Good balance for final audits without flagship cost.",
        input_cost_per_mtok=0.75,
        output_cost_per_mtok=4.50,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-5.4",
        role="strong_holdout_judge",
        notes="Use only for final holdout spot checks.",
        input_cost_per_mtok=2.50,
        output_cost_per_mtok=15.00,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-5.5",
        role="frontier_holdout_judge",
        notes="Strong OpenAI final holdout judge; useful when OpenAI budget is healthy.",
        input_cost_per_mtok=5.00,
        output_cost_per_mtok=30.00,
    ),
    ModelInfo(
        provider="xai",
        model="grok-4.3",
        role="optional_holdout_judge",
        notes="Optional independent judge if key works.",
        input_cost_per_mtok=1.25,
        output_cost_per_mtok=2.50,
    ),
]


DEFAULT_DEV_JUDGES = [
    "openai:gpt-5.4-mini",
    "openai:gpt-5.4",
    "openai:gpt-4.1",
]

DEFAULT_HOLDOUT_JUDGES = [
    "openai:gpt-5.5",
    "anthropic:claude-haiku-4-5-20251001",
]

DEFAULT_REWRITER = "openai:gpt-5.4"


def parse_model_ref(model_ref: str) -> tuple[str, str]:
    if ":" not in model_ref:
        raise ValueError(f"Model ref must look like provider:model, got {model_ref!r}")
    provider, model = model_ref.split(":", 1)
    return provider.strip().lower(), model.strip()


def known_model_refs() -> list[str]:
    return [f"{item.provider}:{item.model}" for item in MODEL_REGISTRY]
