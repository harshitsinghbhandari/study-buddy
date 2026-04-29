"""Screen capture: grab a crop and hash it."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import ImageGrab

from core import config

CropBox = tuple[int, int, int, int]


def capture_crop(image_path: Path) -> tuple[str, CropBox]:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot = ImageGrab.grab()
    crop_box = config.CROP_BOX
    crop = screenshot.crop(crop_box)
    digest = hashlib.sha256(crop.tobytes()).hexdigest()
    crop.save(image_path)
    return digest, crop_box
