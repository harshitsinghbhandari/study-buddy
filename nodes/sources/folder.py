from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from runtime.protocol import Source
from runtime.registry import register

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_PARAMS_SCHEMA = {
    "folder": {"type": "string", "required": True, "description": "Path to image folder"},
}


@register("source.folder")
class FolderSource(Source):
    _params_schema = _PARAMS_SCHEMA

    def configure(self, params: dict[str, Any]) -> None:
        super().configure(params)
        self.folder = Path(params["folder"])

    async def run(self, inbox: None, outbox: Any, ctx: Any) -> None:
        images = sorted(
            p for p in self.folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        for image_path in images:
            ctx.check_cancel()
            digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
            await outbox.put({"image_hash": digest, "image_path": str(image_path.resolve()), "image_name": image_path.name})
            ctx.log(self.name, f"emitted {image_path.name}")
