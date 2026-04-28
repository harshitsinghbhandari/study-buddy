"""Runtime defaults for the screen OCR watcher."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INTERVAL_SECONDS = 30
CROP_BOX = (700, 500, 2700, 1700)

IMAGE_PATH = BASE_DIR / "img.png"
RESPONSES_PATH = BASE_DIR / "responses.jsonl"
CAMERA_RESPONSES_PATH = BASE_DIR / "camera_responses.jsonl"
ARCHIVE_DIR = BASE_DIR / "archive"
CAMERA_ARCHIVE_DIR = BASE_DIR / "camera_archive"

OLLAMA_COMMAND = "ollama"
OLLAMA_MODEL = "deepseek-ocr"
OLLAMA_IMAGE_ARGUMENT = "./img.png"
OLLAMA_QUESTION = "What topic is this image about?"
CAMERA_OLLAMA_QUESTION = "What are the face expressions of this guy?"

SUBPROCESS_TIMEOUT_SECONDS = 30
CAMERA_INDEX = 1
CAMERA_WARMUP_FRAMES = 3
