"""Shared helpers for screenshot and camera OCR loops."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import config

RunMode = int | Literal["no-stop"]


class StopRequested(Exception):
    """Raised when the process receives a stop signal."""


def parse_run(value: str) -> RunMode:
    if value == "no-stop":
        return value
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--run must be an integer or 'no-stop'") from exc
    if count < 1:
        raise argparse.ArgumentTypeError("--run must be at least 1")
    return count


def install_signal_handlers() -> None:
    def handle_stop(signum: int, _frame: object) -> None:
        raise StopRequested(f"received signal {signum}")

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def filename_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def build_ollama_prompt(question: str) -> str:
    return f"{config.OLLAMA_IMAGE_ARGUMENT} \n{question}"


def run_ollama_prompt(
    *,
    model: str,
    prompt: str,
    timeout: float,
    think: str | None = None,
) -> tuple[str, str, int | None]:
    command = [
        config.OLLAMA_COMMAND,
        "run",
    ]
    if think is not None:
        command.append(f"--think={think}")
    command.extend([model, prompt])

    process = subprocess.run(
        command,
        capture_output=True,
        cwd=config.BASE_DIR,
        text=True,
        timeout=timeout,
        check=False,
    )
    return process.stdout.strip(), process.stderr.strip(), process.returncode


def run_ollama(question: str, timeout: float) -> tuple[str, str, int | None]:
    return run_ollama_prompt(
        model=config.OLLAMA_MODEL,
        prompt=build_ollama_prompt(question),
        timeout=timeout,
    )


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
    record = {
        "timestamp": utc_now(),
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


def remove_temp_image(image_path: Path, keep_image: bool) -> None:
    if keep_image:
        return
    try:
        image_path.unlink()
    except FileNotFoundError:
        pass


def archive_processed_image(image_path: Path, archive_dir: Path) -> Path | None:
    if not image_path.exists():
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"img_{filename_timestamp()}.png"
    shutil.move(str(image_path), archive_path)
    return archive_path


def finish_temp_image(
    image_path: Path,
    *,
    keep_image: bool,
    archive_images: bool,
    archive_dir: Path,
) -> Path | None:
    if archive_images:
        return archive_processed_image(image_path, archive_dir)
    remove_temp_image(image_path, keep_image)
    return None


def should_continue(run_mode: RunMode, completed_checks: int) -> bool:
    return run_mode == "no-stop" or completed_checks < run_mode


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_env_value(name: str, env_path: Path | None = None) -> str:
    if env_path is not None:
        load_env_file(env_path)
    return os.environ.get(name, "").strip()


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


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}

    try:
        with state_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        backup_path = state_path.with_suffix(state_path.suffix + ".invalid")
        state_path.rename(backup_path)
        return {}

    if isinstance(data, dict):
        return data
    return {}


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(state_path)
