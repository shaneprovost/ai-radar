"""LLM Pass 1: batch-score all items 0-10 for relevance."""
from __future__ import annotations
import json
import logging

from ..sources.base import FeedItem
from ..profile.schema import Profile
from ..llm.client import call_llm
from ..llm.prompts import build_curation_prompt

logger = logging.getLogger(__name__)


def curate_items(
    items: list[FeedItem],
    profile: Profile,
    min_score: float = 6.0,
    max_items: int = 10,
) -> list[FeedItem]:
    """Score all items and return top N with score >= min_score."""
    if not items:
        return []

    prompt = build_curation_prompt(items, profile)

    try:
        response = call_llm(
            model=profile.llm.model,
            system=prompt["system"],
            user=prompt["user"],
            max_tokens=2000,
        )
        scores = _parse_scores(response)
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or ("invalid" in err.lower() and "key" in err.lower()):
            raise RuntimeError(
                f"Authentication failed for {profile.llm.model}. "
                f"Ensure the correct API key is exported in your shell:\n"
                f"  export ANTHROPIC_API_KEY='sk-ant-...'\n"
                f"  source ~/.zshrc\n"
                f"Then run: ai-radar update-profile  (to fix provider if it was set incorrectly)"
            ) from e
        logger.error(f"Curation LLM call failed: {e}")
        # Fallback: return items sorted by native score
        return sorted(items, key=lambda x: x.score, reverse=True)[:max_items]

    # Apply scores to items
    score_map = {entry["id"]: entry for entry in scores}
    scored: list[FeedItem] = []
    for item in items:
        if item.id in score_map:
            entry = score_map[item.id]
            item.relevance_score = float(entry.get("score", 0))
            item.relevance_reason = entry.get("reason", "")
        else:
            item.relevance_score = 0.0
        scored.append(item)

    relevant = [i for i in scored if i.relevance_score >= min_score]
    relevant.sort(key=lambda x: x.relevance_score, reverse=True)
    return relevant[:max_items]


def _parse_scores(response: str) -> list[dict]:
    """Parse JSON array from LLM response."""
    response = response.strip()
    start = response.find("[")
    end = response.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse curation response as JSON")
        return []
