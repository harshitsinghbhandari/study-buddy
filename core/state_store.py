"""JSON state file helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}

    try:
        with state_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        backup_path = state_path.with_suffix(state_path.suffix + ".invalid")
        state_path.rename(backup_path)
        return {}

    if isinstance(data, dict):
        return data
    return {}


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(state_path)
