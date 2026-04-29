"""Camera capture: grab one frame and hash it."""

from __future__ import annotations

import hashlib
from pathlib import Path

import cv2


def capture_camera_frame(
    image_path: Path,
    *,
    camera_index: int,
    warmup_frames: int,
) -> tuple[str, tuple[int, int]]:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    camera = cv2.VideoCapture(camera_index)
    try:
        if not camera.isOpened():
            raise RuntimeError(f"could not open camera index {camera_index}")

        frame = None
        frames_to_read = max(1, warmup_frames + 1)
        for _ in range(frames_to_read):
            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError(f"could not read from camera index {camera_index}")

        written = cv2.imwrite(str(image_path), frame)
        if not written:
            raise RuntimeError(f"could not write camera image to {image_path}")

        digest = hashlib.sha256(frame.tobytes()).hexdigest()
        height, width = frame.shape[:2]
        return digest, (width, height)
    finally:
        camera.release()
