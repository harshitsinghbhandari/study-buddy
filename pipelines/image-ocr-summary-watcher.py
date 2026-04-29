#!/usr/bin/env python3
"""Compatibility wrapper for image_ocr_summary_watcher."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.image_ocr_summary_watcher import main


if __name__ == "__main__":
    raise SystemExit(main())
