# Screen OCR

A modular **capture → process → sink** pipeline platform. Define pipelines in
YAML, run them locally, manage via API or CLI.

## What it does

Capture screen crops, camera frames, or image folders; OCR them through a local
Ollama model; summarize batches and post to Discord. Or wire any combination of
sources, processors, and sinks through YAML pipeline definitions.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Requires [Ollama](https://ollama.com) running locally with `deepseek-ocr` pulled.
For summaries, pull `gemma4:31b-cloud`.

### Run a pipeline

```bash
python -m cli.pipeline run pipelines/defs/screen-ocr.yaml
python -m cli.pipeline run pipelines/defs/camera-ocr.yaml --db my_runs.db
```

### Start the API server

```bash
python -m cli.pipeline api --port 8000
```

Then:

```bash
# List available node types
curl http://localhost:8000/nodes

# Create a pipeline
curl -X POST http://localhost:8000/pipelines \
  -H "Content-Type: application/json" \
  -d '{"name": "screen-ocr", "definition_yaml": "..."}'

# Start a run
curl -X POST http://localhost:8000/pipelines/1/start

# Stream logs
curl http://localhost:8000/runs/1/logs

# List runs
curl http://localhost:8000/runs
```

### List registered node types

```bash
python -m cli.pipeline nodes
```

## Node types

| Kind | Type | Description |
|---|---|---|
| Source | `source.screen` | Periodic screen crop with hash dedup |
| Source | `source.camera` | Periodic camera frame capture |
| Source | `source.folder` | Iterate images in a folder |
| Processor | `processor.hash_dedup` | Skip duplicate items by hash |
| Processor | `processor.ollama_ocr` | OCR via Ollama subprocess |
| Processor | `processor.ollama_summarize` | Batch summarize via Ollama |
| Sink | `sink.jsonl` | Append to JSONL file |
| Sink | `sink.discord` | Post to Discord webhook |

## Project layout

```
screen-ocr/
├── runtime/          Pipeline runtime (protocol, runner, registry, loader)
├── nodes/            Node implementations
│   ├── sources/      screen, camera, folder
│   ├── processors/   hash_dedup, ollama_ocr, ollama_summarize
│   └── sinks/        jsonl, discord
├── api/              FastAPI backend
│   └── routes/       /nodes, /pipelines, /runs
├── core/             Config, SQLite database, env loader
├── ollama/           Ollama subprocess client
├── extras/           Standalone tools (PDF, video frames, Whisper)
├── pipelines/defs/   YAML pipeline definitions
├── cli/              CLI entry point
├── tests/            Pytest suite (17 tests)
└── docs/             Architecture, vision, ideas, refactor notes
```

## Pipeline YAML format

```yaml
name: screen-ocr
nodes:
  - id: grab
    type: source.screen
    params:
      crop_box: [350, 250, 1350, 850]
      interval: 10
  - id: dedup
    type: processor.hash_dedup
  - id: ocr
    type: processor.ollama_ocr
    params:
      model: deepseek-ocr
  - id: out
    type: sink.jsonl
    params:
      path: data/ocr-output/responses.jsonl
edges:
  - [grab, dedup]
  - [dedup, ocr]
  - [ocr, out]
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/nodes` | List registered node types with param schemas |
| GET | `/pipelines` | List saved pipelines |
| POST | `/pipelines` | Create pipeline |
| GET | `/pipelines/{id}` | Get pipeline definition |
| DELETE | `/pipelines/{id}` | Delete pipeline |
| POST | `/pipelines/{id}/start` | Start a run |
| POST | `/pipelines/{id}/stop` | Stop a run |
| GET | `/runs` | List all runs |
| GET | `/runs/{id}` | Run status |
| GET | `/runs/{id}/logs` | SSE event stream |

## Extras

```bash
python -m extras.pdf_images notes.pdf --output-dir pdf_images
python -m extras.video_frames lecture.mp4 --output-dir frames
python -m extras.whisper lecture.mp4
```

## Dependencies

- **Runtime**: `PyYAML`
- **Capture**: `Pillow` (screen), `opencv-python` (camera/video)
- **PDF**: `PyMuPDF` (extras only)
- **API**: `fastapi`, `uvicorn`, `httpx`
- **Services**: Ollama CLI on `PATH`
- **Optional**: ffmpeg + whisper CLIs for extras

## License

MIT
