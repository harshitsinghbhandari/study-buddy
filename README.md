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
of 20 response strings to `qwen3.5:0.8b` and saves records in `summaries.json`
with `timestamp_start` and `timestamp_end` for the source responses used. It
passes `--think=false` to Ollama by default.

In `screen_ocr.py --run no-stop`, complete summary batches are also checked
every 10 minutes by default and posted to Discord using `DISCORD_WEBHOOK_URL`
from `.env`. Runtime posting progress is tracked in `state.json`.
