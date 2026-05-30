# backend/app/ml/llm_client.py
"""
CodeSense — LLM Client Abstraction Layer
"""

from __future__ import annotations

import os
from typing import Optional
import httpx

from app_logger import logger
from app.core.config import get_settings


class LLMProviderError(Exception):
    """Raised when an LLM provider fails, quota is exceeded, or key is missing."""
    pass


class LLMUnavailableError(Exception):
    """Raised when the LLM is disabled or local LLM (Ollama) is unavailable."""
    pass


_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


def get_provider() -> str:
    """Return the active LLM provider (ollama, openai, anthropic, etc.)."""
    return os.getenv("LLM_PROVIDER", get_settings().LLM_PROVIDER).lower()


async def _call_ollama(system: str, user: str) -> str:
    settings = get_settings()
    base_url = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL)
    client = _get_client()
    
    try:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {
                    "temperature": float(os.getenv("LLM_TEMPERATURE", str(settings.LLM_TEMPERATURE))),
                    "num_predict": int(os.getenv("LLM_MAX_TOKENS", str(settings.LLM_MAX_TOKENS))),
                }
            },
            timeout=30.0,
        )
        if response.status_code != 200:
            raise LLMUnavailableError(f"Ollama returned status code {response.status_code}")
        
        data = response.json()
        return data.get("message", {}).get("content", "")
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise LLMUnavailableError(f"Local LLM unavailable. (Connection error: {str(exc)})")


async def _call_openai(system: str, user: str) -> str:
    settings = get_settings()
    try:
        import openai
    except ImportError:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        )

    api_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file."
        )

    model = os.getenv("OPENAI_MODEL", settings.OPENAI_MODEL)
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", str(settings.LLM_MAX_TOKENS))),
        temperature=float(os.getenv("LLM_TEMPERATURE", str(settings.LLM_TEMPERATURE))),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    logger.debug(
        "OpenAI [{model}] response: {n} chars", model=model, n=len(text)
    )
    return text


async def _call_anthropic(system: str, user: str) -> str:
    settings = get_settings()
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

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model=model,
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", str(settings.LLM_MAX_TOKENS))),
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = message.content[0].text if message.content else ""
    logger.debug(
        "Anthropic [{model}] response: {n} chars",
        model=model,
        n=len(text),
    )
    return text


async def complete(
    system_prompt: str,
    user_prompt: str,
    provider: Optional[str] = None,
) -> str:
    settings = get_settings()
    enable_llm = os.getenv("ENABLE_LLM", str(settings.ENABLE_LLM)).lower() == "true"
    if not enable_llm:
        raise LLMUnavailableError("Local LLM unavailable. (Disabled in settings)")

    p = provider or get_provider()

    try:
        if p == "ollama":
            return await _call_ollama(system_prompt, user_prompt)
        elif p == "openai":
            return await _call_openai(system_prompt, user_prompt)
        elif p == "anthropic":
            return await _call_anthropic(system_prompt, user_prompt)
        elif p == "local":
            return f"Extractive Preview: Local fallback mode active (Provider is {p})."
    except LLMUnavailableError:
        raise
    except (RuntimeError, ImportError) as exc:
        logger.warning("LLM initialization failed ({provider}): {err}", provider=p, err=str(exc))
        return f"LLM Error: LLM initialization failed ({p}): {exc}"
    except Exception as exc:
        logger.error("LLM completion API failed ({provider}): {err}", provider=p, err=str(exc))
        return f"LLM Error ({p}): {exc}"

    raise LLMUnavailableError(f"Local LLM unavailable. (Unsupported provider: {p})")


async def validate_startup() -> None:
    """Validate that Ollama is running and the required model is loaded."""
    settings = get_settings()
    enable_llm = os.getenv("ENABLE_LLM", str(settings.ENABLE_LLM)).lower() == "true"
    if not enable_llm:
        logger.info("LLM features are disabled (ENABLE_LLM=false).")
        return

    provider = get_provider()
    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL).rstrip("/")
        model = os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL)
        logger.info("Validating Ollama connection at {base_url} ...", base_url=base_url)
        client = _get_client()
        try:
            response = await client.get(f"{base_url}/api/tags", timeout=2.0)
            if response.status_code != 200:
                raise LLMUnavailableError(f"Ollama returned status code {response.status_code}")
            
            data = response.json()
            models = [m.get("name") for m in data.get("models", [])]
            model_loaded = False
            for m in models:
                if m == model or m == f"{model}:latest" or model == f"{m}:latest" or m.startswith(model.split(':')[0]):
                    model_loaded = True
                    break
            
            if not model_loaded:
                raise LLMUnavailableError(f"Model '{model}' is not loaded in Ollama. Available: {models}")
            
            logger.info("Ollama provider active")
            logger.info("Model loaded: {model}", model=model)
        except Exception as exc:
            raise LLMUnavailableError(f"Ollama connection validation failed: {exc}")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
        if not api_key:
            raise LLMUnavailableError("OPENAI_API_KEY is not set.")
        logger.info("OpenAI provider active")
