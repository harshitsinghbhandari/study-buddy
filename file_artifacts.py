"""Temporary and archived artifact helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from runtime import filename_timestamp


def remove_temp_image(image_path: Path, keep_image: bool) -> None:
    if keep_image:
        return
    try:
        image_path.unlink()
    except FileNotFoundError:
        pass


def archive_processed_image(image_path: Path, archive_dir: Path) -> Path | None:
    if not image_path.exists():
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"img_{filename_timestamp()}.png"
    shutil.move(str(image_path), archive_path)
    return archive_path


def finish_temp_image(
    image_path: Path,
    *,
    keep_image: bool,
    archive_images: bool,
    archive_dir: Path,
) -> Path | None:
    if archive_images:
        return archive_processed_image(image_path, archive_dir)
    remove_temp_image(image_path, keep_image)
    return None
