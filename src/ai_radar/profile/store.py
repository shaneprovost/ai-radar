"""Load/save profile with atomic writes."""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .schema import Profile
from ..config.paths import CONFIG_DIR, PROFILE_PATH, RUN_STATE_PATH


def load_profile() -> Optional[Profile]:
    if not PROFILE_PATH.exists():
        return None
    try:
        data = yaml.safe_load(PROFILE_PATH.read_text())
        return Profile.model_validate(data)
    except Exception as e:
        raise RuntimeError(f"Failed to load profile from {PROFILE_PATH}: {e}") from e


def save_profile(profile: Profile) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    profile.updated_at = datetime.now()

    # Serialize via Pydantic → dict → YAML
    data = json.loads(profile.model_dump_json())

    tmp_path = PROFILE_PATH.with_suffix(".tmp")
    tmp_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
    os.replace(tmp_path, PROFILE_PATH)


def load_run_state() -> dict:
    if not RUN_STATE_PATH.exists():
        return {}
    try:
        return json.loads(RUN_STATE_PATH.read_text())
    except Exception:
        return {}


def save_run_state(state: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RUN_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    os.replace(tmp, RUN_STATE_PATH)
