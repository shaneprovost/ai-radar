# ai-radar

Personalized weekly AI digest — scans 60+ items from GitHub, Hacker News, and AI blogs, surfaces the ~10 that matter to your workflow.

## Prerequisites

- macOS *(Linux/Windows: [see below](#linux--windows))*
- Python 3.12+ — check: `python3 --version` — install from [python.org](https://python.org/downloads)
- Homebrew — check: `brew --version` — install from [brew.sh](https://brew.sh)
- An API key from one of:

  | Provider | Get your key | Environment variable |
  |---|---|---|
  | **Anthropic** (recommended) | [console.anthropic.com](https://console.anthropic.com) → API Keys | `ANTHROPIC_API_KEY` |
  | OpenAI | [platform.openai.com](https://platform.openai.com) → API Keys | `OPENAI_API_KEY` |
  | Google | [aistudio.google.com](https://aistudio.google.com) → Get API key | `GEMINI_API_KEY` |

---

## Install & Setup (~5 minutes)

**1. Save your API key** (replace the variable name and value with yours):

```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc && source ~/.zshrc
```

**2. Install:**

```bash
brew install pipx && pipx ensurepath
```

> Restart Terminal, then:

```bash
pipx install git+https://github.com/shaneprovost/ai-radar
```

**3. First-time setup:**

```bash
ai-radar setup
```

Detects your environment, asks ~10 short questions about your role and interests, and optionally schedules a weekly digest every Monday at 8am.

**4. Generate your first digest:**

```bash
ai-radar digest
```

Takes 1–2 minutes. Digest saved to `~/ai-radar/digests/YYYY-MM-DD.md`.

---

## Usage

After setup, digests run automatically each week. To run manually:

```bash
ai-radar digest
```

| Command | What it does |
|---|---|
| `ai-radar setup` | First-time setup |
| `ai-radar digest` | Generate a digest now |
| `ai-radar digest --force` | Bypass the 6-hour cooldown |
| `ai-radar digest --dry-run` | Fetch sources, skip AI step |
| `ai-radar digest --digest-dir ~/path` | Save to a custom folder |
| `ai-radar show-profile` | View your current profile |
| `ai-radar update-profile` | Update your preferences |
| `ai-radar list-digests` | List past digests |

---

## Troubleshooting

- **`ai-radar: command not found`** — Run `pipx ensurepath`, restart Terminal, try again
- **API key not found** — Run `echo $ANTHROPIC_API_KEY`; if blank, redo step 1
- **Digest looks generic** — Run `ai-radar update-profile` to fix your preferences
- **Weekly runs don't fire** — System Settings → Privacy & Security → Full Disk Access → add `/usr/sbin/cron`

---

## Linux / Windows

**Linux:** Same steps; replace `brew install pipx` with `pip install --user pipx`, and use `~/.bashrc` instead of `~/.zshrc`.

**Windows:** Set your API key in System Settings → Environment Variables. Automatic weekly scheduling is not supported; run `ai-radar digest` manually.

---

## Reference

**Supported providers:**

| Provider | Default model |
|---|---|
| Anthropic | claude-sonnet-4-6 |
| OpenAI | gpt-4o |
| Google | gemini-2.0-flash |

**Sources:** GitHub Trending · Hacker News (score ≥ 50) · Anthropic, OpenAI, DeepMind, Mistral blogs · TLDR AI · The Batch · Import AI · AI Breakfast

**Config paths:**

| Path | Purpose |
|---|---|
| `~/.config/ai-radar/profile.yaml` | Your profile |
| `~/ai-radar/digests/` | Generated digests |
| `~/ai-radar/logs/` | Cron run logs |
