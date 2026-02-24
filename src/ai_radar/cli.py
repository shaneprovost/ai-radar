"""ai-radar CLI — main entry point."""
from __future__ import annotations
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config.paths import PROFILE_PATH, DIGEST_DIR
from .profile.detector import detect_environment, detect_ai_tooling, detect_workflow_patterns
from .profile.interviewer import show_detection_summary, run_interview
from .profile.schema import Profile
from .profile.store import load_profile, save_profile, load_run_state, save_run_state
from .cron.installer import install_cron

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="ai-radar")
def cli():
    """ai-radar — Personalized AI trend digest, filtered for your workflow."""
    pass


@cli.command()
@click.option("--skip-cron", is_flag=True, help="Skip cron installation")
@click.option("--reconfigure", is_flag=True, help="Re-run setup even if profile exists")
def setup(skip_cron: bool, reconfigure: bool):
    """Set up ai-radar: detect your environment, run interview, install cron."""

    if PROFILE_PATH.exists() and not reconfigure:
        console.print("[yellow]Profile already exists. Use --reconfigure to redo setup.[/yellow]")
        console.print(f"Profile: {PROFILE_PATH}")
        console.print("Run [bold]ai-radar digest[/bold] to generate your first digest.")
        return

    console.print()
    console.print(Panel(
        "[bold cyan]Welcome to ai-radar[/bold cyan]\n\n"
        "Weekly AI trends, filtered for your specific workflow.\n"
        "Setup takes ~2 minutes.",
        border_style="cyan",
    ))
    console.print()

    # Step 1: Auto-detection
    with console.status("[cyan]Scanning your environment...[/cyan]"):
        detected = detect_environment()
        ai_tooling = detect_ai_tooling()
        workflow_patterns = detect_workflow_patterns()

    # Step 2: Show detection summary
    show_detection_summary(detected, ai_tooling, workflow_patterns)

    # Step 3: Interview
    user_provided, llm_cfg, delivery = run_interview(detected, ai_tooling, workflow_patterns)

    # Build and save profile
    profile = Profile(
        detected=detected,
        ai_tooling=ai_tooling,
        user=user_provided,
        llm=llm_cfg,
        delivery=delivery,
    )
    save_profile(profile)

    console.print()
    console.print(f"[green]✓[/green] Profile saved to {PROFILE_PATH}")

    # Step 4: Install cron
    if not skip_cron:
        console.print()
        if click.confirm("Install weekly cron job?", default=True):
            success = install_cron(schedule=delivery.cron_schedule)
            if success:
                console.print(f"[green]✓[/green] Cron installed: {delivery.cron_schedule}")
                console.print()
                console.print("[dim]Note: If weekly runs don't fire, grant cron Full Disk Access in[/dim]")
                console.print("[dim]System Settings → Privacy & Security → Full Disk Access[/dim]")
            else:
                console.print("[yellow]![/yellow] Cron installation failed. Run manually: [bold]ai-radar digest[/bold]")

    # Step 5: Offer first digest
    console.print()
    if click.confirm("Run your first digest now?", default=True):
        ctx = click.get_current_context()
        ctx.invoke(digest_cmd)


