"""Runtime helpers shared by long-running CLI processes."""

from __future__ import annotations

import argparse
import signal
from datetime import datetime, timezone
from typing import Literal

RunMode = int | Literal["no-stop"]


class StopRequested(Exception):
    """Raised when the process receives a stop signal."""


def parse_run(value: str) -> RunMode:
    if value == "no-stop":
        return value
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--run must be an integer or 'no-stop'") from exc
    if count < 1:
        raise argparse.ArgumentTypeError("--run must be at least 1")
    return count


def install_signal_handlers() -> None:
    def handle_stop(signum: int, _frame: object) -> None:
        raise StopRequested(f"received signal {signum}")

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)


def should_continue(run_mode: RunMode, completed_checks: int) -> bool:
    return run_mode == "no-stop" or completed_checks < run_mode


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def filename_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
