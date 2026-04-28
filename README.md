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
