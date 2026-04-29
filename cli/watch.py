#!/usr/bin/env python3
"""CLI entry point for the summary watcher. Delegates to summary.watcher."""

from __future__ import annotations

from summary.watcher import main

if __name__ == "__main__":
    raise SystemExit(main())
