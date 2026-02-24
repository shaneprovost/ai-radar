"""litellm wrapper with retry and exponential backoff."""
from __future__ import annotations
import asyncio
import logging
import os
import time

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds, doubles each retry

_PROVIDER_KEY_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
}


def _get_api_key(model: str) -> str | None:
    """Resolve API key from environment based on model prefix."""
    for prefix, env_var in _PROVIDER_KEY_MAP.items():
        if model.startswith(prefix):
            return os.environ.get(env_var)
    return None


def _suppress_litellm() -> None:
    import litellm
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    logging.getLogger("litellm").setLevel(logging.ERROR)


def call_llm(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1000,
) -> str:
    """Synchronous LLM call with retry."""
    import litellm
    _suppress_litellm()

    api_key = _get_api_key(model)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    last_error: Exception | None = None
    delay = _RETRY_DELAY

    for attempt in range(_MAX_RETRIES):
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                api_key=api_key,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if "429" in str(e) or "rate_limit" in str(e).lower():
                logger.warning(f"Rate limited on attempt {attempt+1}, retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(1)

    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts: {last_error}")


async def call_llm_async(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1000,
) -> str:
    """Async LLM call with retry."""
    import litellm
    _suppress_litellm()

    api_key = _get_api_key(model)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    last_error: Exception | None = None
    delay = _RETRY_DELAY

    for attempt in range(_MAX_RETRIES):
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                api_key=api_key,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if "429" in str(e) or "rate_limit" in str(e).lower():
                logger.warning(f"Rate limited (async) on attempt {attempt+1}, retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                if attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(1)

    raise RuntimeError(f"Async LLM call failed after {_MAX_RETRIES} attempts: {last_error}")
