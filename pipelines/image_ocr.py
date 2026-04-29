#!/usr/bin/env python3
"""Run Ollama OCR over every image in a folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import time
from pathlib import Path
from typing import Any

from core import config
from core.event_log import append_response
from core.runtime import as_text
from ollama.client import run_ollama_prompt

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deepseek-ocr over an image folder and write JSONL responses."
    )
    parser.add_argument("image_folder", type=Path, help="Folder containing page images.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=config.BASE_DIR / "data" / "ocr-output",
        help="Root output directory. Default: data/ocr-output.",
    )
    parser.add_argument(
        "--model",
        default=config.OLLAMA_MODEL,
        help=f"Ollama OCR model. Default: {config.OLLAMA_MODEL}.",
    )
    parser.add_argument(
        "--prompt",
        default=config.OLLAMA_QUESTION,
        help="Question/prompt sent with each image.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=config.SUBPROCESS_TIMEOUT_SECONDS,
        help=f"Seconds to wait for each Ollama call. Default: {config.SUBPROCESS_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Process all images even if their image_path already exists in responses.jsonl.",
    )
    parser.add_argument(
        "--rest-min",
        type=float,
        default=5,
        help="Minimum random rest seconds between OCR calls. Default: 5.",
    )
    parser.add_argument(
        "--rest-max",
        type=float,
        default=7,
        help="Maximum random rest seconds between OCR calls. Default: 7.",
    )
    return parser


def image_files(image_folder: Path) -> list[Path]:
    if not image_folder.exists():
        raise FileNotFoundError(image_folder)
    if not image_folder.is_dir():
        raise NotADirectoryError(image_folder)

    return sorted(
        path
        for path in image_folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def output_path_for(image_folder: Path, output_root: Path) -> Path:
    return output_root / image_folder.name / "responses.jsonl"


def existing_image_paths(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()

    seen: set[str] = set()
    with output_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            image_path = record.get("image_path")
            if isinstance(image_path, str) and image_path:
                seen.add(image_path)
    return seen


def image_hash(image_path: Path) -> str:
    return hashlib.sha256(image_path.read_bytes()).hexdigest()


def build_image_prompt(image_path: Path, question: str) -> str:
    return f"{image_path.resolve()} \n{question}"


def append_ocr_result(
    output_path: Path,
    *,
    image_path: Path,
    image_index: int,
    total_images: int,
    model: str,
    prompt: str,
    status: str,
    response: str = "",
    error: str = "",
    returncode: int | None = None,
) -> None:
    append_response(
        output_path,
        image_hash=image_hash(image_path),
        source="image-folder",
        status=status,
        response=response,
        error=error,
        returncode=returncode,
        metadata={
            "image_path": str(image_path.resolve()),
            "image_name": image_path.name,
            "image_index": image_index,
            "total_images": total_images,
            "model": model,
            "prompt": prompt,
        },
    )


def process_image_folder(
    *,
    image_folder: Path,
    output_root: Path,
    model: str,
    prompt: str,
    timeout: float,
    rerun: bool = False,
    rest_min: float = 5,
    rest_max: float = 7,
) -> tuple[int, int]:
    images = image_files(image_folder)
    output_path = output_path_for(image_folder, output_root)
    seen = set() if rerun else existing_image_paths(output_path)

    processed = 0
    skipped = 0
    total = len(images)
    for index, image_path in enumerate(images, start=1):
        resolved_image_path = str(image_path.resolve())
        if resolved_image_path in seen:
            skipped += 1
            print(f"[{index}/{total}] skipped existing {image_path.name}")
            continue

        print(f"[{index}/{total}] running OCR for {image_path.name}")
        response = ""
        error = ""
        returncode = None
        status = "ok"
        try:
            response, stderr, returncode = run_ollama_prompt(
                model=model,
                prompt=build_image_prompt(image_path, prompt),
                timeout=timeout,
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

        append_ocr_result(
            output_path,
            image_path=image_path,
            image_index=index,
            total_images=total,
            model=model,
            prompt=prompt,
            status=status,
            response=response,
            error=error,
            returncode=returncode,
        )
        processed += 1
        print(f"[{index}/{total}] stored status={status}")
        if index < total:
            rest_seconds = random.uniform(rest_min, rest_max)
            print(f"[{index}/{total}] resting {rest_seconds:.1f}s")
            time.sleep(rest_seconds)

    return processed, skipped


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than 0")
    if args.rest_min < 0 or args.rest_max < 0:
        raise SystemExit("--rest-min and --rest-max must be 0 or greater")
    if args.rest_max < args.rest_min:
        raise SystemExit("--rest-max must be greater than or equal to --rest-min")

    processed, skipped = process_image_folder(
        image_folder=args.image_folder,
        output_root=args.output_root,
        model=args.model,
        prompt=args.prompt,
        timeout=args.timeout,
        rerun=args.rerun,
        rest_min=args.rest_min,
        rest_max=args.rest_max,
    )
    output_path = output_path_for(args.image_folder, args.output_root)
    print(f"image OCR complete: processed={processed}, skipped={skipped}, output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
