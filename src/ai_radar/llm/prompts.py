"""All LLM prompt templates."""
from __future__ import annotations
import json

from ..sources.base import FeedItem
from ..profile.schema import Profile


def build_curation_prompt(items: list[FeedItem], profile: Profile) -> dict:
    """Build the batch curation prompt (Pass 1)."""

    user_ctx = {
        "role": profile.user.role,
        "primary_focus": profile.user.primary_focus,
        "languages": profile.detected.languages,
        "frameworks": profile.detected.frameworks_detected,
        "ai_tools": (
            ["Claude Code"] if profile.ai_tooling.claude_code_detected else []
        ) + profile.ai_tooling.other_ai_tools,
        "mcp_servers": profile.ai_tooling.mcp_servers,
        "interests": profile.user.interests,
        "ignore_topics": profile.user.ignore_topics,
        "adoption_style": profile.user.adoption_style,
    }

    items_json = json.dumps([
        {
            "id": item.id,
            "title": item.title,
            "source": item.source,
            "summary": item.summary[:200],
        }
        for item in items
    ], indent=2)

    system = f"""You are a relevance filter for a developer's weekly AI trend digest.
Score each item 0-10 for relevance to this specific developer. Be strict — most items should score ≤ 4.

Scoring guide:
- 10: Major development directly impacting their stack (must read)
- 8-9: New capability they could use this week
- 6-7: Good to know, relevant to their work
- 4-5: Tangentially related
- 0-3: Not relevant

Developer context:
{json.dumps(user_ctx, indent=2)}

Return ONLY a valid JSON array with no other text:
[{{"id": "...", "score": N, "reason": "<10 words>"}}]"""

    user = f"Score these {len(items)} items:\n\n{items_json}"

    return {"system": system, "user": user}


def build_suggestion_prompt(item: FeedItem, profile: Profile) -> dict:
    """Build the per-item personalized suggestion prompt (Pass 2)."""

    workflow_summary = []
    for wp in profile.user.workflow_patterns:
        steps = " → ".join(wp.commands_or_steps[:5]) if wp.commands_or_steps else wp.description
        workflow_summary.append(
            f"- {wp.description} [{wp.pain_level}]\n  Steps: {steps}"
        )

    ai_tools_summary = []
    if profile.ai_tooling.claude_code_detected:
        ver = f" v{profile.ai_tooling.claude_code_version}" if profile.ai_tooling.claude_code_version else ""
        ai_tools_summary.append(f"Claude Code{ver}")
    if profile.ai_tooling.mcp_servers:
        ai_tools_summary.append(f"MCPs: {', '.join(profile.ai_tooling.mcp_servers[:6])}")
    ai_tools_summary.extend(profile.ai_tooling.other_ai_tools)

    package_managers = profile.detected.package_managers[:3] if profile.detected.package_managers else ["npm"]

    user_context = f"""Developer profile:
- Role: {profile.user.role}
- Focus: {profile.user.primary_focus}
- Stack: {', '.join(profile.detected.frameworks_detected + profile.detected.languages)}
- AI tools: {', '.join(ai_tools_summary) or 'none'}
- Package managers: {', '.join(package_managers)}
- Recently adopted: {', '.join(profile.user.recently_adopted) or 'nothing notable'}
- Adoption style: {profile.user.adoption_style}

Workflow patterns (repetitive tasks):
{chr(10).join(workflow_summary) if workflow_summary else '(none detected)'}

Pain points:
{chr(10).join(f'- {p}' for p in profile.user.pain_points) or '(none listed)'}

Biggest time sink: {profile.user.biggest_time_sink or '(not specified)'}"""

    system = f"""You are writing a personalized tech briefing for a specific developer.
Write as if you know their workflow in detail. Be concrete and specific. No hype. No filler.

FIRST: Check if this item addresses any of their workflow_patterns or pain_points.
If yes — lead with that connection. It's the most compelling reason to care.

{user_context}

Return ONLY valid JSON (no markdown, no explanation outside the JSON):
{{
  "what": "1-2 sentence plain-language explanation of what this is",
  "workflow_match": "which of their patterns/pain points this directly solves, or null",
  "why_it_matters": "Personalized explanation referencing their actual tools by name",
  "before_after": {{"before": "how they do it now", "after": "how this changes it"}} or null,
  "how_to_install": "Exact install command using their package manager",
  "usage_example": "Concrete usage in their actual context — use their tools/repos, never generic placeholders",
  "adoption_effort": "low|medium|high",
  "priority": "must-look-at|worth-knowing|FYI"
}}

Rules:
- before_after is REQUIRED when workflow_match is not null
- usage_example must reference their actual tools — never generic placeholders
- how_to_install should use their package manager ({', '.join(package_managers)})
- priority must be exactly one of: must-look-at, worth-knowing, FYI"""

    item_info = f"""Item to analyze:
Title: {item.title}
Source: {item.source}
URL: {item.url}
Summary: {item.summary or '(no summary available)'}
Relevance note: {item.relevance_reason or '(scored as relevant to their stack)'}"""

    return {"system": system, "user": item_info}
