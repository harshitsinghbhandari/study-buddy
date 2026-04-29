# Vision: Pipeline Builder & Runner

## Goal

Turn screen-ocr from a collection of single-purpose CLI scripts into a general
**capture → process → sink** pipeline platform with a dashboard, where any input
can be wired to any output through any chain of processors.

## What we're really building

Three independent things that often get conflated:

1. **A pipeline runtime** — typed nodes (Source / Processor / Sink), a scheduler,
   state and cursor tracking, retries, backpressure.
2. **A pipeline definition format** — YAML/JSON describing "screen crop every 10s
   → deepseek-ocr → JSONL → gemma summarizer → Discord". Backed by a registry
   of available node types.
3. **A dashboard** — web UI to build, start, stop, and inspect pipelines and
   view live logs/outputs.

## Current state

Steps 1–3 of the sequencing plan below are **done**:

- **Node protocol** (`runtime/protocol.py`): `Source`, `Processor`, `Sink` base
  classes with `configure(params)` + `async run(inbox, outbox, ctx)`.
- **8 node types** in `nodes/` (3 sources, 3 processors, 2 sinks) with
  `@register("type.name")` decorator and JSON param schemas.
- **LinearRunner** (`runtime/runner.py`) wires nodes through asyncio queues,
  persists events/state/checkpoints to SQLite via `PipelineContext`.
- **YAML definitions** in `pipelines/defs/` loaded with topological sort.
- **SQLite** (`core/db.py`) for pipelines, runs, events, state, checkpoints.
- **FastAPI** (`api/`) with CRUD, start/stop, SSE log streaming.
- **CLI** (`cli/pipeline.py`) with `run`, `api`, `nodes` subcommands.
- **17 passing tests**.

Next: **Phase 4 — React dashboard**.

## Proposed shape

### Node interface

```python
class Node:
    def configure(self, params: dict) -> None: ...
    async def run(self, inbox, outbox, ctx) -> None: ...
    # ctx: state store, logger, cancellation token
```

Three node kinds, all the same protocol:

- **Source** — emits items: screen frame, camera frame, image-folder iterator,
  file watcher, webhook receiver, RSS, S3 listing, video frame extractor, …
- **Processor** — consumes + emits: Ollama OCR, Ollama summarize, hash-dedup,
  regex extract, image crop, LLM classify, HTTP transform, Whisper transcribe, …
- **Sink** — consumes only: JSONL append, Discord, Slack, webhook POST, SQLite,
  S3 upload, email, …

### Pipeline

A pipeline is a linear chain of node instances (DAG support planned), stored as
YAML. The runtime instantiates nodes from a registry, wires queues between them,
runs them as async tasks, and persists checkpoints to SQLite.

### Dashboard

Thin layer over the same runtime:

- **Backend**: FastAPI — `/pipelines`, `/runs`, `/nodes` (registry),
  `/runs/{id}/logs` (SSE). **Done.**
- **Frontend**: React + React Flow for the canvas. Node palette and config
  forms generated from each node's JSON schema. Live runs panel. **Next.**
- **CLI**: thin client over the same API — no duplicated logic. **Done.**

## Decisions made

| Decision | Choice | Rationale |
|---|---|---|
| Build vs adopt | **Build** | Learning + portfolio goal, OCR-domain abstractions |
| Concurrency | **asyncio** | Most work is subprocess + HTTP I/O |
| Storage | **SQLite** | Pipeline defs, runs, logs, checkpoints. Files for raw artifacts. |
| Graph shape | **Linear first** | Start simple, add DAG branching later |
| Auth | **None (localhost)** | Localhost only for v1 |
| Plugins | **In-tree** | v1 in-tree, plugin protocol v2 |
| API framework | **FastAPI** | Async-native, automatic OpenAPI docs |

## Sequencing

1. ~~Node protocol + linear runner + YAML definitions.~~ **Done (Phase 1)**
2. ~~SQLite-backed run state, event log, checkpoints.~~ **Done (Phase 2)**
3. ~~FastAPI with `/pipelines` CRUD, `/runs`, `/nodes`, SSE logs.~~ **Done (Phase 3)**
4. React dashboard with React Flow. **Next (Phase 4)**
5. New sources/sinks (RSS, Slack, S3, etc.).
6. DAG runner (branching pipelines).
7. Container image, auth, multi-user.
