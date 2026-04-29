from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from core.db import Database

logger = logging.getLogger("pipeline")


class PipelineContext:
    def __init__(
        self,
        *,
        pipeline_name: str,
        db: Database | None = None,
        run_id: int | None = None,
        cancel: asyncio.Event | None = None,
    ) -> None:
        self.pipeline_name = pipeline_name
        self.db = db
        self.run_id = run_id
        self.cancel = cancel or asyncio.Event()

    @property
    def cancelled(self) -> bool:
        return self.cancel.is_set()

    def check_cancel(self) -> None:
        if self.cancelled:
            raise PipelineCancelled(self.pipeline_name)

    def get_state(self, key: str) -> dict[str, Any]:
        if self.db:
            return self.db.get_state(key)
        return {}

    def set_state(self, key: str, value: dict[str, Any]) -> None:
        if self.db:
            self.db.set_state(key, value)

    def get_checkpoint(self, node_id: str) -> dict[str, Any]:
        if self.db and self.run_id:
            return self.db.get_checkpoint(self.run_id, node_id)
        return {}

    def save_checkpoint(self, node_id: str, cursor: dict[str, Any]) -> None:
        if self.db and self.run_id:
            self.db.set_checkpoint(self.run_id, node_id, cursor)

    def log(self, node_name: str, message: str, **fields: Any) -> None:
        record = {"ts": time.time(), "pipeline": self.pipeline_name, "node": node_name, "msg": message, **fields}
        logger.info(json.dumps(record, default=str))
        if self.db and self.run_id:
            self.db.append_event(self.run_id, node_name, "log", {"msg": message, **fields})


class PipelineCancelled(Exception):
    pass
