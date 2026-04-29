"""Transcribe a video or audio file with the local OpenAI Whisper CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


WHISPER_OUTPUT_FORMATS = ("txt", "srt", "vtt", "json", "tsv")


def extract_audio_with_ffmpeg(input_path: Path, audio_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "ffmpeg audio extraction failed")


def default_output_path(input_path: Path, output_format: str) -> Path:
    return input_path.with_suffix(f".transcript.{output_format}")


def run_whisper_cli(
    audio_path: Path,
    output_dir: Path,
    *,
    model: str = "turbo",
    output_format: str = "txt",
    language: str | None = None,
    task: str = "transcribe",
    initial_prompt: str | None = None,
) -> Path:
    if shutil.which("whisper") is None:
        raise RuntimeError("missing whisper CLI. Install it with: brew install openai-whisper")

    command = [
        "whisper",
        str(audio_path),
        "--model",
        model,
        "--task",
        task,
        "--output_format",
        output_format,
        "--output_dir",
        str(output_dir),
    ]
    if language:
        command.extend(["--language", language])
    if initial_prompt:
        command.extend(["--initial_prompt", initial_prompt])

    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "whisper transcription failed")

    whisper_output = output_dir / f"{audio_path.stem}.{output_format}"
    if not whisper_output.exists():
        raise RuntimeError(f"whisper did not create expected output: {whisper_output}")
    return whisper_output


def transcribe_media(
    input_path: Path,
    output_path: Path,
    *,
    model: str = "turbo",
    output_format: str = "txt",
    language: str | None = None,
    task: str = "transcribe",
    initial_prompt: str | None = None,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if output_format not in WHISPER_OUTPUT_FORMATS:
        raise ValueError(f"output_format must be one of: {', '.join(WHISPER_OUTPUT_FORMATS)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        audio_path = temp_path / f"{input_path.stem}.mp3"
        whisper_output_dir = temp_path / "whisper"
        whisper_output_dir.mkdir()

        extract_audio_with_ffmpeg(input_path, audio_path)
        whisper_output = run_whisper_cli(
            audio_path,
            whisper_output_dir,
            model=model,
            output_format=output_format,
            language=language,
            task=task,
            initial_prompt=initial_prompt,
        )
        shutil.copyfile(whisper_output, output_path)

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe a video/audio file with local Whisper.")
    parser.add_argument("media", type=Path, help="Video or audio file to transcribe.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path. Default suffix matches --output-format.",
    )
    parser.add_argument(
        "--model",
        default="turbo",
        help="Whisper model. Default: turbo.",
    )
    parser.add_argument("--language", help="Optional language code, e.g. en.")
    parser.add_argument(
        "--task",
        choices=["transcribe", "translate"],
        default="transcribe",
        help="Whisper task. Default: transcribe.",
    )
    parser.add_argument("--initial-prompt", help="Optional Whisper initial prompt/context.")
    parser.add_argument(
        "--output-format",
        default="txt",
        choices=WHISPER_OUTPUT_FORMATS,
        help="Whisper output format. Default: txt.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_path = args.output or default_output_path(args.media, args.output_format)
    transcribe_media(
        args.media,
        output_path,
        model=args.model,
        output_format=args.output_format,
        language=args.language,
        task=args.task,
        initial_prompt=args.initial_prompt,
    )
    print(f"transcript saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
