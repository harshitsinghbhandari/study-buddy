#!/usr/bin/env python3
"""Watch a screen crop and OCR it through Ollama when it changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from PIL import ImageGrab

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a screen crop, hash it, and send changed images to Ollama."
    )
    parser.add_argument(
        "--run",
        default="no-stop",
        type=parse_run,
        help="Number of screenshot checks to perform, or 'no-stop' for indefinite mode.",
    )
    parser.add_argument(
        "--interval",
        default=config.INTERVAL_SECONDS,
        type=float,
        help=f"Seconds between screenshot checks. Default: {config.INTERVAL_SECONDS}.",
    )
    parser.add_argument(
        "--output",
        default=config.RESPONSES_PATH,
        type=Path,
        help=f"JSONL file for Ollama responses. Default: {config.RESPONSES_PATH}.",
    )
    parser.add_argument(
        "--image",
        default=config.IMAGE_PATH,
        type=Path,
        help=f"Temporary image path. Default: {config.IMAGE_PATH}.",
    )
    parser.add_argument(
        "--keep-image",
        action="store_true",
        help="Keep img.png after Ollama returns. Default behavior deletes it.",
    )
    parser.add_argument(
        "--timeout",
        default=config.SUBPROCESS_TIMEOUT_SECONDS,
        type=float,
        help="Seconds to wait for Ollama before recording a timeout.",
    )
    return parser


def install_signal_handlers() -> None:
    def handle_stop(signum: int, _frame: object) -> None:
        raise StopRequested(f"received signal {signum}")

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture_crop(image_path: Path) -> str:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot = ImageGrab.grab()
    crop = screenshot.crop(config.CROP_BOX)
    digest = hashlib.sha256(crop.tobytes()).hexdigest()
    crop.save(image_path)
    return digest


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_ollama(timeout: float) -> tuple[str, str, int | None]:
    prompt = f"{config.OLLAMA_IMAGE_ARGUMENT} \n{config.OLLAMA_QUESTION}"
    process = subprocess.run(
        [config.OLLAMA_COMMAND, "run", config.OLLAMA_MODEL, prompt],
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
    status: str,
    response: str = "",
    error: str = "",
    returncode: int | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": utc_now(),
        "image_hash": image_hash,
        "crop_box": config.CROP_BOX,
        "status": status,
        "returncode": returncode,
        "response": response,
        "error": error,
    }
    with output_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def remove_temp_image(image_path: Path, keep_image: bool) -> None:
    if keep_image:
        return
    try:
        image_path.unlink()
    except FileNotFoundError:
        pass


def should_continue(run_mode: RunMode, completed_checks: int) -> bool:
    return run_mode == "no-stop" or completed_checks < run_mode


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 0:
        parser.error("--interval must be 0 or greater")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    install_signal_handlers()

    last_hash: str | None = None
    completed_checks = 0

    print(
        f"screen-ocr started: run={args.run}, interval={args.interval}s, "
        f"crop={config.CROP_BOX}, output={args.output}"
    )

    try:
        while should_continue(args.run, completed_checks):
            completed_checks += 1
            image_hash = capture_crop(args.image)

            if image_hash == last_hash:
                remove_temp_image(args.image, args.keep_image)
                print(f"[{completed_checks}] unchanged; skipped")
            else:
                last_hash = image_hash
                print(f"[{completed_checks}] changed; running ollama")
                try:
                    response, stderr, returncode = run_ollama(args.timeout)
                    status = "ok" if returncode == 0 else "ollama_error"
                    append_response(
                        args.output,
                        image_hash=image_hash,
                        status=status,
                        response=response,
                        error=stderr,
                        returncode=returncode,
                    )
                    print(f"[{completed_checks}] response stored: status={status}")
                except subprocess.TimeoutExpired as exc:
                    append_response(
                        args.output,
                        image_hash=image_hash,
                        status="timeout",
                        response=as_text(exc.stdout),
                        error=as_text(exc.stderr) or f"timed out after {args.timeout} seconds",
                    )
                    print(f"[{completed_checks}] ollama timed out")
                finally:
                    remove_temp_image(args.image, args.keep_image)

            if should_continue(args.run, completed_checks):
                time.sleep(args.interval)
    except StopRequested as exc:
        remove_temp_image(args.image, args.keep_image)
        print(f"screen-ocr stopped: {exc}")
        return 0

    print(f"screen-ocr finished after {completed_checks} check(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
