#!/usr/bin/env python3
"""Summarize image-folder OCR output and post batches to Discord."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from core import config
from core.env_loader import get_env_value
from core.runtime import StopRequested, install_signal_handlers, utc_now
from core.state_store import load_state, save_state
from pipelines.image_ocr import output_path_for
from sinks.discord import post_discord_message
from summary.batcher import (
    batched,
    load_summaries,
    read_response_entries,
    save_summaries,
    summarize_batch,
)
from summary.watcher import split_discord_message

SUMMARY_SOURCE = "image-ocr"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Watch image OCR JSONL output, summarize batches, and post to Discord."
    )
    parser.add_argument(
        "image_folder",
        type=Path,
        help="Original image folder whose OCR output should be summarized.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input OCR responses.jsonl. Default: data/ocr-output/<image-folder>/responses.jsonl.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=config.BASE_DIR / "data" / "ocr-output",
        help="OCR output root. Default: data/ocr-output.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Summary JSON file. Default: alongside OCR responses.jsonl as summaries.json.",
    )
    parser.add_argument(
        "--state",
        default=config.STATE_PATH,
        type=Path,
        help=f"State JSON file. Default: {config.STATE_PATH}.",
    )
    parser.add_argument(
        "--interval",
        default=config.SUMMARY_EVERY_SECONDS,
        type=float,
        help=f"Seconds between checks. Default: {config.SUMMARY_EVERY_SECONDS}.",
    )
    parser.add_argument(
        "--batch-size",
        default=config.SUMMARY_BATCH_SIZE,
        type=int,
        help=f"Responses per summary batch. Default: {config.SUMMARY_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--model",
        default=config.SUMMARY_MODEL,
        help=f"Ollama model for summaries. Default: {config.SUMMARY_MODEL}.",
    )
    parser.add_argument(
        "--think",
        default=config.SUMMARY_THINK,
        help=f"Ollama thinking mode passed as --think=VALUE. Default: {config.SUMMARY_THINK}.",
    )
    parser.add_argument(
        "--prompt",
        default=config.SUMMARY_PROMPT,
        help="Instruction prompt placed before the batched OCR responses.",
    )
    parser.add_argument(
        "--timeout",
        default=config.SUMMARY_TIMEOUT_SECONDS,
        type=float,
        help=f"Seconds to wait for each Ollama call. Default: {config.SUMMARY_TIMEOUT_SECONDS}.",
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
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check once, summarize/post available batches including the final partial batch, then exit.",
    )
    return parser


def default_input_path(image_folder: Path, output_root: Path) -> Path:
    return output_path_for(image_folder, output_root)


def default_summary_output_path(input_path: Path) -> Path:
    return input_path.parent / "summaries.json"


def cursor_state_key(input_path: Path) -> str:
    return f"image_ocr_summary_cursor:{input_path.resolve()}"


def entries_after_cursor(
    entries: list[dict[str, Any]],
    cursor_response_id: str | None,
) -> list[dict[str, Any]]:
    if not cursor_response_id:
        return entries

    for index, entry in enumerate(entries):
        if entry["response_id"] == cursor_response_id:
            return entries[index + 1 :]
    return entries


def image_summary_to_discord_message(summary: dict[str, Any], image_folder: Path) -> str:
    text = str(summary.get("summary") or "").strip()
    if not text:
        text = str(summary.get("error") or "summary produced no text").strip()

    header = (
        "**Image OCR summary**\n"
        f"folder: {image_folder.name}\n"
        f"responses: lines {summary.get('line_start')} - {summary.get('line_end')}\n"
        f"time: {summary.get('timestamp_start')} -> {summary.get('timestamp_end')}\n"
        f"status: {summary.get('status')}"
    )
    return f"{header}\n\n{text}"


def summarize_and_post_available(
    *,
    image_folder: Path,
    input_path: Path,
    summary_output_path: Path,
    state_path: Path,
    webhook_url: str,
    batch_size: int,
    model: str,
    prompt: str,
    timeout: float,
    think: str,
) -> None:
    entries = read_response_entries(input_path)
    state = load_state(state_path)
    state["last_image_ocr_summary_watch_at"] = utc_now()

    pending_entries = entries_after_cursor(entries, state.get(cursor_state_key(input_path)))
    if not pending_entries:
        save_state(state_path, state)
        print("image OCR summary watcher: no new OCR responses")
        return

    if not webhook_url:
        save_state(state_path, state)
        print(
            "image OCR summary watcher: Discord webhook is not configured; "
            f"pending={len(pending_entries)}"
        )
        return

    summaries = load_summaries(summary_output_path)
    created = 0
    posted = 0
    for batch in batched(pending_entries, batch_size):
        summary = summarize_batch(
            input_path=input_path,
            batch=batch,
            model=model,
            prompt=prompt,
            timeout=timeout,
            think=think,
            batch_number=len(summaries) + 1,
            source=SUMMARY_SOURCE,
        )
        summaries.append(summary)
        save_summaries(summary_output_path, summaries)
        created += 1

        for message in split_discord_message(
            image_summary_to_discord_message(summary, image_folder)
        ):
            post_discord_message(webhook_url, message)
        posted += 1

        state[cursor_state_key(input_path)] = batch[-1]["response_id"]
        state["last_image_ocr_summary_post_at"] = utc_now()
        save_state(state_path, state)

    print(
        f"image OCR summary watcher: created={created}, posted={posted}, "
        f"consumed={len(pending_entries)}"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than 0")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    input_path = args.input or default_input_path(args.image_folder, args.output_root)
    summary_output_path = args.summary_output or default_summary_output_path(input_path)
    webhook_url = get_env_value(args.discord_webhook_env, args.env_file)
    install_signal_handlers()

    print(
        f"image OCR summary watcher started: input={input_path}, "
        f"batch_size={args.batch_size}, interval={args.interval}s, "
        f"summary_output={summary_output_path}"
    )

    try:
        while True:
            try:
                summarize_and_post_available(
                    image_folder=args.image_folder,
                    input_path=input_path,
                    summary_output_path=summary_output_path,
                    state_path=args.state,
                    webhook_url=webhook_url,
                    batch_size=args.batch_size,
                    model=args.model,
                    prompt=args.prompt,
                    timeout=args.timeout,
                    think=args.think,
                )
            except Exception as exc:
                print(f"image OCR summary watcher failed: {exc}")

            if args.once:
                break
            time.sleep(args.interval)
    except StopRequested as exc:
        print(f"image OCR summary watcher stopped: {exc}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
