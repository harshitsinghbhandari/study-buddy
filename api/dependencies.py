from __future__ import annotations

from typing import Any

from core.db import Database

db: Database | None = None
_active_runners: dict[int, Any] = {}


def get_db() -> Database:
    if db is None:
        raise RuntimeError("database not initialized")
    return db


def set_db(database: Database) -> None:
    global db
    db = database


def get_active_runners() -> dict[int, Any]:
    return _active_runners
