# Refactor Notes

This document records the move from a flat root layout to module packages.

## Before

~20 Python files in the repo root, mixing CLI entry points, library helpers,
and orchestrators. Difficult to tell what was runnable vs. importable.

## After

| Old path | New path |
|---|---|
| `config.py` | `core/config.py` |
| `runtime.py` | `core/runtime.py` |
| `event_log.py` | `core/event_log.py` |
| `state_store.py` | `core/state_store.py` |
| `file_artifacts.py` | `core/file_artifacts.py` |
| `env_loader.py` | `core/env_loader.py` |
| `ollama_client.py` | `ollama/client.py` |
| `discord_sink.py` | `sinks/discord.py` |
| `screen_ocr.py` | `cli/screen.py` (+ `capture/screen.py` for `capture_crop`) |
| `camera_ocr.py` | `cli/camera.py` (+ `capture/camera.py` for `capture_camera_frame`) |
| `summarize_responses.py` | `summary/batcher.py` (lib) + `cli/summarize.py` (entry) |
| `summary_watcher.py` | `summary/watcher.py` (lib) + `cli/watch.py` (entry) |
| `test_crop.py` | `cli/test_crop.py` |
| `pipelines/image_ollama_ocr.py` | `pipelines/image_ocr.py` |
| `pipelines/image_ocr_summary_watcher.py` | `pipelines/image_ocr_summary.py` |
| `pipelines/image-ollama-ocr.py` | **deleted** (legacy hyphenated wrapper) |
| `pipelines/image-ocr-summary-watcher.py` | **deleted** (legacy hyphenated wrapper) |
| `extra_features/pdf_images.py` | `extras/pdf_images.py` |
| `extra_features/video_distinct_frames.py` | `extras/video_frames.py` |
| `extra_features/openai_video_transcription.py` | `extras/whisper.py` |
| `utils.py` | **deleted** (compat shim no longer needed) |

## Run commands

| Task | Command |
|---|---|
| Watch screen | `python -m cli.screen [--run no-stop\|N] [--interval S]` |
| Watch camera | `python -m cli.camera [--run no-stop\|N]` |
| Summarize responses | `python -m cli.summarize` |
| Run summary watcher | `python -m cli.watch [--all] [--once]` |
| Preview crop | `python -m cli.test_crop [--crop-box L,T,R,B]` |
| Render PDF pages | `python -m extras.pdf_images <file.pdf>` |
| Run image-folder OCR | `python -m pipelines.image_ocr <folder>` |
| Watch image-folder OCR | `python -m pipelines.image_ocr_summary <folder>` |
| Extract distinct video frames | `python -m extras.video_frames <video>` |
| Whisper transcribe | `python -m extras.whisper <media>` |

## Why these boundaries

- `cli/` exists to make entry points discoverable. Anything in `cli/` is a
  script you run; everything else is library code you import.
- `core/` collects the things that have nothing to do with OCR specifically —
  the same modules would survive if we replaced the whole capture/processing
  layer.
- `ollama/`, `sinks/`, `capture/` segregate by concern (LLM client, output
  destinations, input sources) so adding a new Slack sink or a new Twitch
  capture source has an obvious home.
- `summary/` and `pipelines/` are the orchestration layer that ties the others
  together. They will likely shrink (or disappear) when the Node protocol from
  `VISION.md` lands.

## Known issues

- Top-level `ollama/` shadows the PyPI `ollama` package. Acceptable while we
  shell out to the Ollama CLI; revisit if we adopt the Python SDK.
- `cli/` shims duplicate argparse setup with the modules they call. The Node
  protocol (Vision doc) is the planned cleanup.

## Next steps

See `docs/VISION.md` for the pipeline-builder direction and `docs/IDEAS.md`
for assorted improvement ideas not yet scheduled.
