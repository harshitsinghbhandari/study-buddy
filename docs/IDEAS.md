# Ideas Backlog

Loose collection of improvements not yet scheduled. Promote to issues / plan
docs when ready.

## Code quality

- Add `pyproject.toml` with `black`, `mypy`, `ruff`, `pytest` config and
  `[project.scripts]` entries instead of relying on `python -m`.
- Replace ad-hoc `argparse` scripts with subcommands under a single
  `screen-ocr` CLI.
- First three pure-function tests: `core.event_log.append_response`,
  `summary.batcher.batched` + `existing_batch_keys`,
  `core.env_loader.load_env_file`.
- Collapse the two summary watchers (`summary/watcher.py` and
  `pipelines/image_ocr_summary.py`) — they're 80% the same code with two
  state-tracking strategies. The cursor strategy is simpler and works for
  both.

## Pipeline platform (see VISION.md for the full plan)

- Define `Node` protocol with `configure` + `async run(inbox, outbox, ctx)`.
- Convert `cli/screen.py` to `ScreenSource` + `OllamaProcessor` + `JsonlSink`
  wired by a tiny YAML-driven runner. Proves the abstraction.
- SQLite-backed run state to replace `state.json`.
- FastAPI app exposing `/pipelines`, `/runs`, `/nodes`, `/logs/stream`.
- React + React Flow dashboard. Node palette + config forms generated from
  each node's JSON schema.
- More sources: file watcher, webhook receiver, RSS, S3 listing.
- More sinks: Slack, generic webhook POST, SQLite, S3 upload, email.
- More processors: regex extract, image crop, LLM classify, Whisper
  transcribe-as-processor.

## Operational

- Structured logging (JSON to stdout) instead of `print`.
- Health endpoint + Prometheus metrics for long-running watchers.
- Container image so the watchers can run on a homelab box.
- Retry policy for Ollama timeouts (currently a single attempt).

## UX

- Live preview of the configured crop box in a small overlay window.
- Tail mode for `responses.jsonl` (`python -m cli.tail`).
- Browser-based "what is the screen-ocr seeing right now?" page.

## Domain

- Track topic *transitions* over time (when did focus shift from RAG to
  vector indexes?), not just a flat summary.
- Per-application context: detect the active app from window metadata,
  attach it to every record, group summaries by app.
- Deduplicate near-identical responses before batching (current dedup is
  pixel-hash on the source image, not the OCR output).

## Open questions

- Should the dashboard let users import an arbitrary Python function as a
  processor node, or are we strictly registry-only?
- Do we ever want multi-host pipelines, or is single-machine enough?
- Is YAML the right pipeline format, or should the dashboard write JSON
  directly and skip the human-edited path?
