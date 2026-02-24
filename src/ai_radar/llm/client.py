"""litellm wrapper with retry and exponential backoff."""
from __future__ import annotations
import asyncio
import logging
import os
import time

# Suppress litellm's noisy output before importing it
os.environ.setdefault("LITELLM_LOG", "ERROR")
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds, doubles each retry


def call_llm(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1000,
) -> str:
    """Synchronous LLM call with retry."""
    import litellm

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