@cli.command(name="digest")
@click.option("--force", is_flag=True, help="Force run even if last run was recent")
@click.option("--test-slack", is_flag=True, help="Test Slack webhook without full digest")
@click.option("--sources", default=None, help="Comma-separated source names (github_trending,hacker_news,rss)")
@click.option("--dry-run", is_flag=True, help="Fetch and dedup only, skip LLM calls")
def digest_cmd(force: bool, test_slack: bool, sources: Optional[str], dry_run: bool):
    """Fetch sources, curate with LLM, and generate personalized digest."""
    profile = load_profile()
    if profile is None:
        console.print("[red]No profile found. Run [bold]ai-radar setup[/bold] first.[/red]")
        sys.exit(1)

    if test_slack:
        _test_slack(profile)
        return

    # Pre-flight: verify API key is present
    _check_api_key(profile)

    # Guard: last run < 6 hours ago
    run_state = load_run_state()
    if not force and run_state.get("last_run"):
        try:
            last = datetime.fromisoformat(run_state["last_run"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            if elapsed < 6 * 3600:
                hours = elapsed / 3600
                console.print(f"[yellow]Last run was {hours:.1f}h ago. Use --force to override.[/yellow]")
                sys.exit(0)
        except Exception:
            pass

    source_list = [s.strip() for s in sources.split(",")] if sources else None

    console.print()
    console.print(Panel("[bold]Generating your AI Radar digest...[/bold]", border_style="cyan"))
    console.print()

    # Fetch sources
    from .sources.registry import fetch_all_sources
    with console.status("[cyan]Fetching sources...[/cyan]"):
        items, errors = fetch_all_sources(source_list)

    if errors:
        for src, err in errors.items():
            console.print(f"[yellow]![/yellow] {src}: {err}")

    console.print(f"[green]✓[/green] Fetched {len(items)} raw items")

    # Deduplicate
    from .pipeline.dedup import deduplicate
    with console.status("[cyan]Deduplicating...[/cyan]"):
        items = deduplicate(items)
    console.print(f"[green]✓[/green] {len(items)} items after deduplication")

    # Pre-filter
    items = _pre_filter(items, profile)
    console.print(f"[green]✓[/green] {len(items)} items after pre-filtering")

    if dry_run:
        console.print("[yellow]Dry run — skipping LLM calls[/yellow]")
        for item in items[:10]:
            console.print(f"  • {item.title} [{item.source}]")
        return

    # LLM Curation pass
    max_items = profile.delivery.max_items_per_digest
    with console.status(f"[cyan]Curating with {profile.llm.model}...[/cyan]"):
        from .pipeline.curation import curate_items
        curated = curate_items(items, profile, max_items=max_items)

    console.print(f"[green]✓[/green] {len(curated)} items passed curation")

    if not curated:
        console.print("[yellow]No items passed curation threshold. Try --force or broaden your interests.[/yellow]")
        sys.exit(0)

    # LLM Suggestion pass
    with console.status("[cyan]Generating personalized suggestions...[/cyan]"):
        from .pipeline.suggestions import generate_suggestions
        suggestions = asyncio.run(generate_suggestions(curated, profile))

    console.print(f"[green]✓[/green] {len(suggestions)} suggestions generated")

    # Render digest
    total_reviewed = len(items)
    source_names = _get_source_names(items)
    from .delivery.markdown import render_digest
    digest_path = render_digest(suggestions, profile, total_reviewed, source_names)

    console.print()
    console.print(f"[green bold]✓ Digest written to:[/green bold] {digest_path}")

    # Slack delivery
    if profile.delivery.slack_webhook_url:
        from .delivery.slack import post_to_slack
        date_str = datetime.now().strftime("%B %-d, %Y")
        ok = post_to_slack(
            profile.delivery.slack_webhook_url,
            str(digest_path),
            len(suggestions),
            date_str,
        )
        if ok:
            console.print("[green]✓[/green] Sent to Slack")
        else:
            console.print("[yellow]![/yellow] Slack delivery failed")

    # Update run state
    save_run_state({
        "last_run": datetime.now(timezone.utc).isoformat(),
        "item_count": len(suggestions),
        "total_reviewed": total_reviewed,
        "digest_path": str(digest_path),
    })

    console.print()
    console.print(f"Open: [bold]open {digest_path}[/bold]")


@cli.command(name="show-profile")
def show_profile_cmd():
    """Display the current profile in a readable format."""
    profile = load_profile()
    if profile is None:
        console.print("[red]No profile found. Run [bold]ai-radar setup[/bold] first.[/red]")
        sys.exit(1)

    console.print()
    console.print(Panel(
        f"[bold]AI Radar Profile[/bold]\n"
        f"Version: {profile.version} | Created: {profile.created_at.strftime('%Y-%m-%d')}",
        border_style="cyan",
    ))

    console.print("\n[bold cyan]Environment[/bold cyan]")
    console.print(f"  OS/Shell: {profile.detected.os} / {profile.detected.shell}")
    if profile.detected.languages:
        console.print(f"  Languages: {', '.join(profile.detected.languages)}")
    if profile.detected.frameworks_detected:
        console.print(f"  Frameworks: {', '.join(profile.detected.frameworks_detected)}")
    if profile.detected.package_managers:
        console.print(f"  Package managers: {', '.join(profile.detected.package_managers)}")

    console.print("\n[bold cyan]AI Tooling[/bold cyan]")
    if profile.ai_tooling.claude_code_detected:
        ver = f" v{profile.ai_tooling.claude_code_version}" if profile.ai_tooling.claude_code_version else ""
        console.print(f"  Claude Code{ver}: detected")
    if profile.ai_tooling.mcp_servers:
        console.print(f"  MCPs ({len(profile.ai_tooling.mcp_servers)}): {', '.join(profile.ai_tooling.mcp_servers)}")
    if profile.ai_tooling.api_keys_present:
        console.print(f"  API keys: {', '.join(profile.ai_tooling.api_keys_present)}")

    console.print("\n[bold cyan]User[/bold cyan]")
    console.print(f"  Role: {profile.user.role}")
    console.print(f"  Focus: {profile.user.primary_focus}")
    console.print(f"  Adoption style: {profile.user.adoption_style}")
    if profile.user.interests:
        console.print(f"  Interests: {', '.join(profile.user.interests[:5])}")
    if profile.user.ignore_topics:
        console.print(f"  Ignoring: {', '.join(profile.user.ignore_topics)}")
    if profile.user.workflow_patterns:
        console.print(f"\n  Workflow patterns ({len(profile.user.workflow_patterns)}):")
        for wp in profile.user.workflow_patterns:
            console.print(f"    • {wp.description} [{wp.pain_level}]")
    if profile.user.biggest_time_sink:
        console.print(f"\n  Biggest time sink: {profile.user.biggest_time_sink}")

    console.print("\n[bold cyan]LLM Config[/bold cyan]")
    console.print(f"  Provider: {profile.llm.provider}")
    console.print(f"  Model: {profile.llm.model}")

    console.print("\n[bold cyan]Delivery[/bold cyan]")
    console.print(f"  Cron: {profile.delivery.cron_schedule}")
    console.print(f"  Digest dir: {profile.delivery.digest_dir}")
    console.print(f"  Max items: {profile.delivery.max_items_per_digest}")
    if profile.delivery.slack_webhook_url:
        console.print("  Slack: configured")
    console.print()


@cli.command(name="update-profile")
def update_profile_cmd():
    """Re-run the interview to update your profile (preserves detection results)."""
    profile = load_profile()
    if profile is None:
        console.print("[red]No profile found. Run [bold]ai-radar setup[/bold] first.[/red]")
        sys.exit(1)

    console.print()
    console.print(Panel(
        "[bold]Update ai-radar Profile[/bold]\n\n"
        "Re-run the interview to update your preferences.\n"
        "Detection results are preserved.",
        border_style="cyan",
    ))
    console.print()

    with console.status("[cyan]Re-scanning environment...[/cyan]"):
        detected_workflows = detect_workflow_patterns()

    user_provided, llm_cfg, delivery = run_interview(
        profile.detected,
        profile.ai_tooling,
        detected_workflows,
    )

    profile.user = user_provided
    profile.llm = llm_cfg
    profile.delivery = delivery
    save_profile(profile)

    console.print(f"\n[green]✓[/green] Profile updated: {PROFILE_PATH}")


@cli.command(name="list-digests")
def list_digests_cmd():
    """List all generated digests."""
    if not DIGEST_DIR.exists():
        console.print("[yellow]No digests yet. Run [bold]ai-radar digest[/bold] first.[/yellow]")
        return

    digests = sorted(DIGEST_DIR.glob("*.md"), reverse=True)
    if not digests:
        console.print("[yellow]No digests found.[/yellow]")
        return

    console.print(f"\n[bold]Digests in {DIGEST_DIR}[/bold]\n")
    for d in digests:
        size = d.stat().st_size
        console.print(f"  {d.name}  ({size:,} bytes)")
    console.print()


def _pre_filter(items: list, profile: Profile) -> list:
    """Remove items older than lookback, filter ignore topics, cap at 80."""
    from datetime import timedelta
    from .config.defaults import DEFAULT_ITEM_CAP

    cutoff = datetime.now(timezone.utc) - timedelta(days=8)
    ignore_lower = [t.lower() for t in profile.user.ignore_topics]

    filtered = []
    for item in items:
        if item.published_at and item.published_at < cutoff:
            continue
        title_lower = item.title.lower()
        summary_lower = item.summary.lower()
        if any(kw in title_lower or kw in summary_lower for kw in ignore_lower):
            continue
        filtered.append(item)

    return filtered[:DEFAULT_ITEM_CAP]


def _get_source_names(items: list) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item.source not in seen:
            seen.add(item.source)
            result.append(item.source)
    return result[:5]


def _check_api_key(profile: Profile) -> None:
    """Verify the API key for the configured provider is present and looks valid."""
    import os
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GEMINI_API_KEY",
    }
    provider = profile.llm.provider
    env_var = key_map.get(provider, f"{provider.upper()}_API_KEY")
    key = os.environ.get(env_var, "")

    if not key:
        console.print(f"\n[red bold]No API key found.[/red bold]")
        console.print(f"Expected env var: [bold]{env_var}[/bold]")
        console.print(f"Add it to your shell and re-run:\n")
        console.print(f"  echo 'export {env_var}=\"your-key-here\"' >> ~/.zshrc")
        console.print(f"  source ~/.zshrc")
        console.print(f"  ai-radar digest --force\n")
        sys.exit(1)

    console.print(f"[green]✓[/green] {env_var} found (length: {len(key)}, prefix: {key[:12]}...)")


def _test_slack(profile: Profile) -> None:
    if not profile.delivery.slack_webhook_url:
        console.print("[red]No Slack webhook URL configured in profile.[/red]")
        return

    from .delivery.slack import post_to_slack
    console.print("[cyan]Testing Slack webhook...[/cyan]")
    ok = post_to_slack(
        profile.delivery.slack_webhook_url,
        "~/ai-radar/digests/test.md",
        5,
        "Test",
    )
    if ok:
        console.print("[green]✓ Slack webhook works![/green]")
    else:
        console.print("[red]✗ Slack webhook failed.[/red]")
