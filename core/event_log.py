"""Append-only event log helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.runtime import utc_now


def make_response_id(
    *,
    timestamp: str,
    source: str,
    image_hash: str,
    response: str,
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "timestamp": timestamp,
                "source": source,
                "image_hash": image_hash,
                "response": response,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def append_response(
    output_path: Path,
    *,
    image_hash: str,
    source: str,
    status: str,
    response: str = "",
    error: str = "",
    returncode: int | None = None,
    archived_image: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now()
    response_id = make_response_id(
        timestamp=timestamp,
        source=source,
        image_hash=image_hash,
        response=response,
    )
    record = {
        "response_id": response_id,
        "timestamp": timestamp,
        "source": source,
        "image_hash": image_hash,
        "status": status,
        "returncode": returncode,
        "response": response,
        "error": error,
        "archived_image": archived_image,
    }
    if metadata:
        record.update(metadata)

    with output_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
