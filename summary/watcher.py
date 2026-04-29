#!/usr/bin/env python3
"""Watch screen OCR responses, summarize complete batches, and post to Discord."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from core import config
from core.env_loader import get_env_value
from core.runtime import StopRequested, install_signal_handlers, utc_now
from core.state_store import load_state, save_state
from sinks.discord import post_discord_message
from summary.batcher import load_summaries, summarize_pending


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Watch responses.jsonl and post summary batches to Discord."
    )
    parser.add_argument(
        "--input",
        default=config.RESPONSES_PATH,
        type=Path,
        help=f"Input JSONL response file. Default: {config.RESPONSES_PATH}.",
    )
    parser.add_argument(
        "--output",
        default=config.SUMMARY_OUTPUT_PATH,
        type=Path,
        help=f"Summary JSON file. Default: {config.SUMMARY_OUTPUT_PATH}.",
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
        help=f"Seconds between response-file checks. Default: {config.SUMMARY_EVERY_SECONDS}.",
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
        help="Instruction prompt placed before the batched responses.",
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
        help="Check once, summarize/post any complete batches, then exit.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Also summarize/post the final partial batch instead of waiting for it to fill.",
    )
    return parser


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
    if summary.get("response_id_start") and summary.get("response_id_end"):
        return (
            f"{summary.get('input_path')}|{summary.get('response_id_start')}|"
            f"{summary.get('response_id_end')}|{summary.get('batch_size')}"
        )
    return (
        f"{summary.get('input_path')}|{summary.get('line_start')}|"
        f"{summary.get('line_end')}|{summary.get('timestamp_start')}|"
        f"{summary.get('timestamp_end')}"
    )


def summarize_and_post(
    *,
    input_path: Path,
    output_path: Path,
    state_path: Path,
    webhook_url: str,
    batch_size: int,
    model: str,
    prompt: str,
    timeout: float,
    think: str,
    include_partial: bool,
) -> None:
    result = summarize_pending(
        input_path=input_path,
        output_path=output_path,
        batch_size=batch_size,
        model=model,
        prompt=prompt,
        timeout=timeout,
        think=think,
        full_batches_only=not include_partial,
        rerun=False,
        verbose=False,
    )

    state = load_state(state_path)
    state["last_summary_watch_at"] = utc_now()

    if not webhook_url:
        save_state(state_path, state)
        print(
            "summary watcher: Discord webhook is not configured; "
            f"created={result.created}, skipped={result.skipped}"
        )
        return

    summaries = load_summaries(output_path)
    posted_keys = set(state.get("discord_posted_summary_keys") or [])
    pending = [
        summary
        for summary in summaries
        if summary.get("source") == "responses" and summary_state_key(summary) not in posted_keys
    ]
    if not pending:
        save_state(state_path, state)
        print(f"summary watcher: no summaries to post; skipped={result.skipped}")
        return

    posted = 0
    for summary in pending:
        for message in split_discord_message(summary_to_discord_message(summary)):
            post_discord_message(webhook_url, message)
        posted_keys.add(summary_state_key(summary))
        posted += 1
        state["discord_posted_summary_keys"] = sorted(posted_keys)
        state["last_discord_post_at"] = utc_now()
        save_state(state_path, state)

    print(
        f"summary watcher: created={result.created}, posted={posted}, "
        f"skipped={result.skipped}"
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

    install_signal_handlers()
    webhook_url = get_env_value(args.discord_webhook_env, args.env_file)

    print(
        f"summary watcher started: input={args.input}, batch_size={args.batch_size}, "
        f"interval={args.interval}s, output={args.output}"
    )

    try:
        while True:
            try:
                summarize_and_post(
                    input_path=args.input,
                    output_path=args.output,
                    state_path=args.state,
                    webhook_url=webhook_url,
                    batch_size=args.batch_size,
                    model=args.model,
                    prompt=args.prompt,
                    timeout=args.timeout,
                    think=args.think,
                    include_partial=args.all,
                )
            except Exception as exc:
                print(f"summary watcher failed: {exc}")

            if args.once:
                break
            time.sleep(args.interval)
    except StopRequested as exc:
        print(f"summary watcher stopped: {exc}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
