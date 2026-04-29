#!/usr/bin/env python3
"""Watch the laptop camera and OCR changed frames through Ollama."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import cv2

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture laptop camera frames, hash them, and send changes to Ollama."
    )
    parser.add_argument(
        "--run",
        default="no-stop",
        type=parse_run,
        help="Number of camera checks to perform, or 'no-stop' for indefinite mode.",
    )
    parser.add_argument(
        "--interval",
        default=config.INTERVAL_SECONDS,
        type=float,
        help=f"Seconds between camera checks. Default: {config.INTERVAL_SECONDS}.",
    )
    parser.add_argument(
        "--camera-index",
        default=config.CAMERA_INDEX,
        type=int,
        help=f"OpenCV camera index. Default: {config.CAMERA_INDEX}.",
    )
    parser.add_argument(
        "--warmup-frames",
        default=config.CAMERA_WARMUP_FRAMES,
        type=int,
        help=f"Frames to discard after opening the camera. Default: {config.CAMERA_WARMUP_FRAMES}.",
    )
    parser.add_argument(
        "--output",
        default=config.CAMERA_RESPONSES_PATH,
        type=Path,
        help=f"JSONL file for Ollama responses. Default: {config.CAMERA_RESPONSES_PATH}.",
    )
    parser.add_argument(
        "--image",
        default=config.IMAGE_PATH,
        type=Path,
        help=f"Temporary image path given to Ollama. Default: {config.IMAGE_PATH}.",
    )
    parser.add_argument(
        "--keep-image",
        action="store_true",
        help="Keep img.png after Ollama returns. Default behavior deletes it.",
    )
    parser.add_argument(
        "--archive-images",
        action="store_true",
        help="Move each processed img.png to camera_archive/img_TIMESTAMP.png after Ollama returns.",
    )
    parser.add_argument(
        "--archive-dir",
        default=config.CAMERA_ARCHIVE_DIR,
        type=Path,
        help=f"Directory for archived processed images. Default: {config.CAMERA_ARCHIVE_DIR}.",
    )
    parser.add_argument(
        "--timeout",
        default=config.SUBPROCESS_TIMEOUT_SECONDS,
        type=float,
        help="Seconds to wait for Ollama before recording a timeout.",
    )
    return parser


def capture_camera_frame(
    image_path: Path,
    *,
    camera_index: int,
    warmup_frames: int,
) -> tuple[str, tuple[int, int]]:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    camera = cv2.VideoCapture(camera_index)
    try:
        if not camera.isOpened():
            raise RuntimeError(f"could not open camera index {camera_index}")

        frame = None
        frames_to_read = max(1, warmup_frames + 1)
        for _ in range(frames_to_read):
            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError(f"could not read from camera index {camera_index}")

        written = cv2.imwrite(str(image_path), frame)
        if not written:
            raise RuntimeError(f"could not write camera image to {image_path}")

        digest = hashlib.sha256(frame.tobytes()).hexdigest()
        height, width = frame.shape[:2]
        return digest, (width, height)
    finally:
        camera.release()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 0:
        parser.error("--interval must be 0 or greater")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.warmup_frames < 0:
        parser.error("--warmup-frames must be 0 or greater")
    if args.keep_image and args.archive_images:
        parser.error("--keep-image and --archive-images cannot be used together")

    install_signal_handlers()

    last_hash: str | None = None
    completed_checks = 0

    print(
        f"camera-ocr started: run={args.run}, interval={args.interval}s, "
        f"camera_index={args.camera_index}, output={args.output}"
    )

    try:
        while should_continue(args.run, completed_checks):
            completed_checks += 1
            try:
                image_hash, frame_size = capture_camera_frame(
                    args.image,
                    camera_index=args.camera_index,
                    warmup_frames=args.warmup_frames,
                )
            except RuntimeError as exc:
                append_response(
                    args.output,
                    image_hash="",
                    source="camera",
                    status="capture_error",
                    error=str(exc),
                    metadata={"camera_index": args.camera_index},
                )
                remove_temp_image(args.image, args.keep_image)
                print(f"[{completed_checks}] camera capture failed: {exc}")
            else:
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
                            config.CAMERA_OLLAMA_QUESTION,
                            args.timeout,
                        )
                        status = "ok" if returncode == 0 else "ollama_error"
                        error = "" if returncode == 0 else stderr
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
                            source="camera",
                            status=status,
                            response=response,
                            error=error,
                            returncode=returncode,
                            archived_image=str(archived_path or ""),
                            metadata={
                                "camera_index": args.camera_index,
                                "frame_size": frame_size,
                            },
                        )
                        print(f"[{completed_checks}] response stored: status={status}")

            if should_continue(args.run, completed_checks):
                time.sleep(args.interval)
    except StopRequested as exc:
        remove_temp_image(args.image, args.keep_image)
        print(f"camera-ocr stopped: {exc}")
        return 0

    print(f"camera-ocr finished after {completed_checks} check(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
