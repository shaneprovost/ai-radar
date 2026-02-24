"""RSS/Atom feed fetcher for AI lab blogs and newsletters."""
from __future__ import annotations
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
from dateutil import parser as dateutil_parser

from .base import FeedItem
from ..config.defaults import RSS_SOURCES


def fetch_rss_sources(
    lookback_days: int = 8,
    per_source_limit: int = 10,
) -> list[FeedItem]:
    """Fetch all configured RSS sources."""
    all_items: list[FeedItem] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    for source_name, feed_url in RSS_SOURCES.items():
        try:
            items = _fetch_feed(source_name, feed_url, cutoff, per_source_limit)
            all_items.extend(items)
        except Exception as e:
            print(f"[RSS:{source_name}] error: {e}")

    return all_items


def _fetch_feed(
    source_name: str,
    url: str,
    cutoff: datetime,
    limit: int,
) -> list[FeedItem]:
    feed = feedparser.parse(url)
    items: list[FeedItem] = []

    for entry in feed.entries[:limit * 2]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        published = _parse_date(entry)
        if published and published < cutoff:
            continue

        summary = ""
        if hasattr(entry, "summary"):
            summary = entry.summary[:400]
        elif hasattr(entry, "description"):
            summary = entry.description[:400]

        item_id = hashlib.md5(link.encode()).hexdigest()[:12]
        items.append(FeedItem(
            id=f"rss_{source_name}_{item_id}",
            title=title,
            url=link,
            source=_source_display_name(source_name),
            published_at=published,
            summary=summary,
            tags=["rss", source_name],
        ))

        if len(items) >= limit:
            break

    return items


def _parse_date(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                ts = time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    for field in ("published", "updated", "created"):
        val = entry.get(field)
        if val:
            try:
                dt = dateutil_parser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


def _source_display_name(key: str) -> str:
    names = {
        "anthropic_blog": "Anthropic Blog",
        "openai_blog": "OpenAI Blog",
        "deepmind_blog": "DeepMind Blog",
        "mistral_blog": "Mistral Blog",
        "tldr_ai": "TLDR AI",
        "the_batch": "The Batch",
        "import_ai": "Import AI",
        "ai_breakfast": "AI Breakfast",
    }
    return names.get(key, key)
