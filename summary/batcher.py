#!/usr/bin/env python3
"""Summarize batches of screen OCR responses with Ollama."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from core import config
from ollama.client import run_ollama_prompt
from core.runtime import as_text, utc_now


class SummaryRunResult:
    def __init__(
        self,
        *,
        created: int,
        skipped: int,
        output_path: Path,
        summaries: list[dict[str, Any]],
    ) -> None:
        self.created = created
        self.skipped = skipped
        self.output_path = output_path
        self.summaries = summaries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch responses.jsonl entries and summarize key concepts with Ollama."
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
        "--batch-size",
        default=config.SUMMARY_BATCH_SIZE,
        type=int,
        help=f"Responses per Ollama call. Default: {config.SUMMARY_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--model",
        default=config.SUMMARY_MODEL,
        help=f"Ollama model for summaries. Default: {config.SUMMARY_MODEL}.",
    )
    parser.add_argument(
        "--think",
        default=config.SUMMARY_THINK,
        help=(
            "Ollama thinking mode passed as --think=VALUE. "
            f"Default: {config.SUMMARY_THINK}."
        ),
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
        "--full-batches-only",
        action="store_true",
        help="Skip the final partial batch when fewer than batch-size responses remain.",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Do not skip batches already present in the output file.",
    )
    return parser


def read_response_entries(input_path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not input_path.exists():
        return entries

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"skipping invalid JSON on line {line_number}: {exc}", file=sys.stderr)
                continue

            response = str(record.get("response") or "").strip()
            timestamp = str(record.get("timestamp") or "").strip()
            if not response or not timestamp:
                continue
            response_id = str(record.get("response_id") or "").strip()
            if not response_id:
                response_id = hashlib.sha256(
                    json.dumps(
                        {
                            "timestamp": timestamp,
                            "source": record.get("source") or "",
                            "image_hash": record.get("image_hash") or "",
                            "response": response,
                        },
                        sort_keys=True,
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()

            entries.append(
                {
                    "response_id": response_id,
                    "line_number": line_number,
                    "timestamp": timestamp,
                    "response": response,
                }
            )

    return entries


def load_summaries(output_path: Path) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []

    try:
        with output_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        backup_path = output_path.with_suffix(output_path.suffix + ".invalid")
        output_path.rename(backup_path)
        print(f"moved invalid summary JSON to {backup_path}", file=sys.stderr)
        return []

    if not isinstance(data, list):
        raise ValueError(f"{output_path} must contain a JSON array")
    return data


def save_summaries(output_path: Path, summaries: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(summaries, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(output_path)


def batched(entries: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [entries[index : index + batch_size] for index in range(0, len(entries), batch_size)]


def build_summary_prompt(instruction: str, batch: list[dict[str, Any]]) -> str:
    response_block = "\n\n".join(
        f"[{index}] timestamp={entry['timestamp']}\n{entry['response']}"
        for index, entry in enumerate(batch, start=1)
    )
    return (
        f"{instruction}\n\n"
        "Responses:\n"
        f"{response_block}\n\n"
        "Return a compact summary with key concepts and niche concepts."
    )


def batch_keys(input_path: Path, batch: list[dict[str, Any]]) -> set[str]:
    resolved_input_path = str(input_path.resolve())
    return {
        (
            f"id:{resolved_input_path}|{batch[0]['response_id']}|"
            f"{batch[-1]['response_id']}|{len(batch)}"
        ),
        (
            f"legacy:{resolved_input_path}|{batch[0]['line_number']}|"
            f"{batch[-1]['line_number']}|{batch[0]['timestamp']}|"
            f"{batch[-1]['timestamp']}"
        ),
    }


def existing_batch_keys(summaries: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for summary in summaries:
        input_path = summary.get("input_path")
        response_id_start = summary.get("response_id_start")
        response_id_end = summary.get("response_id_end")
        batch_size = summary.get("batch_size")
        if (
            isinstance(input_path, str)
            and isinstance(response_id_start, str)
            and isinstance(response_id_end, str)
            and isinstance(batch_size, int)
        ):
            keys.add(f"id:{input_path}|{response_id_start}|{response_id_end}|{batch_size}")

        line_start = summary.get("line_start")
        line_end = summary.get("line_end")
        timestamp_start = summary.get("timestamp_start")
        timestamp_end = summary.get("timestamp_end")
        if (
            isinstance(input_path, str)
            and isinstance(line_start, int)
            and isinstance(line_end, int)
            and isinstance(timestamp_start, str)
            and isinstance(timestamp_end, str)
        ):
            keys.add(
                f"legacy:{input_path}|{line_start}|{line_end}|"
                f"{timestamp_start}|{timestamp_end}"
            )
    return keys


def summarize_batch(
    *,
    input_path: Path,
    batch: list[dict[str, Any]],
    model: str,
    prompt: str,
    timeout: float,
    think: str,
    batch_number: int,
    source: str = "responses",
) -> dict[str, Any]:
    response = ""
    error = ""
    returncode = None
    status = "ok"
    summary_prompt = build_summary_prompt(prompt, batch)

    try:
        response, stderr, returncode = run_ollama_prompt(
            model=model,
            prompt=summary_prompt,
            timeout=timeout,
            think=think,
        )
        status = "ok" if returncode == 0 else "ollama_error"
        error = "" if returncode == 0 else stderr
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        response = as_text(exc.stdout)
        error = as_text(exc.stderr) or f"timed out after {timeout} seconds"
    except OSError as exc:
        status = "ollama_error"
        error = str(exc)

    return {
        "created_at": utc_now(),
        "source": source,
        "input_path": str(input_path.resolve()),
        "model": model,
        "think": think,
        "batch_number": batch_number,
        "batch_size": len(batch),
        "response_id_start": batch[0]["response_id"],
        "response_id_end": batch[-1]["response_id"],
        "line_start": batch[0]["line_number"],
        "line_end": batch[-1]["line_number"],
        "timestamp_start": batch[0]["timestamp"],
        "timestamp_end": batch[-1]["timestamp"],
        "status": status,
        "returncode": returncode,
        "summary": response,
        "error": error,
    }


def summarize_pending(
    *,
    input_path: Path,
    output_path: Path,
    batch_size: int,
    model: str,
    prompt: str,
    timeout: float,
    think: str,
    full_batches_only: bool = False,
    rerun: bool = False,
    verbose: bool = True,
    source: str = "responses",
    rest_min: float = 0,
    rest_max: float = 0,
) -> SummaryRunResult:
    entries = read_response_entries(input_path)
    if not entries:
        if verbose:
            print(f"no response entries found in {input_path}")
        return SummaryRunResult(created=0, skipped=0, output_path=output_path, summaries=[])

    summaries = load_summaries(output_path)
    seen = set() if rerun else existing_batch_keys(summaries)

    created = 0
    skipped = 0
    created_summaries: list[dict[str, Any]] = []
    for batch_number, batch in enumerate(batched(entries, batch_size), start=1):
        if full_batches_only and len(batch) < batch_size:
            skipped += 1
            continue

        if batch_keys(input_path, batch) & seen:
            skipped += 1
            continue

        if verbose:
            print(
                f"summarizing batch {batch_number}: lines {batch[0]['line_number']}-"
                f"{batch[-1]['line_number']}, timestamps {batch[0]['timestamp']} -> "
                f"{batch[-1]['timestamp']}"
            )
        summary = summarize_batch(
            input_path=input_path,
            batch=batch,
            model=model,
            prompt=prompt,
            timeout=timeout,
            think=think,
            batch_number=batch_number,
            source=source,
        )
        summaries.append(summary)
        created_summaries.append(summary)
        save_summaries(output_path, summaries)
        created += 1
        if rest_max > 0:
            rest_seconds = random.uniform(rest_min, rest_max)
            if verbose:
                print(f"resting {rest_seconds:.1f}s before next summary batch")
            time.sleep(rest_seconds)

    return SummaryRunResult(
        created=created,
        skipped=skipped,
        output_path=output_path,
        summaries=created_summaries,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    result = summarize_pending(
        input_path=args.input,
        output_path=args.output,
        batch_size=args.batch_size,
        model=args.model,
        prompt=args.prompt,
        timeout=args.timeout,
        think=args.think,
        full_batches_only=args.full_batches_only,
        rerun=args.rerun,
    )
    print(
        f"summary complete: created={result.created}, skipped={result.skipped}, "
        f"output={result.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
