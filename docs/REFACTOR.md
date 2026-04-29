# Refactor Notes

## Phase 0: Package reorganization — DONE

The flat root layout was migrated to module packages. See git history for the
full file mapping.

## Phase 1: Pipeline runtime — DONE

Extracted the common pipeline shape into a typed node protocol.

| New path | Role |
|---|---|
| `runtime/protocol.py` | `Node`, `Source`, `Processor`, `Sink` base classes |
| `runtime/context.py` | `PipelineContext` — state, checkpoints, event logging |
| `runtime/runner.py` | `LinearRunner` — wires nodes through asyncio queues |
| `runtime/registry.py` | `@register("type.name")` decorator + lookup |
| `runtime/loader.py` | YAML loading, `PipelineDef`, topological sort |
| `nodes/sources/screen.py` | Periodic screen crop capture |
| `nodes/sources/camera.py` | Periodic camera frame capture |
| `nodes/sources/folder.py` | Iterate images in a folder |
| `nodes/processors/hash_dedup.py` | Skip items with duplicate hash keys |
| `nodes/processors/ollama_ocr.py` | Ollama OCR subprocess |
| `nodes/processors/ollama_summarize.py` | Batch + summarize with Ollama |
| `nodes/sinks/jsonl.py` | Append items as JSONL |
| `nodes/sinks/discord.py` | Post text to Discord webhook |

### Deleted (superseded by nodes)

| Old path | Reason |
|---|---|
| `cli/screen.py`, `cli/camera.py` | Replaced by `cli/pipeline.py run` |
| `cli/summarize.py`, `cli/watch.py` | Replaced by pipeline definitions |
| `cli/test_crop.py` | Manual helper, no longer needed |
| `capture/` package | Logic moved to `nodes/sources/` |
| `summary/batcher.py`, `summary/watcher.py` | Logic moved to `nodes/processors/` |
| `pipelines/image_ocr.py`, `pipelines/image_ocr_summary.py` | Replaced by YAML defs + runner |

## Phase 2: SQLite — DONE

| New path | Role |
|---|---|
| `core/db.py` | SQLite `Database` class with full CRUD |

Tables: `meta`, `pipelines`, `runs`, `events`, `state`, `checkpoints`.
Integrated into `PipelineContext` and `LinearRunner`.

## Phase 3: FastAPI API — DONE

| New path | Role |
|---|---|
| `api/app.py` | FastAPI app factory with CORS + lifespan |
| `api/dependencies.py` | Shared `db` and `_active_runners` state |
| `api/routes/nodes.py` | `GET /nodes` |
| `api/routes/pipelines.py` | CRUD + `POST /pipelines/{id}/start|stop` |
| `api/routes/runs.py` | List/get runs, `GET /runs/{id}/logs` SSE |
| `cli/pipeline.py` | CLI with `run`, `api`, `nodes` subcommands |

## Current module layout

```
screen-ocr/
├── runtime/          Pipeline runtime (protocol, runner, registry, loader)
├── nodes/            Node implementations (sources/, processors/, sinks/)
├── api/              FastAPI backend (app, routes)
├── core/             Shared infra (config, db, env_loader)
├── ollama/           Ollama subprocess client (legacy)
├── sinks/            Discord sink (legacy)
├── extras/           Standalone tools (pdf, video, whisper)
├── pipelines/defs/   YAML pipeline definitions
├── cli/              CLI entry point
├── tests/            Pytest suite (17 tests)
└── docs/             Architecture, vision, ideas, refactor notes
```
