#!/usr/bin/env python3
"""CLI entry point for batch summarization. Delegates to summary.batcher."""

from __future__ import annotations

from summary.batcher import main

if __name__ == "__main__":
    raise SystemExit(main())
