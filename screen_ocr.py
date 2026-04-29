#!/usr/bin/env python3
"""Watch a screen crop and OCR it through Ollama when it changes."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

from PIL import ImageGrab

import config
from event_log import append_response
from file_artifacts import finish_temp_image, remove_temp_image
from ollama_client import run_ollama
from runtime import (
    StopRequested,
    as_text,
    install_signal_handlers,
    parse_run,
    should_continue,
)

CropBox = tuple[int, int, int, int]


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
        "--archive-images",
        action="store_true",
        help="Move each processed img.png to archive/img_TIMESTAMP.png after Ollama returns.",
    )
    parser.add_argument(
        "--archive-dir",
        default=config.ARCHIVE_DIR,
        type=Path,
        help=f"Directory for archived processed images. Default: {config.ARCHIVE_DIR}.",
    )
    parser.add_argument(
        "--timeout",
        default=config.SUBPROCESS_TIMEOUT_SECONDS,
        type=float,
        help="Seconds to wait for Ollama before recording a timeout.",
    )
    return parser


def capture_crop(image_path: Path) -> tuple[str, CropBox]:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot = ImageGrab.grab()
    crop_box = config.CROP_BOX
    crop = screenshot.crop(crop_box)
    digest = hashlib.sha256(crop.tobytes()).hexdigest()
    crop.save(image_path)
    return digest, crop_box


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 0:
        parser.error("--interval must be 0 or greater")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.keep_image and args.archive_images:
        parser.error("--keep-image and --archive-images cannot be used together")

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
            image_hash, crop_box = capture_crop(args.image)

            if image_hash == last_hash:
                remove_temp_image(args.image, args.keep_image)
                print(f"[{completed_checks}] unchanged; skipped")
            else:
                last_hash = image_hash
                print(f"[{completed_checks}] changed; running ollama")
                response = ""
                error = ""
                returncode = None
                status = "ok"
                try:
                    response, stderr, returncode = run_ollama(
                        config.OLLAMA_QUESTION,
                        args.timeout,
                    )
                    status = "ok" if returncode == 0 else "ollama_error"
                    error = "" if returncode == 0 or returncode is None else stderr
                except subprocess.TimeoutExpired as exc:
                    status = "timeout"
                    response = as_text(exc.stdout)
                    error = as_text(exc.stderr) or f"timed out after {args.timeout} seconds"
                    print(f"[{completed_checks}] ollama timed out")
                except OSError as exc:
                    status = "ollama_error"
                    error = str(exc)
                    print(f"[{completed_checks}] ollama failed: {exc}")
                finally:
                    archived_path = finish_temp_image(
                        args.image,
                        keep_image=args.keep_image,
                        archive_images=args.archive_images,
                        archive_dir=args.archive_dir,
                    )
                    append_response(
                        args.output,
                        image_hash=image_hash,
                        source="screen",
                        status=status,
                        response=response,
                        error=error,
                        returncode=returncode,
                        archived_image=str(archived_path or ""),
                        metadata={"crop_box": crop_box},
                    )
                    print(f"[{completed_checks}] response stored: status={status}")

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
