#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
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


def cmd_run(args):
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
    ctx = PipelineContext(pipeline_name=pipeline_def.name, db=db, cancel=cancel)
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


def cmd_api(args):
    import uvicorn
    from api.app import create_app
    app = create_app(db_path=args.db)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def cmd_list_nodes(args):
    from runtime.registry import all_types
    for name, cls in sorted(all_types().items()):
        print(f"  {name:40s} {cls.node_kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen OCR Pipeline CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a pipeline from YAML")
    run_p.add_argument("pipeline", type=Path)
    run_p.add_argument("--db", type=Path, default=None)

    api_p = sub.add_parser("api", help="Start the API server")
    api_p.add_argument("--host", default="127.0.0.1")
    api_p.add_argument("--port", type=int, default=8000)
    api_p.add_argument("--db", default="screen_ocr.db")

    sub.add_parser("nodes", help="List registered node types")

    args = parser.parse_args()
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "api":
        cmd_api(args)
        return 0
    elif args.command == "nodes":
        cmd_list_nodes(args)
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
