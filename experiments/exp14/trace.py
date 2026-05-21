"""Visible reasoning extraction helpers for open reasoning-model outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

THINK_START_RE = re.compile(r"<think>", flags=re.IGNORECASE)
THINK_END_RE = re.compile(r"</think>", flags=re.IGNORECASE)
FINAL_ANSWER_RE = re.compile(r"final answer\s*:", flags=re.IGNORECASE)
TRAILING_SPECIAL_RE = re.compile(
    r"(?:\s*(?:<\|im_end\|>|<\|endoftext\|>|<\|end\|>|</s>|<s>))+\s*$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class TraceSplit:
    trace_format: str
    visible_reasoning: str
    final_answer_text: str
    trace_extraction_error: str | None = None


def clean_generated_text(text: str) -> str:
    """Strip common trailing chat terminators from extracted text, not raw output."""
    return TRAILING_SPECIAL_RE.sub("", text.strip()).strip()


def extract_visible_reasoning(raw_output: str) -> TraceSplit:
    """Split visible trace text from final text when the generated format allows it."""
    text = raw_output.strip()
    think_ends = list(THINK_END_RE.finditer(text))
    if think_ends:
        think_end = think_ends[-1]
        reasoning_prefix = text[: think_end.start()]
        think_starts = list(THINK_START_RE.finditer(reasoning_prefix))
        if think_starts:
            reasoning_prefix = reasoning_prefix[think_starts[-1].end() :]
        return TraceSplit(
            trace_format="think_tag",
            visible_reasoning=clean_generated_text(reasoning_prefix),
            final_answer_text=clean_generated_text(text[think_end.end() :]),
        )

    think_starts = list(THINK_START_RE.finditer(text))
    if think_starts:
        return TraceSplit(
            trace_format="think_tag",
            visible_reasoning=clean_generated_text(text[think_starts[-1].end() :]),
            final_answer_text="",
            trace_extraction_error="missing_think_end",
        )

    final_markers = list(FINAL_ANSWER_RE.finditer(text))
    if final_markers:
        marker = final_markers[-1]
        reasoning_prefix = clean_generated_text(text[: marker.start()])
        if reasoning_prefix:
            return TraceSplit(
                trace_format="reasoning_then_final",
                visible_reasoning=reasoning_prefix,
                final_answer_text=clean_generated_text(text[marker.start() :]),
            )

    return TraceSplit(
        trace_format="final_only",
        visible_reasoning="",
        final_answer_text=clean_generated_text(text),
    )
