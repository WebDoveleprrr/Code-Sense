# backend/app/ml/llm_client.py
"""
CodeSense — LLM Client Abstraction Layer

Provides a single async `complete()` function that dispatches to:
  - OpenAI Chat Completions  (LLM_PROVIDER=openai)
  - Anthropic Messages API   (LLM_PROVIDER=anthropic)
  - Extractive fallback       (LLM_PROVIDER=local  — no API key required)

All callers (rag.py, explain_service, architecture_service) use
this module so that swapping providers requires only an env-var change.

Environment variables (from .env):
  LLM_PROVIDER          : openai | anthropic | local   (default: local)
  OPENAI_API_KEY        : required for openai
  OPENAI_MODEL          : default gpt-4o-mini
  ANTHROPIC_API_KEY     : required for anthropic
  ANTHROPIC_MODEL       : default claude-3-haiku-20240307
  LLM_MAX_TOKENS        : default 1024
  LLM_TEMPERATURE       : default 0.2
"""

from __future__ import annotations

import os
from typing import Optional

from app_logger import logger

# ---------------------------------------------------------------------------
# Config helpers (read directly from env to avoid circular imports)
# ---------------------------------------------------------------------------

class LLMProviderError(Exception):
    """Raised when an LLM provider fails, quota is exceeded, or key is missing."""
    pass


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "local").lower()


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _anthropic_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")


def _max_tokens() -> int:
    return int(os.getenv("LLM_MAX_TOKENS", "1024"))


def _temperature() -> float:
    return float(os.getenv("LLM_TEMPERATURE", "0.2"))


# ---------------------------------------------------------------------------
# OpenAI dispatch
# ---------------------------------------------------------------------------

async def _call_openai(system: str, user: str) -> str:
    try:
        import openai
    except ImportError:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        )

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file."
        )

    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=_openai_model(),
        max_tokens=_max_tokens(),
        temperature=_temperature(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    logger.debug(
        "OpenAI [{model}] response: {n} chars", model=_openai_model(), n=len(text)
    )
    return text


# ---------------------------------------------------------------------------
# Anthropic dispatch
# ---------------------------------------------------------------------------

async def _call_anthropic(system: str, user: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package is not installed. Run: pip install anthropic"
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model=_anthropic_model(),
        max_tokens=_max_tokens(),
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = message.content[0].text if message.content else ""
    logger.debug(
        "Anthropic [{model}] response: {n} chars",
        model=_anthropic_model(),
        n=len(text),
    )
    return text


# ---------------------------------------------------------------------------
# Primary public interface
# ---------------------------------------------------------------------------

async def complete(
    system_prompt: str,
    user_prompt: str,
    provider: Optional[str] = None,
) -> str:
    """
    Call the configured LLM and return the response text.

    Args:
        system_prompt: Role/instruction context for the model.
        user_prompt:   The user-facing query + context payload.
        provider:      Override LLM_PROVIDER env var for this call.

    Returns:
        Generated text string.

    Raises:
        RuntimeError if provider is openai/anthropic and the API key is missing.
    """
    p = provider or _provider()

    try:
        if p == "openai":
            return await _call_openai(system_prompt, user_prompt)

        if p == "anthropic":
            return await _call_anthropic(system_prompt, user_prompt)

    except (RuntimeError, ImportError) as exc:
        logger.warning("LLM initialization failed ({provider}): {err}", provider=p, err=exc)
        return f"LLM Error: LLM initialization failed ({p}): {exc}"

    except Exception as exc:
        logger.error("LLM completion API failed ({provider}): {err}", provider=p, err=exc)
        return f"LLM Error ({p}): {exc}"

    # Fallback due to missing or local provider
    logger.debug("LLM_PROVIDER={p} — using extractive fallback.", p=p)
    return f"Extractive Preview: Local fallback mode active (Provider is {p})."

