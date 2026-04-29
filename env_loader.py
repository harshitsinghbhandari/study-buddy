"""Environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_env_value(name: str, env_path: Path | None = None) -> str:
    if env_path is not None:
        load_env_file(env_path)
    return os.environ.get(name, "").strip()
