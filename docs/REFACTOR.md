# Refactor Notes

## Status: DONE

The flat root layout has been fully migrated to module packages.

## What changed

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
| `screen_ocr.py` | `cli/screen.py` + `capture/screen.py` |
| `camera_ocr.py` | `cli/camera.py` + `capture/camera.py` |
| `summarize_responses.py` | `summary/batcher.py` + `cli/summarize.py` |
| `summary_watcher.py` | `summary/watcher.py` + `cli/watch.py` |
| `test_crop.py` | `cli/test_crop.py` |
| `pipelines/image_ollama_ocr.py` | `pipelines/image_ocr.py` |
| `pipelines/image_ocr_summary_watcher.py` | `pipelines/image_ocr_summary.py` |
| `extra_features/pdf_images.py` | `extras/pdf_images.py` |
| `extra_features/video_distinct_frames.py` | `extras/video_frames.py` |
| `extra_features/openai_video_transcription.py` | `extras/whisper.py` |

## What was deleted

| File | Reason |
|---|---|
| `utils.py` | Compatibility shim, no longer needed |
| `pipelines/image-ocr-summary-watcher.py` | Legacy hyphenated wrapper |
| `pipelines/image-ollama-ocr.py` | Legacy hyphenated wrapper |
| `pipelines/summarize_ocr_folder_once.py` | Broken untracked file with stale imports |
| `ocr_all_content.sh` | Stale module paths |
| `process_visual_multimodal.sh` | Stale module paths |
| `run_study_batch.sh` | Stale module paths |

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

## Remaining known issues

- Top-level `ollama/` shadows the PyPI `ollama` package. Acceptable while shelling out to the CLI; revisit if adopting the Python SDK.
- `cli/` entry points duplicate argparse setup with the modules they delegate to. The Node protocol (see `VISION.md`) is the planned fix.
- No automated tests yet.
