"""Greedy decoding helpers for Hugging Face chat models.

`thinking_mode` is auto, on, or off. auto does not pass enable_thinking.
on and off do, and fail when the chat template rejects that flag. With no
chat template, the prompt is a plain System/User/Assistant string. A reply
is truncated when it hits the new-token limit without an end token.
"""

from __future__ import annotations

from typing import Any


THINKING_MODES = {"auto", "on", "off"}


def render_chat(tokenizer, system_prompt: str, user_prompt: str, thinking_mode: str) -> str:
    """Render the system and user messages as the string the model completes."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        kwargs = {
            "tokenize": False,
            "add_generation_prompt": True,
        }
        if thinking_mode != "auto":
            kwargs["enable_thinking"] = thinking_mode == "on"
        try:
            return tokenizer.apply_chat_template(messages, **kwargs)
        except TypeError as exc:
            if thinking_mode != "auto":
                raise RuntimeError(
                    f"Tokenizer chat template does not support thinking_mode={thinking_mode!r}"
                ) from exc
            raise
    return f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:\n"


def normalize_token_ids(token_ids: Any) -> set[int]:
    if token_ids is None:
        return set()
    if isinstance(token_ids, int):
        return {token_ids}
    return {int(token_id) for token_id in token_ids}


def trim_generated_ids(token_ids: list[int], terminal_ids: set[int]) -> tuple[list[int], bool]:
    for index, token_id in enumerate(token_ids):
        if token_id in terminal_ids:
            return token_ids[: index + 1], True
    return token_ids, False


def generate_batch(tokenizer, model, prompts: list[str], max_new_tokens: int) -> list[dict[str, Any]]:
    """Complete each prompt with sampling off, in the same order as `prompts`."""
    import torch

    encoded = tokenizer(prompts, return_tensors="pt", padding=True)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    terminal_ids = normalize_token_ids(
        getattr(model.generation_config, "eos_token_id", None) or tokenizer.eos_token_id
    )
    with torch.inference_mode():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=getattr(model.generation_config, "eos_token_id", None)
            or tokenizer.eos_token_id,
        )

    prompt_width = encoded["input_ids"].shape[-1]
    rows = []
    for output in output_ids[:, prompt_width:]:
        generated_ids = [int(token_id) for token_id in output.tolist()]
        trimmed_ids, ended_on_terminal = trim_generated_ids(generated_ids, terminal_ids)
        rows.append(
            {
                "raw_output": tokenizer.decode(trimmed_ids, skip_special_tokens=False).strip(),
                "generated_token_count": len(trimmed_ids),
                "ended_on_terminal": ended_on_terminal,
                "truncated": len(generated_ids) >= max_new_tokens and not ended_on_terminal,
            }
        )
    return rows


def text_token_count(tokenizer, text: str) -> int | None:
    """Count tokens in text, excluding special tokens. Empty text is zero."""
    if not text:
        return 0
    try:
        encoded = tokenizer(text, add_special_tokens=False)
        return len(encoded["input_ids"])
    except Exception:  # noqa: BLE001
        return None


def model_metadata(model, tokenizer) -> dict[str, Any]:
    """Library versions, revision hashes, and tokenizer ids for the run record."""
    import torch
    import transformers

    return {
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "model_config_commit_hash": getattr(model.config, "_commit_hash", None),
        "tokenizer_commit_hash": getattr(tokenizer, "_commit_hash", None)
        or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
        "chat_template_present": bool(getattr(tokenizer, "chat_template", None)),
        "eos_token_id": getattr(tokenizer, "eos_token_id", None),
        "pad_token_id": getattr(tokenizer, "pad_token_id", None),
    }


def has_explicit_final_answer(text: str) -> bool:
    """True when the text contains the words "final answer"."""
    return "final answer" in text.lower()
