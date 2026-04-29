from __future__ import annotations

import asyncio
from typing import Any

from core.db import Database
from runtime.context import PipelineContext
from runtime.loader import PipelineDef
from runtime.protocol import Node


class LinearRunner:
    def __init__(self, pipeline_def: PipelineDef, nodes: list[Node], ctx: PipelineContext) -> None:
        self.pipeline_def = pipeline_def
        self.nodes = nodes
        self.ctx = ctx
        self._queues: list[asyncio.Queue[Any]] = []
        self._tasks: list[asyncio.Task[Any]] = []

    async def run(self) -> None:
        for _ in range(len(self.nodes) - 1):
            self._queues.append(asyncio.Queue(maxsize=256))

        self._ensure_run()
        coros = []
        for i, node in enumerate(self.nodes):
            inbox = self._queues[i - 1] if i > 0 else None
            outbox = self._queues[i] if i < len(self.nodes) - 1 else None
            coros.append(self._run_node(node, inbox, outbox))

        self._tasks = [asyncio.create_task(c) for c in coros]
        try:
            await asyncio.gather(*self._tasks)
            self._finish_run("stopped")
        except Exception as exc:
            self._finish_run("failed")
            raise
        finally:
            if self.ctx.db:
                self.ctx.db.close()

    async def _run_node(self, node: Node, inbox: Any, outbox: Any) -> None:
        try:
            await node.run(inbox=inbox, outbox=outbox, ctx=self.ctx)
        except asyncio.CancelledError:
            pass
        finally:
            if outbox is not None:
                await outbox.put(None)

    def stop(self) -> None:
        self.ctx.cancel.set()
        self._finish_run("stopped")
        for t in self._tasks:
            t.cancel()

    def _ensure_run(self) -> None:
        db = self.ctx.db
        if not db:
            return
        name = self.pipeline_def.name
        row = db.get_pipeline_by_name(name)
        if row is None:
            import yaml
            pid = db.create_pipeline(name, yaml.dump({"name": name}))
        else:
            pid = row["id"]
        self.ctx.run_id = db.create_run(pid)

    def _finish_run(self, status: str) -> None:
        if self.ctx.db and self.ctx.run_id:
            self.ctx.db.stop_run(self.ctx.run_id, status)
