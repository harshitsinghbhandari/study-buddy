from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import cv2

from runtime.protocol import Source
from runtime.registry import register


@register("source.camera")
class CameraSource(Source):
    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.camera_index = int(params.get("camera_index") or 1)
        self.warmup_frames = int(params.get("warmup_frames") or 3)
        self.interval = float(params.get("interval") or 10)
        self.image_path = Path(params.get("image_path") or "img.png")

    async def run(self, inbox: None, outbox: Any, ctx: Any) -> None:
        last_hash: str | None = None
        while not ctx.cancelled:
            ctx.check_cancel()
            try:
                image_hash, frame_size = await asyncio.to_thread(self._capture)
            except RuntimeError as exc:
                ctx.log(self.name, f"capture failed: {exc}")
                await asyncio.sleep(self.interval)
                continue

            if image_hash != last_hash:
                last_hash = image_hash
                await outbox.put({"image_hash": image_hash, "image_path": str(self.image_path), "frame_size": frame_size})
            else:
                ctx.log(self.name, "unchanged; skipped")

            try:
                await asyncio.wait_for(ctx.cancel.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    def _capture(self) -> tuple[str, tuple[int, int]]:
        self.image_path.parent.mkdir(parents=True, exist_ok=True)
        camera = cv2.VideoCapture(self.camera_index)
        try:
            if not camera.isOpened():
                raise RuntimeError(f"could not open camera index {self.camera_index}")
            frame = None
            for _ in range(max(1, self.warmup_frames + 1)):
                ok, frame = camera.read()
                if not ok or frame is None:
                    raise RuntimeError(f"could not read from camera index {self.camera_index}")
            cv2.imwrite(str(self.image_path), frame)
            digest = hashlib.sha256(frame.tobytes()).hexdigest()
            h, w = frame.shape[:2]
            return digest, (w, h)
        finally:
            camera.release()
