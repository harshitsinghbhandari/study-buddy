from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    definition_yaml TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id),
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    stopped_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    node_id TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    kind TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS checkpoints (
    run_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    cursor TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (run_id, node_id)
);
"""


class Database:
    def __init__(self, path: str | Path = "screen_ocr.db") -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript(_SCHEMA)
        self._conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def create_pipeline(self, name: str, definition_yaml: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO pipelines (name, definition_yaml) VALUES (?, ?)",
            (name, definition_yaml),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_pipeline(self, pipeline_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)).fetchone()
        return dict(row) if row else None

    def get_pipeline_by_name(self, name: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM pipelines WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def list_pipelines(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM pipelines ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def delete_pipeline(self, pipeline_id: int) -> None:
        self.conn.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
        self.conn.commit()

    def create_run(self, pipeline_id: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (pipeline_id, status) VALUES (?, 'running')",
            (pipeline_id,),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_runs(self, pipeline_id: int | None = None) -> list[dict[str, Any]]:
        if pipeline_id:
            rows = self.conn.execute("SELECT * FROM runs WHERE pipeline_id = ? ORDER BY id DESC", (pipeline_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def stop_run(self, run_id: int, status: str = "stopped") -> None:
        self.conn.execute(
            "UPDATE runs SET status = ?, stopped_at = datetime('now') WHERE id = ?",
            (status, run_id),
        )
        self.conn.commit()

    def append_event(self, run_id: int, node_id: str, kind: str, payload: dict[str, Any] | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO events (run_id, node_id, kind, payload) VALUES (?, ?, ?, ?)",
            (run_id, node_id, kind, json.dumps(payload or {})),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_events(self, run_id: int, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE run_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (run_id, limit, offset),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            results.append(d)
        return results

    def get_state(self, key: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else {}

    def set_state(self, key: str, value: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        self.conn.commit()

    def get_checkpoint(self, run_id: int, node_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT cursor FROM checkpoints WHERE run_id = ? AND node_id = ?",
            (run_id, node_id),
        ).fetchone()
        return json.loads(row["cursor"]) if row else {}

    def set_checkpoint(self, run_id: int, node_id: str, cursor: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoints (run_id, node_id, cursor, updated_at) VALUES (?, ?, ?, datetime('now'))",
            (run_id, node_id, json.dumps(cursor, ensure_ascii=False)),
        )
        self.conn.commit()
