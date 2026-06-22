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


# ─────────────────────────────────────────────
# LINES 41-173
# PURPOSE:
# Standardized async wrappers for multiple LLM APIs.
#
# WHY IT EXISTS:
# By wrapping the specific nuances of Ollama (REST), OpenAI (SDK), Anthropic (SDK),
# and Gemini (SDK) into identical `(system, user) -> str` signatures, the rest of 
# CodeSense never has to care which provider is actively responding.
#
# ARCHITECTURE NOTE:
# This acts as an adapter layer (Adapter Pattern). It isolates third-party vendor
# lock-in. If we decide to add Cohere tomorrow, we simply add a `_call_cohere`
# function here and register it in the chain below.
# ─────────────────────────────────────────────

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


async def _call_gemini(system: str, user: str) -> str:
    settings = get_settings()
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "google-generativeai package is not installed. Run: pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY", getattr(settings, "GEMINI_API_KEY", ""))
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"))
    
    # We use an async wrapper or call it synchronously since it's an API call, 
    # but the python SDK `generate_content_async` exists
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system)
    
    response = await model.generate_content_async(
        user,
        generation_config=genai.types.GenerationConfig(
            temperature=float(os.getenv("LLM_TEMPERATURE", str(settings.LLM_TEMPERATURE))),
            max_output_tokens=int(os.getenv("LLM_MAX_TOKENS", str(settings.LLM_MAX_TOKENS))),
        )
    )
    text = response.text if response else ""
    logger.debug(
        "Gemini [{model}] response: {n} chars",
        model=model_name,
        n=len(text),
    )
    return text


# ─────────────────────────────────────────────
# LINES 176-224
# PURPOSE:
# The global entry point for all LLM inference in the platform, featuring
# an automated provider fallback chain.
#
# WHY IT EXISTS:
# Relying on a single API provider in a production environment is dangerous.
# If OpenAI goes down, or Ollama OOMs the Render container, the entire RAG pipeline
# breaks. This function catches connection/quota errors and transparently fails over.
#
# INTERVIEW QUESTION:
# "How does CodeSense guarantee uptime during LLM outages?"
#
# GOOD ANSWER:
# "I built a resilient Chain-of-Responsibility fallback mechanism. If Gemini fails 
# due to rate limits, it silently catches the exception and attempts OpenAI. If 
# OpenAI fails, it tries Anthropic, then local Ollama, and finally falls back to
# a static mock response. The user always gets an answer without seeing a 500 server error."
# ─────────────────────────────────────────────

async def complete(
    system_prompt: str,
    user_prompt: str,
    provider: Optional[str] = None,
) -> str:
    # FUNCTION PURPOSE:
    # Safely route prompts to the best available LLM with cascading fallbacks.
    
    settings = get_settings()
    enable_llm = os.getenv("ENABLE_LLM", str(settings.ENABLE_LLM)).lower() == "true"
    if not enable_llm:
        raise LLMUnavailableError("Local LLM unavailable. (Disabled in settings)")

    p = provider or get_provider()
    
    # Implement Provider Chain: Gemini -> OpenAI -> Anthropic -> Ollama -> Local Fallback
    providers_to_try = [p] if provider else [p, "gemini", "openai", "anthropic", "ollama", "local"]
    
    # Deduplicate while preserving order
    seen = set()
    providers_to_try = [x for x in providers_to_try if not (x in seen or seen.add(x))]

    last_error = None

    for current_provider in providers_to_try:
        try:
            if current_provider == "gemini":
                return await _call_gemini(system_prompt, user_prompt)
            elif current_provider == "openai":
                return await _call_openai(system_prompt, user_prompt)
            elif current_provider == "anthropic":
                return await _call_anthropic(system_prompt, user_prompt)
            elif current_provider == "ollama":
                return await _call_ollama(system_prompt, user_prompt)
            elif current_provider == "local":
                # Graceful degradation at the very end of the chain
                return f"Extractive Preview: LLM capabilities are currently degraded (Fallback mode active). Cannot generate deep insights."
        except (RuntimeError, ImportError, LLMUnavailableError) as exc:
            last_error = exc
            logger.warning("Provider {provider} failed: {err}. Attempting fallback.", provider=current_provider, err=str(exc))
            continue
        except Exception as exc:
            last_error = exc
            logger.error("Provider {provider} threw unexpected error: {err}. Attempting fallback.", provider=current_provider, err=str(exc))
            continue

    if last_error:
        logger.error("All LLM providers failed. Last error: {err}", err=str(last_error))
    
    # Graceful degradation - do not crash
    return "LLM Error: Could not generate response. The AI provider is temporarily unavailable. Please verify API keys or local Ollama setup."


def normalize_model_name(name: str) -> str:
    """Normalize model names by lowercasing, stripping registry prefix, and trimming default tag."""
    name = name.lower().split('/')[-1]
    if name.endswith(':latest'):
        name = name[:-7]
    return name

async def validate_startup() -> None:
    """Validate that at least one LLM provider is available."""
    # FUNCTION PURPOSE:
    # Runs during the FastAPI startup lifecycle (`main.py`) to verify API keys
    # or ping the local Ollama instance. If nothing is available, it warns the user
    # immediately rather than waiting for them to type a RAG query.
    settings = get_settings()
    enable_llm = os.getenv("ENABLE_LLM", str(settings.ENABLE_LLM)).lower() == "true"
    if not enable_llm:
        logger.info("LLM features are disabled (ENABLE_LLM=false).")
        return

    # Check providers in order of fallback
    
    # 1. Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", getattr(settings, "GEMINI_API_KEY", ""))
    if gemini_key:
        logger.info("Gemini provider active (Configured via GEMINI_API_KEY)")
        return
        
    # 2. OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if openai_key:
        logger.info("OpenAI provider active (Configured via OPENAI_API_KEY)")
        return
        
    # 3. Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        logger.info("Anthropic provider active (Configured via ANTHROPIC_API_KEY)")
        return

    # 4. Ollama (Only check if no cloud providers are configured)
    base_url = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL)
    logger.info("Validating Ollama connection at {base_url} ...", base_url=base_url)
    client = _get_client()
    response_status = None
    available_models = []
    try:
        response = await client.get(f"{base_url}/api/tags", timeout=5.0)
        response_status = response.status_code
        if response.status_code != 200:
            raise LLMUnavailableError(f"Ollama returned status code {response.status_code}")
        
        data = response.json()
        available_models = [m.get("name") for m in data.get("models", [])]
        
        target_norm = normalize_model_name(model)
        model_loaded = False
        for m in available_models:
            if normalize_model_name(m) == target_norm:
                model_loaded = True
                break
        
        if not model_loaded:
            logger.warning(
                "LLM Startup Health-Check Failed for Ollama:\n"
                "  Base URL: {base_url}\n"
                "  Configured Model: {model}\n"
                "  Available Models: {available}\n"
                "  Response Status: {status}",
                base_url=base_url,
                model=model,
                available=available_models,
                status=response_status
            )
        else:
            logger.info("Ollama provider active")
            logger.info("Model loaded: {model}", model=model)
            return
    except Exception as exc:
        logger.warning(f"Ollama connection validation failed: {exc}")

    # If we got here, no provider is fully validated
    logger.warning("No LLM provider could be validated. Features will fall back gracefully to 'local' stub mode.")
