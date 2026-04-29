# Screen OCR Watcher

Pipelines that capture from a screen, camera, image folder, PDF, or video,
send frames to an Ollama OCR model, and post batched summaries to Discord.

See `docs/VISION.md` for the planned pipeline-builder + dashboard direction
and `docs/ARCHITECTURE.md` for the current layout.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ollama must be installed separately and the relevant models pulled
(`deepseek-ocr` for vision, `gemma4:31b-cloud` for summaries by default).

## Running

| Task | Command |
|---|---|
| Watch screen | `python -m cli.screen --run no-stop` |
| Watch screen, fixed count | `python -m cli.screen --run 5` |
| Watch camera | `python -m cli.camera --run no-stop` |
| Override interval | `python -m cli.screen --run no-stop --interval 10` |
| Archive each processed image | `python -m cli.screen --run no-stop --archive-images` |
| Preview crop box | `python -m cli.test_crop` |
| Override crop box | `python -m cli.test_crop --crop-box 350,250,1350,850` |
| Summarize responses | `python -m cli.summarize` |
| Disable summary thinking | `python -m cli.summarize --think=false` |
| Run summary + Discord watcher | `python -m cli.watch` |
| Include the partial batch | `python -m cli.watch --all` |
| Render PDF pages to images | `python -m extras.pdf_images notes.pdf --output-dir pdf_images` |
| Run Ollama OCR on a folder | `python -m pipelines.image_ocr content/images/RAG-1` |
| Watch image-folder OCR | `python -m pipelines.image_ocr_summary content/images/RAG-1` |
| Extract distinct video frames | `python -m extras.video_frames clip.mp4` |
| Whisper transcribe | `python -m extras.whisper clip.mp4` |

## Module layout

| Package | Role |
|---|---|
| `cli/` | Thin entry-point scripts (argparse + `main`). |
| `core/` | Config, runtime, event log, state store, file artifacts, env loader. |
| `ollama/` | Ollama subprocess client. |
| `sinks/` | Output destinations (Discord). |
| `capture/` | Input sources (screen, camera). |
| `summary/` | Batching and watcher logic for summarization. |
| `pipelines/` | Higher-level orchestrators (image-folder OCR, watcher). |
| `extras/` | Standalone tools (PDF render, video frames, Whisper). |
| `docs/` | Architecture, vision, refactor notes, ideas. |

## Output paths

- `responses.jsonl` — screen OCR responses (append-only, one JSON per line).
- `camera_responses.jsonl` — camera OCR responses.
- `data/ocr-output/<folder>/responses.jsonl` — image-folder OCR.
- `summaries.json` — batched summaries (atomic write).
- `state.json` — watcher progress (Discord post tracking, cursors).
- `archive/img_TIMESTAMP.png` — archived screenshots when `--archive-images` is passed.

## Config

Defaults live in `core/config.py`. Crop box uses absolute screenshot
coordinates: `CROP_BOX = (left, top, right, bottom)`. The Discord webhook
URL is read from `DISCORD_WEBHOOK_URL` in `.env`.

The camera pipeline does not crop — it saves the full frame to `img.png`,
passes that to Ollama, and writes responses to `camera_responses.jsonl`.
Set `CAMERA_OLLAMA_QUESTION` in `core/config.py` for the camera prompt.

The summary pipeline currently reads only `responses.jsonl`. It sends each
batch of response strings to the configured summary model and saves records
in `summaries.json` with source timestamp and response ID ranges.

The watcher is decoupled from screen capture: run `python -m cli.screen` in
one terminal and `python -m cli.watch` in another. The watcher polls
`responses.jsonl`, summarizes new complete batches, posts unposted summaries
to Discord, and tracks posting progress in `state.json`. Pass `--all` to
include the final partial batch.
