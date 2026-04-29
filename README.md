# Screen OCR Watcher

Capture screen crops, camera frames, or image folders; OCR them through a local Ollama model; summarize batches and post to Discord.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Requires [Ollama](https://ollama.com) running locally with `deepseek-ocr` pulled. For summaries, pull `gemma4:31b-cloud` (or set `--model`).

## Usage

### Screen OCR

```bash
python -m cli.screen --run no-stop
python -m cli.screen --run 5
python -m cli.screen --run no-stop --interval 10
python -m cli.screen --run no-stop --archive-images
```

### Camera OCR

```bash
python -m cli.camera --run no-stop
```

### Summarize responses

```bash
python -m cli.summarize
python -m cli.summarize --think=false
```

### Summary watcher (summarize + post to Discord)

```bash
python -m cli.watch
python -m cli.watch --all
python -m cli.watch --once
```

Set `DISCORD_WEBHOOK_URL` in `.env` for Discord posting.

### Crop preview

```bash
python -m cli.test_crop
python -m cli.test_crop --crop-box 350,250,1350,850
```

### Image-folder OCR

```bash
python -m pipelines.image_ocr content/images/RAG-1
```

Outputs to `data/ocr-output/<folder>/responses.jsonl`.

### Image-folder OCR summary watcher

```bash
python -m pipelines.image_ocr_summary content/images/RAG-1
```

### Extras

```bash
python -m extras.pdf_images notes.pdf --output-dir pdf_images
python -m extras.video_frames lecture.mp4 --output-dir frames
python -m extras.whisper lecture.mp4
```

## Module Layout

| Package | Role |
|---|---|
| `cli/` | Entry-point scripts. `python -m cli.<name>` to run. |
| `core/` | Shared infrastructure: config, runtime helpers, event log, state store, file artifacts, env loader. |
| `capture/` | Input sources: screen grab, camera frame. |
| `ollama/` | Ollama subprocess client. |
| `sinks/` | Output destinations (Discord webhook). |
| `summary/` | Batching and watcher logic for summarization. |
| `pipelines/` | Higher-level orchestrators (image-folder OCR, image-folder summary watcher). |
| `extras/` | Standalone tools (PDF to images, video frame extraction, Whisper transcription). |

Configuration lives in `core/config.py`. The crop box uses absolute screenshot coordinates: `CROP_BOX = (left, top, right, bottom)`.

## Dependencies

- Python: `Pillow` (screen grab), `opencv-python` (camera + video frames), `PyMuPDF` (PDF render).
- Services: Ollama CLI on `PATH`.
- Optional: `ffmpeg` + `whisper` CLIs for `extras/whisper.py`.

## License

MIT
