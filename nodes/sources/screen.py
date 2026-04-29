from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from PIL import ImageGrab

from runtime.protocol import Source
from runtime.registry import register

_PARAMS_SCHEMA = {
    "crop_box": {"type": "array", "items": {"type": "integer"}, "default": [100, 400, 2800, 1900], "description": "Crop box [left, top, right, bottom]"},
    "interval": {"type": "number", "default": 10, "description": "Seconds between captures"},
    "image_path": {"type": "string", "default": "img.png"},
    "run": {"type": "integer", "default": 0, "description": "Number of captures (0 = infinite)"},
}


@register("source.screen")
class ScreenSource(Source):
    _params_schema = _PARAMS_SCHEMA

    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.crop_box = tuple(params.get("crop_box") or (100, 400, 2800, 1900))
        self.interval = float(params.get("interval") or 10)
        self.image_path = Path(params.get("image_path") or "img.png")
        self.run_count = int(params.get("run") or 0) or None

    async def run(self, inbox: None, outbox: Any, ctx: Any) -> None:
        last_hash: str | None = None
        checks = 0
        while not ctx.cancelled:
            ctx.check_cancel()
            checks += 1
            self.image_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot = await asyncio.to_thread(ImageGrab.grab)
            crop = await asyncio.to_thread(screenshot.crop, self.crop_box)
            digest = hashlib.sha256(crop.tobytes()).hexdigest()
            await asyncio.to_thread(crop.save, self.image_path)

            if digest != last_hash:
                last_hash = digest
                await outbox.put({
                    "image_hash": digest,
                    "image_path": str(self.image_path),
                    "crop_box": self.crop_box,
                    "source": "screen",
                    "check": checks,
                })
                ctx.log(self.name, f"changed; emitted check={checks}")
            else:
                ctx.log(self.name, f"unchanged; skipped check={checks}")

            if self.run_count and checks >= self.run_count:
                break
            try:
                await asyncio.wait_for(ctx.cancel.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
