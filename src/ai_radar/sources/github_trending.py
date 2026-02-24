"""GitHub trending fetcher — unofficial JSON API with BS4 HTML fallback."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .base import FeedItem

TRENDING_URL = "https://github.com/trending"
UNOFFICIAL_API = "https://api.ghrend.com/trending"  # community mirror


def fetch_github_trending(language: str = "", period: str = "weekly") -> list[FeedItem]:
    """Fetch GitHub trending repos. Tries unofficial API first, falls back to HTML scrape."""
    items = _try_unofficial_api(period)
    if not items:
        items = _scrape_html(language, period)
    return items


def _try_unofficial_api(period: str = "weekly") -> list[FeedItem]:
    """Try ghrend.com community API."""
    items = []
    try:
        url = f"{UNOFFICIAL_API}?since={period}"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                return []
            data = resp.json()

        repo_list = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(repo_list, list):
            return []

        for repo in repo_list[:40]:
            if not isinstance(repo, dict):
                continue
            name = repo.get("full_name") or repo.get("name", "")
            if not name:
                continue
            url_val = repo.get("url") or f"https://github.com/{name}"
            desc = repo.get("description") or ""
            stars = repo.get("stars") or repo.get("stargazers_count") or 0

            item_id = hashlib.md5(url_val.encode()).hexdigest()[:12]
            items.append(FeedItem(
                id=f"gh_{item_id}",
                title=name,
                url=url_val,
                source="GitHub Trending",
                published_at=datetime.now(timezone.utc),
                summary=desc[:300],
                score=int(stars) if isinstance(stars, (int, float)) else 0,
                tags=["github-trending"],
            ))
    except Exception:
        pass
    return items


def _scrape_html(language: str = "", period: str = "weekly") -> list[FeedItem]:
    """Scrape GitHub trending HTML page."""
    items = []
    try:
        url = TRENDING_URL
        if language:
            url = f"{TRENDING_URL}/{language}"

        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, params={"since": period}, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ai-radar/0.1)"
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        for article in soup.select("article.Box-row"):
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip("/")
            if not repo_path:
                continue
            repo_url = f"https://github.com/{repo_path}"

            desc_el = article.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            stars_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_text = stars_el.get_text(strip=True) if stars_el else "0"
            stars_num = _parse_stars(stars_text)

            item_id = hashlib.md5(repo_url.encode()).hexdigest()[:12]
            items.append(FeedItem(
                id=f"gh_{item_id}",
                title=repo_path,
                url=repo_url,
                source="GitHub Trending",
                published_at=datetime.now(timezone.utc),
                summary=desc[:300],
                score=stars_num,
                tags=["github-trending"],
            ))
    except Exception as e:
        print(f"[GitHub Trending] HTML scrape error: {e}")
    return items


def _parse_stars(text: str) -> int:
    text = text.replace(",", "").strip()
    match = re.search(r"([\d.]+)\s*([km]?)", text.lower())
    if not match:
        return 0
    num = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        num *= 1000
    elif suffix == "m":
        num *= 1_000_000
    return int(num)
