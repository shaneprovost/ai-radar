"""Auto-detects user environment: tools, API keys, workflow patterns."""
from __future__ import annotations
import json
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Optional

from .schema import AITooling, DetectedEnvironment, WorkflowPattern
from ..config.paths import CLAUDE_CONFIG_DIR, CLAUDE_SETTINGS_PATH


def detect_environment() -> DetectedEnvironment:
    env = DetectedEnvironment()

    # OS
    env.os = platform.system()

    # Shell
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        env.shell = Path(shell_path).name

    # Package managers
    pm_candidates = ["bun", "npm", "yarn", "pnpm", "pip", "pip3", "conda", "poetry", "brew", "nvm", "fnm"]
    env.package_managers = [pm for pm in pm_candidates if shutil.which(pm)]

    # Languages
    lang_candidates = {
        "python3": "Python", "python": "Python", "node": "Node.js",
        "go": "Go", "rustc": "Rust", "java": "Java", "ruby": "Ruby",
        "swift": "Swift", "kotlin": "Kotlin",
    }
    env.languages = list({v for k, v in lang_candidates.items() if shutil.which(k)})

    # Editors — check PATH first, then macOS .app bundles
    editor_candidates = {
        "code": "VS Code", "cursor": "Cursor", "vim": "Vim", "nvim": "Neovim", "nano": "nano",
        "idea": "IntelliJ IDEA", "pycharm": "PyCharm", "webstorm": "WebStorm",
        "goland": "GoLand", "clion": "CLion", "rubymine": "RubyMine",
        "phpstorm": "PhpStorm", "rider": "Rider", "datagrip": "DataGrip",
    }
    found_editors = {v for k, v in editor_candidates.items() if shutil.which(k)}
    found_editors.update(_detect_macos_editors())
    env.editors = sorted(found_editors)

    # Frameworks from package.json files
    frameworks, repos = _scan_repos()
    env.frameworks_detected = frameworks
    env.git_repos_sampled = repos

    return env


def detect_ai_tooling() -> AITooling:
    ai = AITooling()

    # Claude Code
    claude_bin = shutil.which("claude")
    if claude_bin:
        ai.claude_code_detected = True
        ai.claude_code_version = _get_claude_version()

    # MCP servers from settings
    ai.mcp_servers = _detect_mcp_servers()

    # API keys (names only, never values)
    ai.api_keys_present = _detect_api_keys()

    # Other AI tools
    other_tools = []
    if shutil.which("cursor"):
        other_tools.append("Cursor")
    # Check if GitHub Copilot extension is installed via VS Code
    vscode_ext_dir = Path.home() / ".vscode" / "extensions"
    if vscode_ext_dir.exists():
        try:
            for ext in vscode_ext_dir.iterdir():
                if "copilot" in ext.name.lower():
                    other_tools.append("GitHub Copilot")
                    break
        except (PermissionError, OSError):
            pass
    ai.other_ai_tools = other_tools

    return ai


def detect_workflow_patterns() -> list[WorkflowPattern]:
    """Parse shell aliases and functions to detect repetitive workflows."""
    patterns = []

    rc_files = [
        Path.home() / ".zshrc",
        Path.home() / ".bashrc",
        Path.home() / ".bash_profile",
        Path.home() / ".profile",
    ]

    for rc_file in rc_files:
        if rc_file.exists():
            patterns.extend(_parse_rc_file(rc_file))

    # Deduplicate by description
    seen = set()
    unique = []
    for p in patterns:
        if p.description not in seen:
            seen.add(p.description)
            unique.append(p)

    return unique


def _detect_macos_editors() -> set[str]:
    """Detect editors installed as macOS .app bundles (e.g. via JetBrains Toolbox)."""
    app_name_map = {
        "IntelliJ IDEA": "IntelliJ IDEA",
        "PyCharm": "PyCharm",
        "WebStorm": "WebStorm",
        "GoLand": "GoLand",
        "CLion": "CLion",
        "RubyMine": "RubyMine",
        "PhpStorm": "PhpStorm",
        "Rider": "Rider",
        "DataGrip": "DataGrip",
        "Android Studio": "Android Studio",
        "Visual Studio Code": "VS Code",
        "Cursor": "Cursor",
        "Zed": "Zed",
    }
    found: set[str] = set()
    app_dirs = [Path("/Applications"), Path.home() / "Applications"]
    for app_dir in app_dirs:
        if not app_dir.is_dir():
            continue
        try:
            for entry in app_dir.iterdir():
                if not entry.suffix == ".app":
                    continue
                name = entry.stem  # e.g. "PyCharm" from "PyCharm.app"
                for pattern, label in app_name_map.items():
                    if pattern.lower() in name.lower():
                        found.add(label)
                        break
        except (PermissionError, OSError):
            pass
    return found


