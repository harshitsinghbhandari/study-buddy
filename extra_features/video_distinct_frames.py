"""Extract visually distinct frames from a video."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class ExtractedFrame:
    frame_index: int
    timestamp_seconds: float
    image_path: Path
    max_similarity: float


def frame_signature(frame: np.ndarray, size: int = 64) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)


def frame_similarity(left: np.ndarray, right: np.ndarray, pixel_tolerance: int = 16) -> float:
    if left.shape != right.shape:
        raise ValueError("frame signatures must have the same shape")
    diff = cv2.absdiff(left, right)
    return float(np.mean(diff <= pixel_tolerance))


def extract_distinct_frames(
    video_path: Path,
    output_dir: Path,
    *,
    similarity_threshold: float = 0.80,
    sample_every_seconds: float = 1.0,
    pixel_tolerance: int = 16,
    image_format: str = "jpg",
    prefix: str | None = None,
) -> list[ExtractedFrame]:
    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between 0 and 1")
    if sample_every_seconds <= 0:
        raise ValueError("sample_every_seconds must be greater than 0")
    if not 0 <= pixel_tolerance <= 255:
        raise ValueError("pixel_tolerance must be between 0 and 255")

    image_format = image_format.lower().lstrip(".")
    if image_format not in {"jpg", "jpeg", "png"}:
        raise ValueError("image_format must be jpg, jpeg, or png")
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = prefix or video_path.stem
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"could not open video {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30
        frame_step = max(1, int(round(fps * sample_every_seconds)))
        kept_signatures: list[np.ndarray] = []
        extracted: list[ExtractedFrame] = []
        frame_index = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % frame_step != 0:
                frame_index += 1
                continue

            signature = frame_signature(frame)
            max_similarity = (
                max(
                    frame_similarity(signature, kept_signature, pixel_tolerance)
                    for kept_signature in kept_signatures
                )
                if kept_signatures
                else 0.0
            )
            if max_similarity < similarity_threshold:
                timestamp_seconds = frame_index / fps
                image_path = output_dir / f"{stem}_frame_{len(extracted) + 1:04d}.{image_format}"
                cv2.imwrite(str(image_path), frame)
                kept_signatures.append(signature)
                extracted.append(
                    ExtractedFrame(
                        frame_index=frame_index,
                        timestamp_seconds=timestamp_seconds,
                        image_path=image_path,
                        max_similarity=max_similarity,
                    )
                )

            frame_index += 1

        return extracted
    finally:
        capture.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract visually distinct frames from a video.")
    parser.add_argument("video", type=Path, help="Video file, e.g. an MP4.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("video_frames"),
        help="Directory where distinct frames will be written. Default: video_frames.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.80,
        help="Skip frames at or above this pixel similarity to any kept frame. Default: 0.80.",
    )
    parser.add_argument(
        "--sample-every-seconds",
        type=float,
        default=1.0,
        help="Sample one frame every N seconds. Default: 1.0.",
    )
    parser.add_argument(
        "--pixel-tolerance",
        type=int,
        default=16,
        help="Downscaled grayscale pixel tolerance for a frame match. Default: 16.",
    )
    parser.add_argument(
        "--format",
        default="jpg",
        choices=["jpg", "jpeg", "png"],
        help="Output image format. Default: jpg.",
    )
    parser.add_argument("--prefix", help="Output filename prefix. Default: video filename stem.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    extracted = extract_distinct_frames(
        args.video,
        args.output_dir,
        similarity_threshold=args.similarity_threshold,
        sample_every_seconds=args.sample_every_seconds,
        pixel_tolerance=args.pixel_tolerance,
        image_format=args.format,
        prefix=args.prefix,
    )
    for frame in extracted:
        print(
            f"frame={frame.frame_index} time={frame.timestamp_seconds:.2f}s "
            f"similarity={frame.max_similarity:.3f} path={frame.image_path}"
        )
    print(f"extracted {len(extracted)} distinct frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
