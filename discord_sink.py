"""Discord webhook sink."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def post_discord_message(webhook_url: str, content: str, timeout: float = 15) -> None:
    payload = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "screen-ocr/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"discord webhook returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"discord webhook returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"discord webhook failed: {exc.reason}") from exc
