#!/usr/bin/env python3
"""Record fixed-length audio chunks for later transcription."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf

import config
from utils import StopRequested, install_signal_handlers, parse_run, should_continue, utc_now


def parse_device(value: str) -> int | str:
    value = value.strip()
    if value.isdigit():
        return int(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record audio chunks to disk and append chunk metadata to a JSONL manifest."
    )
    parser.add_argument(
        "--run",
        default="no-stop",
        type=parse_run,
        help="Number of audio chunks to record, or 'no-stop' for indefinite mode.",
    )
    parser.add_argument(
        "--chunk-seconds",
        default=config.AUDIO_CHUNK_SECONDS,
        type=float,
        help=f"Seconds per audio chunk. Default: {config.AUDIO_CHUNK_SECONDS}.",
    )
    parser.add_argument(
        "--sample-rate",
        default=config.AUDIO_SAMPLE_RATE,
        type=int,
        help=f"Audio sample rate. Default: {config.AUDIO_SAMPLE_RATE}.",
    )
    parser.add_argument(
        "--channels",
        default=config.AUDIO_CHANNELS,
        type=int,
        help=f"Number of channels to record. Default: {config.AUDIO_CHANNELS}.",
    )
    parser.add_argument(
        "--device",
        default=config.AUDIO_DEVICE,
        type=parse_device,
        help="Input device index or name. Use --list-devices to inspect available devices.",
    )
    parser.add_argument(
        "--segments-dir",
        default=config.AUDIO_SEGMENTS_DIR,
        type=Path,
        help=f"Directory for recorded WAV chunks. Default: {config.AUDIO_SEGMENTS_DIR}.",
    )
    parser.add_argument(
        "--manifest",
        default=config.AUDIO_MANIFEST_PATH,
        type=Path,
        help=f"JSONL manifest for recorded chunks. Default: {config.AUDIO_MANIFEST_PATH}.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List audio devices and exit.",
    )
    return parser


def list_devices() -> None:
    print(sd.query_devices())


def chunk_filename(timestamp: str, chunk_number: int) -> str:
    safe_timestamp = timestamp.replace(":", "").replace("-", "")
    return f"audio_{safe_timestamp}_{chunk_number:06d}.wav"


def append_manifest_record(manifest_path: Path, record: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_chunk(
    *,
    chunk_number: int,
    chunk_seconds: float,
    sample_rate: int,
    channels: int,
    device: int | str | None,
    segments_dir: Path,
    manifest_path: Path,
) -> None:
    segments_dir.mkdir(parents=True, exist_ok=True)
    timestamp_start = utc_now()
    frame_count = int(chunk_seconds * sample_rate)
    started_at = time.monotonic()

    audio = sd.rec(
        frame_count,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        device=device,
    )
    sd.wait()

    timestamp_end = utc_now()
    duration_seconds = time.monotonic() - started_at
    path = segments_dir / chunk_filename(timestamp_start, chunk_number)
    sf.write(path, audio, sample_rate)

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    append_manifest_record(
        manifest_path,
        {
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "source": "audio",
            "chunk_number": chunk_number,
            "path": str(path),
            "sha256": digest,
            "duration_seconds": duration_seconds,
            "sample_rate": sample_rate,
            "channels": channels,
            "device": device,
            "status": "recorded",
        },
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return 0
    if args.chunk_seconds <= 0:
        parser.error("--chunk-seconds must be greater than 0")
    if args.sample_rate <= 0:
        parser.error("--sample-rate must be greater than 0")
    if args.channels < 1:
        parser.error("--channels must be at least 1")

    install_signal_handlers()
    completed_chunks = 0
    print(
        f"audio-recorder started: run={args.run}, chunk_seconds={args.chunk_seconds}, "
        f"sample_rate={args.sample_rate}, channels={args.channels}, device={args.device}"
    )

    try:
        while should_continue(args.run, completed_chunks):
            completed_chunks += 1
            print(f"[{completed_chunks}] recording audio chunk")
            record_chunk(
                chunk_number=completed_chunks,
                chunk_seconds=args.chunk_seconds,
                sample_rate=args.sample_rate,
                channels=args.channels,
                device=args.device,
                segments_dir=args.segments_dir,
                manifest_path=args.manifest,
            )
            print(f"[{completed_chunks}] audio chunk stored")
    except StopRequested as exc:
        print(f"audio-recorder stopped: {exc}")
        return 0

    print(f"audio-recorder finished after {completed_chunks} chunk(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
