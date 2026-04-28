#!/usr/bin/env python3
"""Probe YouTube caption/audio availability with yt-dlp."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether a YouTube URL exposes captions and downloadable audio."
    )
    parser.add_argument("url", help="YouTube video URL.")
    parser.add_argument(
        "--output-dir",
        default=config.YOUTUBE_DOWNLOADS_DIR,
        type=Path,
        help=f"Directory for downloaded test artifacts. Default: {config.YOUTUBE_DOWNLOADS_DIR}.",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Caption language to prefer. Default: en.",
    )
    parser.add_argument(
        "--download-captions",
        action="store_true",
        help="Download manual/auto captions for the selected language if available.",
    )
    parser.add_argument(
        "--download-audio",
        action="store_true",
        help="Download best available audio without extracting/transcoding.",
    )
    return parser


def run_yt_dlp(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "yt_dlp", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def fetch_metadata(url: str) -> dict[str, Any]:
    result = run_yt_dlp(["--dump-single-json", "--skip-download", url])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp metadata fetch failed")
    return json.loads(result.stdout)


def available_languages(entries: dict[str, Any]) -> list[str]:
    return sorted(entries.keys())


def print_probe(metadata: dict[str, Any], lang: str) -> None:
    subtitles = metadata.get("subtitles") or {}
    automatic_captions = metadata.get("automatic_captions") or {}
    formats = metadata.get("formats") or []
    audio_formats = [
        fmt
        for fmt in formats
        if fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") == "none"
    ]

    print(f"title={metadata.get('title')}")
    print(f"id={metadata.get('id')}")
    print(f"duration_seconds={metadata.get('duration')}")
    print(f"manual_caption_languages={available_languages(subtitles)}")
    print(f"auto_caption_languages={available_languages(automatic_captions)}")
    print(f"preferred_lang={lang}")
    print(f"manual_caption_available={lang in subtitles}")
    print(f"auto_caption_available={lang in automatic_captions}")
    print(f"audio_only_formats={len(audio_formats)}")
    if audio_formats:
        best = audio_formats[-1]
        print(
            "sample_audio_format="
            f"format_id={best.get('format_id')} ext={best.get('ext')} "
            f"abr={best.get('abr')} acodec={best.get('acodec')}"
        )


def download_captions(url: str, output_dir: Path, lang: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title).80s-%(id)s.%(ext)s")
    result = run_yt_dlp(
        [
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            lang,
            "--sub-format",
            "vtt/srv3/best",
            "-o",
            output_template,
            url,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "caption download failed")
    print(result.stdout.strip() or f"captions downloaded to {output_dir}")


def download_audio(url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title).80s-%(id)s.%(ext)s")
    result = run_yt_dlp(
        [
            "-f",
            "bestaudio",
            "--no-playlist",
            "-o",
            output_template,
            url,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "audio download failed")
    print(result.stdout.strip() or f"audio downloaded to {output_dir}")


def main() -> int:
    args = build_parser().parse_args()

    metadata = fetch_metadata(args.url)
    print_probe(metadata, args.lang)

    if args.download_captions:
        download_captions(args.url, args.output_dir, args.lang)
    if args.download_audio:
        download_audio(args.url, args.output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
