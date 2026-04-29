# Screen OCR Watcher

Small CLI that watches a configured screen crop and sends changed frames to Ollama.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run indefinitely:

```bash
python screen_ocr.py --run no-stop
```

Run five screenshot checks:

```bash
python screen_ocr.py --run 5
```

Run the laptop camera pipeline:

```bash
python camera_ocr.py --run no-stop
```

Summarize screen OCR responses in batches of 20:

```bash
python summarize_responses.py
```

Run the summary and Discord watcher as a separate process:

```bash
python summary_watcher.py
```

Post the current partial summary batch too:

```bash
python summary_watcher.py --all
```

Disable thinking explicitly for summaries:

```bash
python summarize_responses.py --think=false
```

Change the interval:

```bash
python screen_ocr.py --run no-stop --interval 10
```

Archive every changed image after Ollama finishes:

```bash
python screen_ocr.py --run no-stop --archive-images
```

Test the crop box:

```bash
python test_crop.py
```

Override the crop box for a preview:

```bash
python test_crop.py --crop-box 350,250,1350,850
```

Convert a PDF into page images:

```bash
python -m extra_features.pdf_images notes.pdf --output-dir pdf_images
```

Run Ollama OCR over an image folder:

```bash
python -m pipelines.image_ollama_ocr content/images/RAG-1
```

Outputs are written to `data/ocr-output/<image-folder>/responses.jsonl`. The
pipeline rests for a random 5-7 seconds between OCR calls by default.

Summarize and post image-folder OCR output:

```bash
python -m pipelines.image_ocr_summary_watcher content/images/RAG-1
```

This watcher consumes available OCR rows in batches of 10, including the final
partial batch, posts summaries to Discord, and stores per-folder summaries next
to the OCR output as `data/ocr-output/<image-folder>/summaries.json`.

Responses are appended to `responses.jsonl`. The temporary crop is written as
`img.png` before calling Ollama and deleted after the response arrives. With
`--archive-images`, the processed `img.png` is moved to
`archive/img_TIMESTAMP.png` instead.

Defaults live in `config.py`. The crop box uses absolute screenshot coordinates:
`CROP_BOX = (left, top, right, bottom)`.

The camera pipeline does not crop. It saves the full camera frame to `img.png`,
passes that same `img.png` to Ollama, and writes responses to
`camera_responses.jsonl` by default. Set `CAMERA_OLLAMA_QUESTION` in
`config.py` for the camera prompt.

The summary pipeline currently reads only `responses.jsonl`. It sends each batch
of response strings to the configured summary model and saves records in
`summaries.json` with source timestamp and response ID ranges. It passes the
configured `--think` value to Ollama.

The watcher pipeline is decoupled from screen capture. Run `screen_ocr.py` in
one terminal and `summary_watcher.py` in another. The watcher polls
`responses.jsonl`, summarizes new complete batches, posts unposted summaries to
Discord using `DISCORD_WEBHOOK_URL` from `.env`, and tracks posting progress in
`state.json`. By default it waits for complete batches; pass `--all` when you
want it to summarize and post the final partial batch too.

## Module Layout

The code is split by pipeline responsibility:

- `runtime.py` - run modes, signal handling, timestamps, text coercion.
- `ollama_client.py` - all Ollama subprocess calls.
- `event_log.py` - append-only JSONL response records and response IDs.
- `file_artifacts.py` - temp image cleanup and archive moves.
- `state_store.py` - JSON state load/save.
- `env_loader.py` - `.env` loading.
- `discord_sink.py` - Discord webhook posting.
- `extra_features/` - standalone capabilities such as PDF page rendering.
- `pipelines/` - orchestration modules for larger workflows.
- `summarize_responses.py` - batch summary processor.
- `summary_watcher.py` - response-log watcher and Discord dispatcher.
- `utils.py` - compatibility re-exports for older imports.
