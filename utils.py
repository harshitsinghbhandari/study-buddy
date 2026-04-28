"""Shared helpers for screenshot and camera OCR loops."""

from __future__ import annotations

import argparse
import json
import shutil
import signal
import subprocess
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


def run_ollama(question: str, timeout: float) -> tuple[str, str, int | None]:
    process = subprocess.run(
        [
            config.OLLAMA_COMMAND,
            "run",
            config.OLLAMA_MODEL,
            build_ollama_prompt(question),
        ],
        capture_output=True,
        cwd=config.BASE_DIR,
        text=True,
        timeout=timeout,
        check=False,
    )
    return process.stdout.strip(), process.stderr.strip(), process.returncode


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
