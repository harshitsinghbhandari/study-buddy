# Current Architecture

Snapshot of the system after the cli/core/ollama/... refactor.

## Module layout

| Package | Role |
|---|---|
| `cli/` | Thin entry-point scripts. Argparse + `main()`. |
| `core/` | Shared infrastructure: config, runtime, event log, state store, file artifacts, env loader. |
| `ollama/` | Ollama subprocess client. |
| `sinks/` | Output destinations (Discord webhook). |
| `capture/` | Input sources (screen grab, camera frame). |
| `summary/` | Batching and watcher logic for summarization. |
| `pipelines/` | Higher-level orchestrators (image-folder OCR, image-folder summary watcher). |
| `extras/` | Standalone tools (PDF→images, video distinct-frame extraction, Whisper). |
| `docs/` | Vision, architecture, refactor notes, idea dump. |

## Data flow

```
Screen ─ ImageGrab.grab + crop ─┐
Camera ─ cv2.VideoCapture ──────┼─► img.png ─► ollama run deepseek-ocr ─► responses.jsonl
Folder ─ image files ───────────┘                                          │
                                                                            ▼
                                            summarize batches (gemma4:31b-cloud)
                                                            │
                                                            ▼
                                                      summaries.json
                                                            │
                                                            ▼
                                          summary watcher ─► Discord webhook
                                                            │
                                                            ▼
                                                       state.json
```

Hashes provide change-detection (skip duplicate frames) and stable
`response_id`s for idempotent batching. State files plus atomic temp-file
writes make watchers crash-safe.

## External dependencies

- Python: `Pillow` (screen grab), `opencv-python` (camera + video frames),
  `PyMuPDF` (PDF render). Stdlib for everything else.
- Services: **Ollama** CLI on `PATH` (`deepseek-ocr` for vision,
  `gemma4:31b-cloud` for summary). **Discord webhook** via `urllib.request`,
  URL from `DISCORD_WEBHOOK_URL` env var.
- Optional: **ffmpeg** + **whisper** CLIs for `extras/whisper.py`.

## Configuration

All defaults live in `core/config.py`. Per-process overrides come from CLI
flags. Discord webhook is the only env-loaded value (`.env` parsed by
`core/env_loader.py`).

## Caveats

- `ollama/` shadows the PyPI `ollama` package. If we ever depend on the Python
  Ollama SDK, rename to `ollama_client/` or move under a top-level
  `screen_ocr/` package.
- No automated tests yet. `cli/test_crop.py` is a manual visual helper.
- Pipelines, capture loops, and summary watchers each have their own argparse
  + run loop. The Vision doc (`VISION.md`) proposes consolidating them under
  a single Node protocol.
