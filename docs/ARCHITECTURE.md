# Current Architecture

Snapshot of the system after Phases 1–3 (pipeline runtime, SQLite, FastAPI).

## Module layout

| Package | Role |
|---|---|
| `runtime/` | Pipeline runtime: Node protocol, async runner, YAML loader, registry. |
| `nodes/` | All node implementations grouped by kind (sources, processors, sinks). |
| `api/` | FastAPI backend — pipeline CRUD, run tracking, SSE log streaming. |
| `core/` | Shared infrastructure: config, env loader, SQLite database layer. |
| `ollama/` | Ollama subprocess client (legacy, used by `extras/`). |
| `sinks/` | Discord webhook sink (legacy, used by `extras/`). |
| `extras/` | Standalone tools (PDF→images, video frames, Whisper). |
| `pipelines/defs/` | YAML pipeline definitions. |
| `cli/` | Single CLI entry point with subcommands (`run`, `api`, `nodes`). |
| `docs/` | Vision, architecture, refactor notes, ideas. |
| `tests/` | Pytest suite (17 tests). |

## Data flow

```
YAML definition ─► loader ─► instantiate nodes from registry
                                         │
                                         ▼
Source ─[queue]─► Processor ─[queue]─► Sink    (LinearRunner, asyncio)
                                         │
                                         ▼
                                    SQLite DB
                              (events, state, checkpoints)
                                         │
                                         ▼
                                   FastAPI API
                              (/pipelines, /runs, /nodes)
```

Nodes communicate through async queues. The runner creates one queue per edge,
drives all nodes concurrently via `asyncio.create_task`, and writes events to
SQLite through `PipelineContext`. The API server exposes pipeline CRUD and
start/stop over HTTP.

## Node types

| Kind | Type key | Description |
|---|---|---|
| Source | `source.screen` | Periodic screen crop capture with hash change-detection |
| Source | `source.camera` | Periodic camera frame capture |
| Source | `source.folder` | Iterate images in a folder |
| Processor | `processor.hash_dedup` | Skip items with duplicate hash keys |
| Processor | `processor.ollama_ocr` | Async Ollama OCR subprocess call |
| Processor | `processor.ollama_summarize` | Batch responses and summarize with Ollama |
| Sink | `sink.jsonl` | Append items as JSONL records |
| Sink | `sink.discord` | Post text to a Discord webhook |

Each node declares a `_params_schema` dict used by `GET /nodes` to advertise
configurable parameters.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/nodes` | List registered node types with param schemas |
| GET | `/pipelines` | List saved pipelines |
| POST | `/pipelines` | Create pipeline (validates YAML) |
| GET | `/pipelines/{id}` | Get pipeline definition |
| DELETE | `/pipelines/{id}` | Delete pipeline |
| POST | `/pipelines/{id}/start` | Start a pipeline run |
| POST | `/pipelines/{id}/stop` | Stop a running pipeline |
| GET | `/runs` | List all runs |
| GET | `/runs/{id}` | Run status |
| GET | `/runs/{id}/logs` | SSE event stream |

## SQLite schema

| Table | Purpose |
|---|---|
| `pipelines` | Saved pipeline definitions (name, YAML) |
| `runs` | Run instances with status + timestamps |
| `events` | Per-node log events (item_emitted, item_consumed, error, log) |
| `state` | Generic key/value state store (replaces `state.json`) |
| `checkpoints` | Per-node cursor for resume-after-crash |

## CLI

```bash
python -m cli.pipeline run <yaml> [--db <path>]    # Run a pipeline directly
python -m cli.pipeline api [--host 127.0.0.1] [--port 8000]  # Start API server
python -m cli.pipeline nodes                        # List registered node types
```

## Dependencies

- **Runtime**: `PyYAML` (pipeline definitions)
- **Screen capture**: `Pillow` (ImageGrab)
- **Camera + video**: `opencv-python`
- **PDF**: `PyMuPDF` (extras only)
- **API**: `fastapi`, `uvicorn`, `httpx`
- **Services**: Ollama CLI on PATH, Discord webhook (optional)
- **Optional**: ffmpeg + whisper CLIs for `extras/whisper.py`

## What's done

- [x] Modular package layout (`core/ollama/sinks/extras/`)
- [x] Node protocol (`Source`, `Processor`, `Sink`) with async `run()`
- [x] LinearRunner wiring nodes through asyncio queues
- [x] YAML pipeline definitions with topological sort
- [x] 8 node types (3 sources, 3 processors, 2 sinks)
- [x] SQLite state store, event log, run tracking, checkpoints
- [x] FastAPI backend with CRUD, start/stop, SSE logs
- [x] Single CLI with subcommands
- [x] `pyproject.toml` with pytest config
- [x] 17 passing tests

## What's left

- [ ] Phase 4: React dashboard (React Flow canvas, node palette, run panel)
- [ ] Phase 5: Expand node library (file_watcher, webhook, RSS, Slack, etc.)
- [ ] DAG runner (branching pipelines — current runner is linear only)
- [ ] Container image
- [ ] Auth / multi-user
