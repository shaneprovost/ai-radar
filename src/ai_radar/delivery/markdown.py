"""Renders digest to ~/ai-radar/digests/YYYY-MM-DD.md."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..pipeline.suggestions import Suggestion
from ..profile.schema import Profile
from ..config.paths import DIGEST_DIR


def render_digest(
    suggestions: list[Suggestion],
    profile: Profile,
    total_reviewed: int,
    sources_used: list[str],
    date: Optional[datetime] = None,
) -> Path:
    """Render digest markdown and write to file. Returns the file path."""
    if date is None:
        date = datetime.now()

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    filename = DIGEST_DIR / f"{date.strftime('%Y-%m-%d')}.md"

    content = _build_markdown(suggestions, profile, total_reviewed, sources_used, date)
    filename.write_text(content, encoding="utf-8")
    return filename


def _build_markdown(
    suggestions: list[Suggestion],
    profile: Profile,
    total_reviewed: int,
    sources_used: list[str],
    date: datetime,
) -> str:
    lines: list[str] = []

    # Header
    date_str = date.strftime("%B %-d, %Y")
    lines.append(f"# AI Radar — {date_str}")
    lines.append("")

    # Byline
    stack_parts = []
    if profile.detected.frameworks_detected:
        stack_parts.append("/".join(profile.detected.frameworks_detected[:3]))
    if profile.ai_tooling.claude_code_detected:
        mcp_count = len(profile.ai_tooling.mcp_servers)
        cc = "Claude Code"
        if mcp_count:
            cc += f" + {mcp_count} MCPs"
        stack_parts.append(cc)

    stack_str = ", ".join(stack_parts) if stack_parts else "your stack"
    sources_str = ", ".join(sources_used) if sources_used else "multiple sources"

    lines.append(f"> Personalized for: {profile.user.role or 'you'} ({stack_str})")
    lines.append(f"> Sources: {sources_str} | Reviewed: {total_reviewed} | Surfaced: {len(suggestions)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by priority
    must_look = [s for s in suggestions if s.priority == "must-look-at"]
    worth_knowing = [s for s in suggestions if s.priority == "worth-knowing"]
    fyi = [s for s in suggestions if s.priority == "FYI"]

    counter = 1

    if must_look:
        lines.append("## Must Look At")
        lines.append("")
        for s in must_look:
            lines.extend(_render_suggestion(s, counter))
            counter += 1

    if worth_knowing:
        lines.append("## Worth Knowing")
        lines.append("")
        for s in worth_knowing:
            lines.extend(_render_suggestion(s, counter))
            counter += 1

    if fyi:
        lines.append("## FYI")
        lines.append("")
        for s in fyi:
            lines.extend(_render_suggestion(s, counter))
            counter += 1

    # Footer
    from ai_radar import __version__
    lines.append("---")
    lines.append(f"*ai-radar v{__version__} · Run manually: `ai-radar digest`*")

    return "\n".join(lines)


def _render_suggestion(s: Suggestion, num: int) -> list[str]:
    lines: list[str] = []
    item = s.item

    lines.append(f"### {num}. {item.title}")
    lines.append("")

    # Meta line
    pub_str = ""
    if item.published_at:
        pub_str = f" · {item.published_at.strftime('%b %d')}"
    score_str = f" (⭐ {item.score:,})" if item.score > 0 else ""
    effort_str = f" · **Effort:** {s.adoption_effort.capitalize()}"
    lines.append(f"**Source:** {item.source}{score_str}{pub_str} · [Read →]({item.url}){effort_str}")
    lines.append("")

    if s.what:
        lines.append(f"**What it is:** {s.what}")
        lines.append("")

    if s.workflow_match:
        lines.append(f"**Addresses your workflow:** {s.workflow_match}")
        lines.append("")

    if s.before_after:
        before = s.before_after.get("before", "")
        after = s.before_after.get("after", "")
        lines.append("**Before vs After:**")
        lines.append("```")
        if before:
            lines.append(f"Before: {before}")
        if after:
            lines.append(f"After:  {after}")
        lines.append("```")
        lines.append("")

    if s.how_to_install:
        lines.append("**Install:**")
        lines.append("```")
        lines.append(s.how_to_install)
        lines.append("```")
        lines.append("")

    if s.usage_example:
        lines.append("**Usage in your context:**")
        lines.append("```")
        lines.append(s.usage_example)
        lines.append("```")
        lines.append("")

    if s.why_it_matters:
        lines.append(f"**Why it matters to you:** {s.why_it_matters}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines
