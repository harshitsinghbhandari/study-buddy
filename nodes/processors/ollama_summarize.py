from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from runtime.protocol import Processor
from runtime.registry import register


@register("processor.ollama_summarize")
class OllamaSummarizeProcessor(Processor):
    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.model = params.get("model") or "gemma4:31b-cloud"
        self.batch_size = int(params.get("batch_size") or 10)
        self.prompt = params.get("prompt") or "Extract the key concepts from these responses."
        self.timeout = float(params.get("timeout") or 600)
        self.think = params.get("think") or "false"
        self.command = params.get("ollama_command") or "ollama"

    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        batch: list[Any] = []
        while True:
            item = await inbox.get()
            if item is None:
                if batch:
                    summary = await self._summarize(batch, ctx)
                    await outbox.put(summary)
                break
            batch.append(item)
            if len(batch) >= self.batch_size:
                summary = await self._summarize(batch, ctx)
                await outbox.put(summary)
                batch = []

    async def _summarize(self, batch: list[Any], ctx: Any) -> dict[str, Any]:
        response_block = "\n\n".join(
            f"[{i}] {item.get('response', '')}" for i, item in enumerate(batch, 1)
        )
        prompt = f"{self.prompt}\n\nResponses:\n{response_block}\n\nReturn a compact summary."
        cmd = [self.command, "run", f"--think={self.think}", self.model, prompt]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            return {
                "status": "ok" if proc.returncode == 0 else "ollama_error",
                "summary": stdout.decode("utf-8", errors="replace").strip(),
                "error": stderr.decode("utf-8", errors="replace").strip() if proc.returncode else "",
                "batch_size": len(batch),
            }
        except asyncio.TimeoutError:
            return {"status": "timeout", "summary": "", "error": f"timed out after {self.timeout}s", "batch_size": len(batch)}
        except OSError as exc:
            return {"status": "ollama_error", "summary": "", "error": str(exc), "batch_size": len(batch)}
