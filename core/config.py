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
OLLAMA_QUESTION = "What study topics is this image about?"
CAMERA_OLLAMA_QUESTION = "What are the face expressions of this guy?"
SUMMARY_MODEL = "gemma4:31b-cloud"
SUMMARY_BATCH_SIZE = 10
SUMMARY_OUTPUT_PATH = BASE_DIR / "summaries.json"
STATE_PATH = BASE_DIR / "state.json"
SUMMARY_THINK = "false"
SUMMARY_EVERY_SECONDS = 120
DISCORD_WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
DISCORD_MESSAGE_MAX_CHARS = 1900
SUMMARY_PROMPT = (
   "Extract the key concepts from these responses. Keep it concise, group by concept, and avoid repetition. Focus on the subjects he is studying. Summarize the topics he has studied so far. Don't think too much."
)

SUBPROCESS_TIMEOUT_SECONDS = 30
SUMMARY_TIMEOUT_SECONDS = 600
CAMERA_INDEX = 1
CAMERA_WARMUP_FRAMES = 3
