"""Base types for feed sources."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class FeedItem:
    id: str
    title: str
    url: str
    source: str
    published_at: Optional[datetime] = None
    summary: str = ""
    score: int = 0          # HN score or GitHub stars
    tags: list[str] = field(default_factory=list)
    # Set by curation pass
    relevance_score: float = 0.0
    relevance_reason: str = ""


class FeedFetcher(Protocol):
    def fetch(self) -> list[FeedItem]: ...
