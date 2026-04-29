from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.protocol import Sink
from runtime.registry import register

_PARAMS_SCHEMA = {
    "path": {"type": "string", "default": "responses.jsonl", "description": "Output JSONL file path"},
}


@register("sink.jsonl")
class JsonlSink(Sink):
    _params_schema = _PARAMS_SCHEMA

    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.path = Path(params.get("path") or "responses.jsonl")

    async def run(self, inbox: Any, outbox: None, ctx: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            item = await inbox.get()
            if item is None:
                break
            ts = datetime.now(timezone.utc).isoformat()
            if "response_id" not in item:
                raw = json.dumps({
                    "ts": ts,
                    "source": item.get("source", ""),
                    "hash": item.get("image_hash", ""),
                    "resp": item.get("response", ""),
                }, sort_keys=True)
                item["response_id"] = hashlib.sha256(raw.encode()).hexdigest()
            if "timestamp" not in item:
                item["timestamp"] = ts
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            ctx.log(self.name, f"wrote {item.get('response_id', '')[:8]}...")
