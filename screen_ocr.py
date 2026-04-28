#!/usr/bin/env python3
"""Watch a screen crop and OCR it through Ollama when it changes."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import ImageGrab

import config
from summarize_responses import load_summaries, summarize_pending
from utils import (
    StopRequested,
    append_response,
    as_text,
    finish_temp_image,
    get_env_value,
    install_signal_handlers,
    load_state,
    post_discord_message,
    parse_run,
    remove_temp_image,
    run_ollama,
    save_state,
    should_continue,
    utc_now,
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
    parser.add_argument(
        "--summary-every",
        default=config.SUMMARY_EVERY_SECONDS,
        type=float,
        help=(
            "In no-stop mode, summarize complete response batches every N seconds. "
            f"Default: {config.SUMMARY_EVERY_SECONDS}."
        ),
    )
    parser.add_argument(
        "--no-periodic-summary",
        action="store_true",
        help="Disable periodic summarization and Discord posting in no-stop mode.",
    )
    parser.add_argument(
        "--env-file",
        default=config.BASE_DIR / ".env",
        type=Path,
        help="Env file containing the Discord webhook URL.",
    )
    parser.add_argument(
        "--discord-webhook-env",
        default=config.DISCORD_WEBHOOK_ENV,
        help=f"Environment variable name for the Discord webhook. Default: {config.DISCORD_WEBHOOK_ENV}.",
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


def summary_to_discord_message(summary: dict[str, Any]) -> str:
    text = str(summary.get("summary") or "").strip()
    if not text:
        text = str(summary.get("error") or "summary produced no text").strip()

    header = (
        "**Screen OCR summary**\n"
        f"responses: lines {summary.get('line_start')} - {summary.get('line_end')}\n"
        f"time: {summary.get('timestamp_start')} -> {summary.get('timestamp_end')}\n"
        f"status: {summary.get('status')}"
    )
    return f"{header}\n\n{text}"


def split_discord_message(message: str) -> list[str]:
    limit = config.DISCORD_MESSAGE_MAX_CHARS
    if len(message) <= limit:
        return [message]

    chunks: list[str] = []
    remaining = message
    while remaining:
        chunk = remaining[:limit]
        split_at = chunk.rfind("\n")
        if split_at > 500:
            chunk = chunk[:split_at]
        chunks.append(chunk)
        remaining = remaining[len(chunk) :].lstrip()
    return chunks


def summary_state_key(summary: dict[str, Any]) -> str:
    return (
        f"{summary.get('input_path')}|{summary.get('line_start')}|"
        f"{summary.get('line_end')}|{summary.get('timestamp_start')}|"
        f"{summary.get('timestamp_end')}"
    )


def run_periodic_summary_and_post(
    *,
    webhook_url: str,
) -> None:
    result = summarize_pending(
        input_path=config.RESPONSES_PATH,
        output_path=config.SUMMARY_OUTPUT_PATH,
        batch_size=config.SUMMARY_BATCH_SIZE,
        model=config.SUMMARY_MODEL,
        prompt=config.SUMMARY_PROMPT,
        timeout=config.SUMMARY_TIMEOUT_SECONDS,
        think=config.SUMMARY_THINK,
        full_batches_only=True,
        rerun=False,
        verbose=False,
    )

    if not webhook_url:
        state = load_state(config.STATE_PATH)
        state["last_periodic_summary_at"] = utc_now()
        save_state(config.STATE_PATH, state)
        print(
            "periodic summary: Discord webhook is not configured; "
            f"created={result.created}, skipped={result.skipped}"
        )
        return

    summaries = load_summaries(config.SUMMARY_OUTPUT_PATH)
    state = load_state(config.STATE_PATH)
    posted_keys = set(state.get("discord_posted_summary_keys") or [])
    pending = [
        summary
        for summary in summaries
        if summary.get("source") == "responses" and summary_state_key(summary) not in posted_keys
    ]
    if not pending:
        state["last_periodic_summary_at"] = utc_now()
        save_state(config.STATE_PATH, state)
        print(f"periodic summary: no summaries to post; skipped={result.skipped}")
        return

    posted = 0
    for summary in pending:
        for message in split_discord_message(summary_to_discord_message(summary)):
            post_discord_message(webhook_url, message)
        posted_keys.add(summary_state_key(summary))
        posted += 1
        state["discord_posted_summary_keys"] = sorted(posted_keys)
        state["last_discord_post_at"] = utc_now()
        save_state(config.STATE_PATH, state)

    state["last_periodic_summary_at"] = utc_now()
    save_state(config.STATE_PATH, state)
    print(
        f"periodic summary: created={result.created}, posted={posted}, "
        f"skipped={result.skipped}"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 0:
        parser.error("--interval must be 0 or greater")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.summary_every <= 0:
        parser.error("--summary-every must be greater than 0")
    if args.keep_image and args.archive_images:
        parser.error("--keep-image and --archive-images cannot be used together")

    install_signal_handlers()

    last_hash: str | None = None
    completed_checks = 0
    periodic_summary_enabled = args.run == "no-stop" and not args.no_periodic_summary
    next_summary_at = time.monotonic() + args.summary_every
    webhook_url = ""
    if periodic_summary_enabled:
        webhook_url = get_env_value(args.discord_webhook_env, args.env_file)

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
                        source="screen",
                        status=status,
                        response=response,
                        error=error,
                        returncode=returncode,
                        archived_image=str(archived_path or ""),
                        metadata={"crop_box": crop_box},
                    )
                    print(f"[{completed_checks}] response stored: status={status}")

            if periodic_summary_enabled and time.monotonic() >= next_summary_at:
                try:
                    run_periodic_summary_and_post(webhook_url=webhook_url)
                except Exception as exc:
                    print(f"periodic summary failed: {exc}")
                finally:
                    next_summary_at = time.monotonic() + args.summary_every

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
