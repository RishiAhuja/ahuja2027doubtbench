"""Minimal provider clients using environment variables and stdlib HTTP."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    provider: str
    model: str
    text: str
    raw: dict[str, Any]


def _post_json(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_s: int = 120,
    retries: int = 2,
) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            last_error = ProviderError(f"HTTP {exc.code} from {url}: {message[:500]}")
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise ProviderError(str(last_error))


def _get_json(url: str, headers: dict[str, str], timeout_s: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"HTTP {exc.code} from {url}: {message[:500]}") from exc


def env_key_for_provider(provider: str) -> str:
    keys = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "xai": "XAI_API_KEY",
    }
    try:
        return keys[provider]
    except KeyError as exc:
        raise ValueError(f"Unknown provider {provider!r}") from exc


def provider_available(provider: str) -> bool:
    return bool(os.environ.get(env_key_for_provider(provider)))


def call_model(
    provider: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.0,
) -> LLMResponse:
    provider = provider.lower()
    if provider == "openai":
        return _call_openai(model, system, user, max_tokens, temperature)
    if provider == "anthropic":
        return _call_anthropic(model, system, user, max_tokens, temperature)
    if provider == "groq":
        return _call_openai_compatible(
            provider="groq",
            base_url="https://api.groq.com/openai/v1",
            env_key="GROQ_API_KEY",
            model=model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "xai":
        return _call_openai_compatible(
            provider="xai",
            base_url="https://api.x.ai/v1",
            env_key="XAI_API_KEY",
            model=model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    raise ValueError(f"Unknown provider {provider!r}")


def list_provider_models(provider: str) -> dict[str, Any]:
    provider = provider.lower()
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OPENAI_API_KEY is not set")
        return _get_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        return _get_json(
            "https://api.anthropic.com/v1/models",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
    if provider == "groq":
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise ProviderError("GROQ_API_KEY is not set")
        return _get_json(
            "https://api.groq.com/openai/v1/models",
            {"Authorization": f"Bearer {key}"},
        )
    if provider == "xai":
        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise ProviderError("XAI_API_KEY is not set")
        return _get_json("https://api.x.ai/v1/models", {"Authorization": f"Bearer {key}"})
    raise ValueError(f"Unknown provider {provider!r}")


def _call_openai(
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> LLMResponse:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderError("OPENAI_API_KEY is not set")
    body = {
        "model": model,
        "instructions": system,
        "input": user,
        "max_output_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        raw = _post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            body,
        )
    except ProviderError as exc:
        if "Unsupported parameter" not in str(exc) or "temperature" not in str(exc):
            raise
        body.pop("temperature", None)
        raw = _post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            body,
        )
    text = raw.get("output_text")
    if not text:
        text = _extract_openai_response_text(raw)
    return LLMResponse(provider="openai", model=model, text=text, raw=raw)


def _extract_openai_response_text(raw: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in raw.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    return "\n".join(part for part in parts if part).strip()


def _call_anthropic(
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> LLMResponse:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ProviderError("ANTHROPIC_API_KEY is not set")
    raw = _post_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        {
            "model": model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
    )
    parts = [item.get("text", "") for item in raw.get("content", []) if item.get("type") == "text"]
    return LLMResponse(provider="anthropic", model=model, text="\n".join(parts).strip(), raw=raw)


def _call_openai_compatible(
    provider: str,
    base_url: str,
    env_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> LLMResponse:
    key = os.environ.get(env_key)
    if not key:
        raise ProviderError(f"{env_key} is not set")
    raw = _post_json(
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {key}"},
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        },
    )
    text = raw["choices"][0]["message"].get("content", "")
    return LLMResponse(provider=provider, model=model, text=text.strip(), raw=raw)
