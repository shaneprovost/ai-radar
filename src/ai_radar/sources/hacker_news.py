"""Hacker News fetcher via Algolia API."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib

import httpx

from .base import FeedItem

HN_API = "https://hn.algolia.com/api/v1/search"


def fetch_hacker_news(
    days: int = 7,
    min_score: int = 50,
    limit: int = 30,
) -> list[FeedItem]:
    items = []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_ts = int(since.timestamp())

    params = {
        "query": "AI LLM Claude OpenAI machine learning agent",
        "tags": "story",
        "numericFilters": f"created_at_i>{since_ts},points>={min_score}",
        "hitsPerPage": limit,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(HN_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            title = hit.get("title", "").strip()
            if not title:
                continue

            item_id = hashlib.md5(url.encode()).hexdigest()[:12]
            published = None
            if ts := hit.get("created_at_i"):
                published = datetime.fromtimestamp(ts, tz=timezone.utc)

            items.append(FeedItem(
                id=f"hn_{item_id}",
                title=title,
                url=url,
                source="Hacker News",
                published_at=published,
                summary=hit.get("story_text", "")[:300],
                score=hit.get("points", 0),
                tags=["hacker-news"],
            ))
    except Exception as e:
        print(f"[HN] fetch error: {e}")

    return sorted(items, key=lambda x: x.score, reverse=True)
