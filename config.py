"""Runtime defaults for the screen OCR watcher."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INTERVAL_SECONDS = 10
CROP_BOX = (100, 400, 2800, 1900)

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
SUMMARY_MODEL = "qwen3.5:0.8b"
SUMMARY_BATCH_SIZE = 10
SUMMARY_OUTPUT_PATH = BASE_DIR / "summaries.json"
STATE_PATH = BASE_DIR / "state.json"
SUMMARY_THINK = "false"
SUMMARY_EVERY_SECONDS = 300
DISCORD_WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
DISCORD_MESSAGE_MAX_CHARS = 1900
SUMMARY_PROMPT = (
    "Extract the key concepts from these responses. Keep it concise, grouped by concept, and avoid repeating the same idea."
)

SUBPROCESS_TIMEOUT_SECONDS = 30
SUMMARY_TIMEOUT_SECONDS = 300
CAMERA_INDEX = 1
CAMERA_WARMUP_FRAMES = 3
