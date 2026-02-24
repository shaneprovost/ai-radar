# ai-radar

Personalized AI trend radar CLI — filters 60+ weekly items down to ~10 that genuinely matter to your workflow.

## What it does

- **Profiles your environment** once: detects Claude Code, MCPs, API keys, shell aliases, frameworks
- **Fetches weekly** from GitHub Trending, Hacker News, and AI lab blogs/newsletters
- **Curates with LLM**: scores each item for relevance to your specific stack and workflow
- **Explains *why*** each item matters — and exactly how to adopt it — referencing your actual tools and commands
- **Delivers** to `~/ai-radar/digests/YYYY-MM-DD.md` + optional Slack DM
- **Zero cloud dependencies** — runs entirely on your machine

## Install

```bash
pipx install ai-radar
```

Or from source:

```bash
git clone https://github.com/YOUR_USERNAME/ai-radar
cd ai-radar
pipx install -e .
```

## Usage

```bash
# First-time setup (detects environment, runs interview, installs cron)
ai-radar setup

# Generate digest manually
ai-radar digest

# Force regenerate (bypass 6h guard)
ai-radar digest --force

# Fetch only, skip LLM (useful for testing sources)
ai-radar digest --dry-run

# View your profile
ai-radar show-profile

# Update preferences
ai-radar update-profile

# List past digests
ai-radar list-digests
```

## Requirements

- Python 3.10+
- One of: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`

## Configuration

| Path | Purpose |
|------|---------|
| `~/.config/ai-radar/profile.yaml` | Your profile (role, stack, workflow patterns) |
| `~/.config/ai-radar/run-state.json` | Last run timestamp and stats |
| `~/.config/ai-radar/run-digest.sh` | Cron wrapper script |
| `~/ai-radar/digests/` | Generated digest files |
| `~/ai-radar/logs/` | Cron run logs |

## Supported LLM Providers

| Provider | Default Model |
|----------|--------------|
| Anthropic | claude-sonnet-4-6 |
| OpenAI | gpt-4o |
| Google | gemini-2.0-flash |

Provider is auto-detected from available API keys during `ai-radar setup`.

## Sources

- **GitHub Trending** — top repos this week
- **Hacker News** — AI/ML stories with score ≥ 50, past 7 days
- **RSS feeds** — Anthropic, OpenAI, DeepMind, Mistral blogs + TLDR AI, The Batch, Import AI, AI Breakfast

## Digest Format

```
# AI Radar — February 24, 2026

> Personalized for: Engineering Manager (TypeScript/React, Claude Code + 9 MCPs)
> Sources: GitHub Trending, Hacker News, 4 RSS feeds | Reviewed: 67 | Surfaced: 9

## Must Look At
### 1. [Item that directly addresses one of your workflow patterns]
...

## Worth Knowing
...

## FYI
...
```

## macOS Cron Note

If weekly runs don't fire, grant cron Full Disk Access:
**System Settings → Privacy & Security → Full Disk Access → cron**
