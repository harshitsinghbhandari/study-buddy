"""Compatibility imports for older pipeline modules.

New code should import from the focused modules directly:
runtime, ollama_client, event_log, file_artifacts, env_loader,
discord_sink, and state_store.
"""

from discord_sink import post_discord_message
from env_loader import get_env_value, load_env_file
from event_log import append_response
from file_artifacts import archive_processed_image, finish_temp_image, remove_temp_image
from ollama_client import build_ollama_prompt, run_ollama, run_ollama_prompt
from runtime import (
    RunMode,
    StopRequested,
    as_text,
    filename_timestamp,
    install_signal_handlers,
    parse_run,
    should_continue,
    utc_now,
)
from state_store import load_state, save_state

__all__ = [
    "RunMode",
    "StopRequested",
    "append_response",
    "archive_processed_image",
    "as_text",
    "build_ollama_prompt",
    "filename_timestamp",
    "finish_temp_image",
    "get_env_value",
    "install_signal_handlers",
    "load_env_file",
    "load_state",
    "parse_run",
    "post_discord_message",
    "remove_temp_image",
    "run_ollama",
    "run_ollama_prompt",
    "save_state",
    "should_continue",
    "utc_now",
]
