"""Runtime defaults for the screen OCR watcher."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INTERVAL_SECONDS = 30
CROP_BOX = (350, 250, 1350, 850)

IMAGE_PATH = BASE_DIR / "img.png"
RESPONSES_PATH = BASE_DIR / "responses.jsonl"

OLLAMA_COMMAND = "ollama"
OLLAMA_MODEL = "deepseek-ocr"
OLLAMA_IMAGE_ARGUMENT = "./img.png"
OLLAMA_QUESTION = "What does this image show?"

SUBPROCESS_TIMEOUT_SECONDS = 300
