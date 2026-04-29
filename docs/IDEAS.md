# Ideas Backlog

Loose collection of improvements not yet scheduled. Promote to issues / plan
docs when ready.

## Code quality

- ~~Add `pyproject.toml` with `black`, `mypy`, `ruff`, `pytest` config~~ — done.
- ~~Replace ad-hoc `argparse` scripts with subcommands under a single CLI~~ — done (`cli/pipeline.py`).
- ~~Collapse the two summary watchers~~ — done (replaced by node protocol).
- Structured logging (JSON to stdout) instead of `print`.
- Type checking pass with `mypy` or `pyright`.
- CI pipeline (GitHub Actions: lint + test on push).

## Pipeline platform — remaining

- **Phase 4**: React + React Flow dashboard. Node palette + config forms
  generated from each node's JSON schema. Live runs panel.
- **Phase 5**: More sources: file watcher, webhook receiver, RSS, S3 listing.
- More sinks: Slack, generic webhook POST, S3 upload, email.
- More processors: regex extract, image crop, LLM classify, Whisper
  transcribe-as-processor.
- DAG runner (branching pipelines — current `LinearRunner` is linear only).
- Resume from checkpoint on crash (infrastructure exists, not yet wired).
- Retry/backoff policy for subprocess and HTTP nodes.

## Operational

- Health endpoint + Prometheus metrics for long-running watchers.
- Container image so the watchers can run on a homelab box.
- Auth / API key for non-localhost deployments.

## UX

- Live preview of the configured crop box in a small overlay window.
- Tail mode for event log (`GET /runs/{id}/logs` SSE exists, CLI tail TBD).
- Browser-based "what is the screen-ocr seeing right now?" page.
- Drag-and-drop pipeline builder on the React dashboard.

## Domain

- Track topic *transitions* over time (when did focus shift from RAG to
  vector indexes?), not just a flat summary.
- Per-application context: detect the active app from window metadata,
  attach it to every record, group summaries by app.
- Deduplicate near-identical OCR output (current dedup is pixel-hash on the
  source image, not the text).

## Open questions

- Should the dashboard let users import an arbitrary Python function as a
  processor node, or are we strictly registry-only?
- Do we ever want multi-host pipelines, or is single-machine enough?
- YAML vs JSON pipeline format — currently YAML for human-editability;
  dashboard will likely write JSON directly.
