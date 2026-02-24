"""3-layer deduplication: exact URL, title similarity, domain+keywords."""
from __future__ import annotations
import re
from urllib.parse import urlparse

from ..sources.base import FeedItem


def deduplicate(items: list[FeedItem]) -> list[FeedItem]:
    """Remove duplicate items using 3-layer dedup."""
    # Layer 1: exact URL
    seen_urls: set[str] = set()
    unique: list[FeedItem] = []

    for item in items:
        norm_url = _normalize_url(item.url)
        if norm_url not in seen_urls:
            seen_urls.add(norm_url)
            unique.append(item)

    # Layer 2: title similarity (token overlap)
    filtered: list[FeedItem] = []
    seen_title_tokens: list[set[str]] = []

    for item in unique:
        tokens = _title_tokens(item.title)
        if not _is_similar_to_any(tokens, seen_title_tokens, threshold=0.7):
            filtered.append(item)
            seen_title_tokens.append(tokens)

    # Layer 3: domain + keyword overlap
    final: list[FeedItem] = []
    seen_domain_keys: list[tuple[str, frozenset[str]]] = []

    for item in filtered:
        domain = _extract_domain(item.url)
        keywords = _extract_keywords(item.title)
        if not _domain_keyword_overlap(domain, keywords, seen_domain_keys, threshold=3):
            final.append(item)
            seen_domain_keys.append((domain, keywords))

    return final


def _normalize_url(url: str) -> str:
    url = url.lower().strip().rstrip("/")
    if "?" in url:
        base, params = url.split("?", 1)
        clean_params = "&".join(
            p for p in params.split("&")
            if not any(p.startswith(utm) for utm in ("utm_", "ref=", "source="))
        )
        url = f"{base}?{clean_params}" if clean_params else base
    return url


def _title_tokens(title: str) -> set[str]:
    stop_words = {"a", "an", "the", "and", "or", "for", "in", "on", "at", "to", "of", "with", "by"}
    tokens = set(re.findall(r"\b\w{3,}\b", title.lower()))
    return tokens - stop_words


def _is_similar_to_any(tokens: set[str], seen: list[set[str]], threshold: float) -> bool:
    for seen_tokens in seen:
        if not tokens or not seen_tokens:
            continue
        overlap = len(tokens & seen_tokens) / max(len(tokens), len(seen_tokens))
        if overlap >= threshold:
            return True
    return False


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _extract_keywords(title: str) -> frozenset[str]:
    stop_words = {"a", "an", "the", "and", "or", "for", "in", "on", "at", "to", "of", "with", "by", "is", "are"}
    words = re.findall(r"\b\w{4,}\b", title.lower())
    return frozenset(w for w in words if w not in stop_words)


def _domain_keyword_overlap(
    domain: str,
    keywords: frozenset[str],
    seen: list[tuple[str, frozenset[str]]],
    threshold: int,
) -> bool:
    for seen_domain, seen_kw in seen:
        if seen_domain == domain and seen_domain:
            overlap = len(keywords & seen_kw)
            if overlap >= threshold:
                return True
    return False
