"""Maps source names to fetcher functions and runs them concurrently."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from .base import FeedItem
from .github_trending import fetch_github_trending
from .hacker_news import fetch_hacker_news
from .rss import fetch_rss_sources


FETCHERS: dict[str, Callable[[], list[FeedItem]]] = {
    "github_trending": fetch_github_trending,
    "hacker_news": fetch_hacker_news,
    "rss": fetch_rss_sources,
}


def fetch_all_sources(sources: list[str] | None = None) -> tuple[list[FeedItem], dict[str, str]]:
    """Fetch all sources concurrently. Returns (items, errors)."""
    if sources is None:
        sources = list(FETCHERS.keys())

    all_items: list[FeedItem] = []
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {
            executor.submit(FETCHERS[name]): name
            for name in sources
            if name in FETCHERS
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                items = future.result()
                all_items.extend(items)
            except Exception as e:
                errors[name] = str(e)

    return all_items, errors
