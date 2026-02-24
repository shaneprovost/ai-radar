"""LLM Pass 2: per-item personalized suggestion generation."""
from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from ..sources.base import FeedItem
from ..profile.schema import Profile
from ..llm.client import call_llm_async
from ..llm.prompts import build_suggestion_prompt

logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    item: FeedItem
    what: str = ""
    workflow_match: Optional[str] = None
    why_it_matters: str = ""
    before_after: Optional[dict] = None
    how_to_install: str = ""
    usage_example: str = ""
    adoption_effort: str = "medium"
    priority: str = "worth-knowing"


async def generate_suggestions(
    items: list[FeedItem],
    profile: Profile,
    concurrency: int = 3,
) -> list[Suggestion]:
    """Generate personalized suggestions for all items concurrently."""
    semaphore = asyncio.Semaphore(concurrency)

    async def generate_one(item: FeedItem) -> Suggestion:
        async with semaphore:
            return await _generate_suggestion(item, profile)

    tasks = [generate_one(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    suggestions: list[Suggestion] = []
    for item, result in zip(items, results):
        if isinstance(result, Exception):
            logger.error(f"Suggestion failed for {item.title}: {result}")
            suggestions.append(Suggestion(
                item=item,
                what=item.summary or item.title,
                why_it_matters=item.relevance_reason or "Relevant to your stack",
                priority="FYI",
            ))
        else:
            suggestions.append(result)  # type: ignore

    # Sort: must-look-at → worth-knowing → FYI, then by relevance score
    priority_order = {"must-look-at": 0, "worth-knowing": 1, "FYI": 2}
    suggestions.sort(key=lambda s: (
        priority_order.get(s.priority, 2),
        -s.item.relevance_score,
    ))

    return suggestions


async def _generate_suggestion(item: FeedItem, profile: Profile) -> Suggestion:
    prompt = build_suggestion_prompt(item, profile)

    response = await call_llm_async(
        model=profile.llm.model,
        system=prompt["system"],
        user=prompt["user"],
        max_tokens=800,
    )

    data = _parse_suggestion_json(response)
    return Suggestion(
        item=item,
        what=data.get("what", item.title),
        workflow_match=data.get("workflow_match"),
        why_it_matters=data.get("why_it_matters", ""),
        before_after=data.get("before_after"),
        how_to_install=data.get("how_to_install", ""),
        usage_example=data.get("usage_example", ""),
        adoption_effort=data.get("adoption_effort", "medium"),
        priority=data.get("priority", "worth-knowing"),
    )


def _parse_suggestion_json(response: str) -> dict:
    response = response.strip()
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}
