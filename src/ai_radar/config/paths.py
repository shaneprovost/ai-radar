"""All path constants for ai-radar (XDG-compliant)."""
from pathlib import Path
import os

# Config directory: ~/.config/ai-radar/
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ai-radar"

# Profile file
PROFILE_PATH = CONFIG_DIR / "profile.yaml"

# Run state (last run timestamp, item counts)
RUN_STATE_PATH = CONFIG_DIR / "run-state.json"

# Cron wrapper script
CRON_SCRIPT_PATH = CONFIG_DIR / "run-digest.sh"

# Output directories
DIGEST_DIR = Path.home() / "ai-radar" / "digests"
LOG_DIR = Path.home() / "ai-radar" / "logs"

# Claude config directory (for detection)
CLAUDE_CONFIG_DIR = Path.home() / ".claude"
CLAUDE_SETTINGS_PATH = CLAUDE_CONFIG_DIR / "settings.local.json"
