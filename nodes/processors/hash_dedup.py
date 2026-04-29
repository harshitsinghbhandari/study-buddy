from __future__ import annotations

from typing import Any

from runtime.protocol import Processor
from runtime.registry import register


@register("processor.hash_dedup")
class HashDedupProcessor(Processor):
    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.key = params.get("key") or "image_hash"
        self.pass_unchanged = params.get("pass_unchanged") or False

    async def run(self, inbox: Any, outbox: Any, ctx: Any) -> None:
        seen: set[str] = set()
        while True:
            item = await inbox.get()
            if item is None:
                break
            h = item.get(self.key, "")
            if h in seen:
                if self.pass_unchanged:
                    item["_dedup_skipped"] = True
                    await outbox.put(item)
                else:
                    ctx.log(self.name, "dedup skipped")
                continue
            seen.add(h)
            await outbox.put(item)
