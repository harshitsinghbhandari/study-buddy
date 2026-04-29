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

The current code already contains #1 and #2 implicitly: every script is a
hardcoded pipeline. The work is *extracting* that shape, not inventing it.

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

A pipeline is a DAG of node instances + edges, stored as JSON. The runtime
instantiates nodes from a registry, wires queues between them, runs them as
async tasks, and persists checkpoints.

### Dashboard

Thin layer over the same runtime:

- **Backend**: FastAPI exposing `/pipelines`, `/runs`, `/nodes` (registry),
  `/logs/stream` (SSE/WebSocket).
- **Frontend**: React + React Flow for the canvas. Node palette and config
  forms generated from each node's JSON schema. Live runs panel.
- **CLI**: thin client over the same API — no duplicated logic.

## Decisions to make

| Decision | Options | Lean |
|---|---|---|
| Build vs adopt | Roll our own / Prefect / Dagster / n8n / Node-RED | **Adopt** if "have it working" matters most. **Build** if learning is the point. |
| Concurrency | asyncio queues / threads+processes | **asyncio** (most work is subprocess + HTTP) |
| Storage | files / SQLite | **SQLite** for pipeline defs, runs, logs, checkpoints. Files for raw artifacts. |
| Graph shape | linear / DAG | **Start linear**, add branches when needed |
| Auth | none / real auth | **Localhost only** for v1 |
| Plugins | in-tree / entry points | **In-tree** v1, plugin protocol v2 |

## Honest tradeoff

If the goal is "I want a dashboard to wire screen capture + Ollama + Discord,"
n8n gets you there in a weekend (it has Ollama and Discord nodes plus a
custom-node SDK). Build-your-own makes sense if you want to learn the runtime,
need OCR-domain abstractions n8n can't express (typed image cursors,
hash-dedup as a first-class concept), or want a portfolio piece.

## Sequencing if we build it

1. Refactor existing code into the Node protocol — no UI yet. Convert
   `screen_ocr` to `ScreenSource` + `OllamaProcessor` + `JsonlSink` + a tiny
   linear runner reading a YAML file. Proves the abstraction.
2. SQLite-backed run state. Replace `state.json` and `responses.jsonl` lookups.
3. FastAPI with `/pipelines` CRUD and `/runs/{id}/logs` SSE. Drive with curl.
4. React dashboard with React Flow. Palette comes from the registry endpoint.
5. New sources/sinks (RSS, Slack, S3, etc.). By step 5 each new node is ~50
   lines because the framework carries the weight.
