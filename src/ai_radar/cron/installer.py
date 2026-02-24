"""macOS crontab installer for ai-radar weekly digest."""
from __future__ import annotations
import subprocess
import sys

from ..config.paths import CONFIG_DIR, CRON_SCRIPT_PATH, LOG_DIR


CRON_MARKER = "# ai-radar-cron"

WRAPPER_TEMPLATE = """\
#!/bin/zsh
# ai-radar cron wrapper — sources zshrc for PATH/env vars
# {marker}

# Source user's zshrc to get PATH, conda, nvm, API keys, etc.
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc" 2>/dev/null
fi

# Use the exact Python interpreter recorded at install time
"{python}" -m ai_radar.cli digest >> "{log_dir}/cron.log" 2>&1
"""


def install_cron(schedule: str = "0 8 * * 1") -> bool:
    """Install or update the weekly cron job. Returns True on success."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    _write_wrapper_script(sys.executable)
    return _update_crontab(schedule)


def _write_wrapper_script(python_path: str) -> None:
    script = WRAPPER_TEMPLATE.format(
        marker=CRON_MARKER,
        python=python_path,
        log_dir=str(LOG_DIR),
    )
    CRON_SCRIPT_PATH.write_text(script)
    CRON_SCRIPT_PATH.chmod(0o755)


def _update_crontab(schedule: str) -> bool:
    """Read current crontab, remove old ai-radar entries, add new one."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # "no crontab for user" is not a real error
            if "no crontab" in (result.stderr or "").lower():
                existing = ""
            else:
                print(f"[cron] Warning: crontab -l returned error: {result.stderr}")
                existing = ""
        else:
            existing = result.stdout
    except Exception as e:
        print(f"[cron] Could not read crontab: {e}")
        return False

    # Remove existing ai-radar entries
    lines = [
        line for line in existing.splitlines()
        if CRON_MARKER not in line and "ai-radar" not in line
    ]

    # Add new entry
    cron_entry = (
        f"{schedule} /bin/zsh {CRON_SCRIPT_PATH} >> {LOG_DIR}/cron.log 2>&1 {CRON_MARKER}"
    )
    lines.append(cron_entry)
    lines.append("")  # crontab needs trailing newline

    new_crontab = "\n".join(lines)

    try:
        proc = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"[cron] Could not write crontab: {e}")
        return False


def remove_cron() -> bool:
    """Remove ai-radar cron entry."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            return True
        lines = [
            line for line in result.stdout.splitlines()
            if CRON_MARKER not in line and "ai-radar" not in line
        ]
        new_crontab = "\n".join(lines) + "\n"
        proc = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
        return proc.returncode == 0
    except Exception:
        return False
