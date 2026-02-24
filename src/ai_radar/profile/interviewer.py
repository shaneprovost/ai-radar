"""Smart CLI interview to build user profile, adapting to detection results."""
from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from .schema import AITooling, DetectedEnvironment, LLMConfig, DeliveryPreferences, UserProvided, WorkflowPattern
from ..config.defaults import INTEREST_TOPICS, PROVIDER_DEFAULTS, DEFAULT_CRON_SCHEDULE

console = Console()


def show_detection_summary(
    detected: DetectedEnvironment,
    ai_tooling: AITooling,
    workflow_patterns: list[WorkflowPattern],
) -> None:
    """Show a rich panel summarizing what was auto-detected."""
    lines = []

    if detected.os and detected.shell:
        lines.append(f"  [green]✓[/green] {detected.os}, {detected.shell}")

    if ai_tooling.claude_code_detected:
        ver = f" v{ai_tooling.claude_code_version}" if ai_tooling.claude_code_version else ""
        lines.append(f"  [green]✓[/green] Claude Code{ver} detected")

    if ai_tooling.mcp_servers:
        mcp_list = ", ".join(ai_tooling.mcp_servers[:8])
        suffix = "..." if len(ai_tooling.mcp_servers) > 8 else ""
        lines.append(f"  [green]✓[/green] {len(ai_tooling.mcp_servers)} MCPs found: {mcp_list}{suffix}")

    if ai_tooling.api_keys_present:
        key_list = ", ".join(ai_tooling.api_keys_present[:5])
        lines.append(f"  [green]✓[/green] API keys: {key_list}")

    if detected.frameworks_detected:
        stack = "/".join(detected.frameworks_detected[:4])
        lines.append(f"  [green]✓[/green] {stack} stack inferred")

    if detected.package_managers:
        pms = ", ".join(detected.package_managers[:4])
        lines.append(f"  [green]✓[/green] {pms} detected")

    if detected.editors:
        editors = ", ".join(detected.editors[:3])
        lines.append(f"  [green]✓[/green] Editors: {editors}")

    if workflow_patterns:
        lines.append(f"  [green]✓[/green] {len(workflow_patterns)} workflow pattern(s) detected from shell config")

    if not lines:
        lines.append("  [yellow]![/yellow] No environment details detected")

    content = "\n".join(lines)
    console.print(Panel(
        content,
        title="[bold cyan]Scanning your environment...[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))

    console.print()
    console.print("[bold]The more detail you provide below, the more precisely ai-radar can filter trends")
    console.print("and tailor suggestions to your actual workflow. Take 2 minutes — it pays off every week.[/bold]")
    console.print()


def run_interview(
    detected: DetectedEnvironment,
    ai_tooling: AITooling,
    detected_workflows: list[WorkflowPattern],
) -> tuple[UserProvided, LLMConfig, DeliveryPreferences]:
    """Run the smart interview. Returns (UserProvided, LLMConfig, DeliveryPreferences)."""

    user = UserProvided()
    llm_cfg = LLMConfig()
    delivery = DeliveryPreferences()

    # Q1: Role (always)
    user.role = click.prompt(
        click.style("1. What's your primary role?", bold=True),
        default="Software Engineer",
    ).strip()

    # Q2: Primary focus (always)
    user.primary_focus = click.prompt(
        click.style("2. What's your main focus right now?", bold=True),
        default="",
    ).strip()

    # Q3: Mobile dev (if React detected)
    if "React" in detected.frameworks_detected or "React Native" in detected.frameworks_detected:
        doing_mobile = click.confirm(
            click.style("3. We see React in your stack. Also doing mobile / React Native?", bold=True),
            default="React Native" in detected.frameworks_detected,
        )
        if doing_mobile and "React Native" not in detected.frameworks_detected:
            detected.frameworks_detected.append("React Native")

    # Q4: MCPs used daily (if many MCPs)
    daily_mcps: list[str] = []
    if len(ai_tooling.mcp_servers) > 3:
        console.print(click.style("\n4. You have many MCPs. Which do you use daily?", bold=True))
        console.print(f"   Available: {', '.join(ai_tooling.mcp_servers)}")
        mcp_input = click.prompt(
            "   Enter names (comma-separated, or press Enter for all)",
            default="",
        ).strip()
        if mcp_input:
            daily_mcps = [m.strip() for m in mcp_input.split(",") if m.strip()]

    # Q5: Claude Code usage (if detected)
    claude_usage = ""
    if ai_tooling.claude_code_detected:
        claude_usage = click.prompt(
            click.style("\n5. How are you using Claude Code most? (free text)", bold=True),
            default="Code review, writing tests, exploring new codebases",
        ).strip()

    # Q6: LLM provider selection
    api_keys = ai_tooling.api_keys_present
    provider_map: dict[str, str] = {}
    if any("ANTHROPIC" in k for k in api_keys):
        provider_map["anthropic"] = PROVIDER_DEFAULTS["anthropic"]
    if any("OPENAI" in k for k in api_keys):
        provider_map["openai"] = PROVIDER_DEFAULTS["openai"]
    if any(k in api_keys for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY")):
        provider_map["google"] = PROVIDER_DEFAULTS["google"]

    if len(provider_map) > 1:
        console.print(click.style("\n6. Multiple LLM API keys found. Which provider for ai-radar?", bold=True))
        provider_choices = list(provider_map.keys())
        for i, p in enumerate(provider_choices, 1):
            console.print(f"   [{i}] {p} ({provider_map[p]})")
        choice_idx = click.prompt(
            "   Enter number",
            type=click.IntRange(1, len(provider_choices)),
            default=1,
        )
        chosen_provider = provider_choices[choice_idx - 1]
        llm_cfg.provider = chosen_provider
        llm_cfg.model = provider_map[chosen_provider]
    elif len(provider_map) == 1:
        provider = list(provider_map.keys())[0]
        llm_cfg.provider = provider
        llm_cfg.model = provider_map[provider]
    else:
        console.print(click.style("\n6. No recognized LLM API keys found.", bold=True))
        provider = click.prompt(
            "   LLM provider for ai-radar (anthropic/openai/google)",
            default="anthropic",
        ).strip().lower()
        llm_cfg.provider = provider
        llm_cfg.model = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["anthropic"])

    # Q7: AI topics of interest (multi-select)
    console.print(click.style("\n7. AI topics you're most interested in:", bold=True))
    for i, topic in enumerate(INTEREST_TOPICS, 1):
        console.print(f"   [{i:2d}] {topic}")
    console.print()
    topics_input = click.prompt(
        "   Enter numbers (comma-separated) or press Enter for defaults [1,2,3,4,10]",
        default="1,2,3,4,10",
    ).strip()
    try:
        indices = [int(x.strip()) - 1 for x in topics_input.split(",") if x.strip()]
        user.interests = [INTEREST_TOPICS[i] for i in indices if 0 <= i < len(INTEREST_TOPICS)]
    except ValueError:
        user.interests = INTEREST_TOPICS[:5]

    # Q8: Topics to filter out
    ignore_input = click.prompt(
        click.style("\n8. Topics to filter OUT (comma-separated, or Enter to skip)", bold=True),
        default="",
    ).strip()
    if ignore_input:
        user.ignore_topics = [t.strip() for t in ignore_input.split(",") if t.strip()]

    # Q9: Adoption style
    console.print(click.style("\n9. Adoption style:", bold=True))
    console.print("   [1] Early adopter — try things as soon as they ship")
    console.print("   [2] Pragmatic — adopt when there's clear value")
    console.print("   [3] Cautious — wait for maturity and community validation")
    style_choice = click.prompt("   Enter number", type=click.IntRange(1, 3), default=2)
    styles = ["early adopter", "pragmatic", "cautious"]
    user.adoption_style = styles[style_choice - 1]  # type: ignore

    # Q10: Recently adopted tools
    recently_input = click.prompt(
        click.style("\n10. Tools / libraries adopted in the last 3 months (comma-separated)", bold=True),
        default="",
    ).strip()
    if recently_input:
        user.recently_adopted = [t.strip() for t in recently_input.split(",") if t.strip()]

    # Q11: Workflow patterns — CRITICAL
    user.workflow_patterns = _interview_workflow_patterns(detected_workflows)

    # Q12: Biggest time sink
    user.biggest_time_sink = click.prompt(
        click.style("\n12. What's your single biggest time sink in your dev workflow?", bold=True),
        default="",
    ).strip()

    # Q13: Slack webhook
    console.print(click.style("\n13. Slack webhook URL (for weekly DMs — optional):", bold=True))
    slack_url = click.prompt("   Webhook URL or press Enter to skip", default="").strip()
    if slack_url:
        delivery.slack_webhook_url = slack_url

    # Q14: Cron schedule
    console.print(click.style(f"\n14. Cron schedule (default: {DEFAULT_CRON_SCHEDULE} = Monday 8am):", bold=True))
    cron = click.prompt("   Cron expression", default=DEFAULT_CRON_SCHEDULE).strip()
    delivery.cron_schedule = cron

    # Build daily_tools from detection + interview
    daily_tools: list[str] = []
    if daily_mcps:
        daily_tools.extend(daily_mcps)
    elif ai_tooling.mcp_servers:
        daily_tools.extend(ai_tooling.mcp_servers[:5])
    if ai_tooling.claude_code_detected:
        daily_tools.append("Claude Code")
    daily_tools.extend(detected.editors[:2])
    user.daily_tools = daily_tools

    if claude_usage:
        user.pain_points.append(f"Claude Code primary use: {claude_usage}")

    return user, llm_cfg, delivery


def _interview_workflow_patterns(detected: list[WorkflowPattern]) -> list[WorkflowPattern]:
    """Show detected patterns, ask for pain level and additional patterns."""
    console.print(click.style("\n11. Workflow patterns & pain points:", bold=True))

    pain_levels = {
        "1": "minor annoyance",
        "2": "real friction",
        "3": "major time sink",
    }

    final_patterns: list[WorkflowPattern] = []

    if detected:
        console.print("\n   We detected these repetitive workflows from your shell config:")
        console.print()
        for wp in detected:
            steps_preview = " → ".join(wp.commands_or_steps[:3])
            if len(wp.commands_or_steps) > 3:
                steps_preview += f" ... (+{len(wp.commands_or_steps)-3} more)"
            console.print(f"   [cyan][detected][/cyan] {wp.description}")
            console.print(f"   [dim]{steps_preview}[/dim]")
        console.print()
        console.print("   For each, how painful is it? (1=minor / 2=real friction / 3=major time sink)")
        console.print("   Press Enter to include with default (1=minor)")
        console.print()

        for wp in detected:
            pain = click.prompt(
                f"   {wp.description[:50]}",
                default="1",
                show_default=False,
            ).strip()
            wp.pain_level = pain_levels.get(pain, "minor annoyance")
            final_patterns.append(wp)
    else:
        console.print("   (No workflow patterns detected automatically)")

    # Ask for additional patterns
    console.print()
    console.print("   Any other repetitive workflows? (one per line, blank line to finish)")
    console.print("   [dim]e.g. 'manually check 3 AWS accounts for errors every morning'")
    console.print("   e.g. 'copy-paste Linear ticket IDs into every branch name'[/dim]")
    console.print()

    while True:
        line = click.prompt("   →", default="", prompt_suffix=" ").strip()
        if not line:
            break
        pain = click.prompt(
            "     Pain level (1=minor / 2=real friction / 3=major time sink)",
            default="2",
        ).strip()
        final_patterns.append(WorkflowPattern(
            description=line,
            commands_or_steps=[],
            frequency="unknown",
            pain_level=pain_levels.get(pain, "real friction"),
            source="user",
        ))

    return final_patterns
