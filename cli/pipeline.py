#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

import nodes.sources.screen
import nodes.sources.camera
import nodes.sources.folder
import nodes.processors.hash_dedup
import nodes.processors.ollama_ocr
import nodes.processors.ollama_summarize
import nodes.sinks.jsonl
import nodes.sinks.discord
from core.db import Database
from runtime.context import PipelineContext
from runtime.loader import load_pipeline
from runtime.runner import LinearRunner

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a pipeline from a YAML definition.")
    parser.add_argument("pipeline", type=Path, help="Path to pipeline YAML file.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path (enables run tracking).")
    args = parser.parse_args()

    if not args.pipeline.exists():
        print(f"pipeline not found: {args.pipeline}")
        return 1

    pipeline_def = load_pipeline(args.pipeline)
    nodes = pipeline_def.instantiate()

    cancel = asyncio.Event()

    def handle_stop(signum: int, _frame: object) -> None:
        cancel.set()

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    db = Database(args.db) if args.db else None
    ctx = PipelineContext(
        pipeline_name=pipeline_def.name,
        db=db,
        cancel=cancel,
    )

    runner = LinearRunner(pipeline_def, nodes, ctx)
    print(f"pipeline '{pipeline_def.name}' started with {len(nodes)} node(s)")

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        runner.stop()
    except Exception as exc:
        print(f"pipeline failed: {exc}")
        return 1

    print(f"pipeline '{pipeline_def.name}' stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
