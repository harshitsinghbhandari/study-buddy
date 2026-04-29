from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from runtime.protocol import Sink
from runtime.registry import register

_PARAMS_SCHEMA = {
    "webhook_url": {"type": "string", "default": "", "description": "Discord webhook URL"},
    "max_chars": {"type": "integer", "default": 1900},
}


@register("sink.discord")
class DiscordSink(Sink):
    _params_schema = _PARAMS_SCHEMA

    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.webhook_url = params.get("webhook_url") or ""
        self.max_chars = int(params.get("max_chars") or 1900)

    async def run(self, inbox: Any, outbox: None, ctx: Any) -> None:
        while True:
            item = await inbox.get()
            if item is None:
                break
            text = item.get("summary") or item.get("response") or str(item)
            if not self.webhook_url:
                ctx.log(self.name, "no webhook configured; skipped")
                continue
            for chunk in self._split(text):
                self._post(chunk)
                ctx.log(self.name, "posted to discord")

    def _split(self, message: str) -> list[str]:
        if len(message) <= self.max_chars:
            return [message]
        chunks: list[str] = []
        remaining = message
        while remaining:
            chunk = remaining[: self.max_chars]
            split_at = chunk.rfind("\n")
            if split_at > 500:
                chunk = chunk[:split_at]
            chunks.append(chunk)
            remaining = remaining[len(chunk) :].lstrip()
        return chunks

    def _post(self, content: str) -> None:
        payload = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "screen-ocr/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"discord returned HTTP {resp.status}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"discord returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"discord failed: {exc.reason}") from exc
