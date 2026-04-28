#!/usr/bin/env python3
"""Capture the configured crop box to a preview image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import ImageGrab

import config


def parse_crop_box(value: str) -> tuple[int, int, int, int]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop box must be left,top,right,bottom")

    try:
        left, top, right, bottom = (int(part.strip()) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop box values must be integers") from exc

    if right <= left or bottom <= top:
        raise argparse.ArgumentTypeError("crop box must have right > left and bottom > top")

    return left, top, right, bottom


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Save a preview image using the configured absolute crop box."
    )
    parser.add_argument(
        "--crop-box",
        default=config.CROP_BOX,
        type=parse_crop_box,
        help="Absolute crop box as left,top,right,bottom. Defaults to config.CROP_BOX.",
    )
    parser.add_argument(
        "--output",
        default=config.BASE_DIR / "crop_preview.png",
        type=Path,
        help="Where to save the crop preview.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    screenshot = ImageGrab.grab()
    crop = screenshot.crop(args.crop_box)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    crop.save(args.output)

    print(f"screenshot_size={screenshot.size}")
    print(f"crop_box={args.crop_box}")
    print(f"crop_size={crop.size}")
    print(f"saved={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
