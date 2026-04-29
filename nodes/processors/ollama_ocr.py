from __future__ import annotations

import asyncio
from typing import Any

from runtime.protocol import Processor
from runtime.registry import register

_PARAMS_SCHEMA = {
    "model": {"type": "string", "default": "deepseek-ocr"},
    "question": {"type": "string", "default": "What study topics is this image about?"},
    "timeout": {"type": "number", "default": 30},
    "ollama_command": {"type": "string", "default": "ollama"},
}


@register("processor.ollama_ocr")
class OllamaOCRProcessor(Processor):
    _params_schema = _PARAMS_SCHEMA

    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.model = params.get("model") or "deepseek-ocr"
        self.question = params.get("question") or "What study topics is this image about?"
        self.timeout = float(params.get("timeout") or 30)
        self.command = params.get("ollama_command") or "ollama"

    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        while True:
            item = await inbox.get()
            if item is None:
                break
            image_path = item.get("image_path", "")
            prompt = f"{image_path} \n{self.question}"
            cmd = [self.command, "run", self.model, prompt]

            status = "ok"
            response = ""
            error = ""
            returncode = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
                returncode = proc.returncode
                response = stdout.decode("utf-8", errors="replace").strip()
                error = stderr.decode("utf-8", errors="replace").strip()
                status = "ok" if returncode == 0 else "ollama_error"
            except asyncio.TimeoutError:
                status = "timeout"
                error = f"timed out after {self.timeout}s"
                ctx.log(self.name, "ollama timed out")
            except OSError as exc:
                status = "ollama_error"
                error = str(exc)

            item["status"] = status
            item["response"] = response
            item["error"] = error
            item["returncode"] = returncode
            item["source"] = item.get("source", "pipeline")
            ctx.log(self.name, f"ocr status={status}")
            await outbox.put(item)
