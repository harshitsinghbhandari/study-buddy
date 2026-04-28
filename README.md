# Screen OCR Watcher

Small CLI that watches a fixed screen crop and sends changed frames to Ollama.

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

Change the interval:

```bash
python screen_ocr.py --run no-stop --interval 10
```

Responses are appended to `responses.jsonl`. The temporary crop is written as
`img.png` before calling Ollama and deleted after the response arrives.

Defaults live in `config.py`.