def _get_claude_version() -> Optional[str]:
    import subprocess
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            match = re.search(r"(\d+\.\d+\.\d+)", result.stdout + result.stderr)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _detect_mcp_servers() -> list[str]:
    servers = set()

    # From Claude settings.local.json
    if CLAUDE_SETTINGS_PATH.exists():
        try:
            data = json.loads(CLAUDE_SETTINGS_PATH.read_text())
            mcp = data.get("mcpServers", {})
            if isinstance(mcp, dict):
                servers.update(mcp.keys())
        except Exception:
            pass

    # Also check ~/.claude/settings.json (non-local)
    claude_settings = CLAUDE_CONFIG_DIR / "settings.json"
    if claude_settings.exists():
        try:
            data = json.loads(claude_settings.read_text())
            mcp = data.get("mcpServers", {})
            if isinstance(mcp, dict):
                servers.update(mcp.keys())
        except Exception:
            pass

    # Scan for .mcp.json files in home directory (depth 5)
    home = Path.home()
    try:
        for mcp_file in _find_files(home, ".mcp.json", max_depth=5):
            try:
                data = json.loads(mcp_file.read_text())
                mcp = data.get("mcpServers", {})
                if isinstance(mcp, dict):
                    servers.update(mcp.keys())
            except Exception:
                pass
    except Exception:
        pass

    return sorted(servers)


def _detect_api_keys() -> list[str]:
    """Detect API key names from environment (never values)."""
    key_names = []
    for key in os.environ:
        upper = key.upper()
        if any(kw in upper for kw in ("API_KEY", "API_SECRET", "TOKEN", "SECRET_KEY")):
            if any(svc in upper for svc in (
                "ANTHROPIC", "OPENAI", "GEMINI", "GOOGLE", "MISTRAL",
                "COHERE", "HUGGINGFACE", "REPLICATE", "GROQ", "TOGETHER",
                "PERPLEXITY", "GITHUB", "SLACK", "LINEAR", "NOTION",
                "AWS", "AZURE", "GCP",
            )):
                key_names.append(key)
    return sorted(key_names)


def _scan_repos() -> tuple[list[str], list[str]]:
    """Scan ~/Documents/repos and home dir for package.json to detect frameworks."""
    frameworks = set()
    repos = []

    scan_dirs = [
        Path.home() / "Documents" / "repos",
        Path.home(),
    ]

    checked = 0
    for base in scan_dirs:
        if not base.exists():
            continue
        for pkg_file in _find_files(base, "package.json", max_depth=3):
            if checked > 20:
                break
            checked += 1
            try:
                data = json.loads(pkg_file.read_text())
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))

                framework_map = {
                    "react": "React",
                    "react-native": "React Native",
                    "expo": "Expo",
                    "next": "Next.js",
                    "vue": "Vue",
                    "svelte": "Svelte",
                    "prisma": "Prisma",
                    "express": "Express",
                    "typescript": "TypeScript",
                }
                for dep_key, fw_name in framework_map.items():
                    if dep_key in deps or f"@{dep_key}" in deps:
                        frameworks.add(fw_name)

                repo_name = pkg_file.parent.name
                if repo_name not in repos and repo_name not in ("node_modules",):
                    repos.append(repo_name)
            except Exception:
                pass

    return sorted(frameworks), repos[:10]


def _find_files(base: Path, filename: str, max_depth: int = 5) -> list[Path]:
    """Find files by name up to max_depth, skipping common noise dirs."""
    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", ".tox", "dist", "build", ".cache",
    }
    results = []

    def _recurse(path: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for item in path.iterdir():
                if item.is_dir() and item.name not in skip_dirs:
                    _recurse(item, depth + 1)
                elif item.is_file() and item.name == filename:
                    results.append(item)
        except (PermissionError, OSError):
            pass

    _recurse(base, 0)
    return results


def _parse_rc_file(rc_file: Path) -> list[WorkflowPattern]:
    """Parse shell aliases from rc files to detect multi-step workflows."""
    patterns = []
    try:
        content = rc_file.read_text(errors="ignore")
    except Exception:
        return patterns

    # Parse aliases: alias name='commands' or alias name="commands"
    alias_pattern = re.compile(r"""^alias\s+(\w+)\s*=\s*['"](.+?)['"]""", re.MULTILINE)
    for match in alias_pattern.finditer(content):
        name = match.group(1)
        cmd_str = match.group(2)

        # Only interested in multi-step aliases (contain && or ;)
        steps = [s.strip() for s in re.split(r"&&|;", cmd_str) if s.strip()]
        if len(steps) >= 3:
            patterns.append(WorkflowPattern(
                description=f"{name} — {len(steps)}-step sequence",
                commands_or_steps=steps,
                frequency="unknown",
                pain_level="minor annoyance",
                source="detected",
            ))

    return patterns
