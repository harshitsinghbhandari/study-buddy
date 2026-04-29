"""Small Ollama subprocess client."""

from __future__ import annotations

import subprocess

from core import config


def build_ollama_prompt(question: str) -> str:
    return f"{config.OLLAMA_IMAGE_ARGUMENT} \n{question}"


def run_ollama_prompt(
    *,
    model: str,
    prompt: str,
    timeout: float,
    think: str | None = None,
) -> tuple[str, str, int | None]:
    command = [
        config.OLLAMA_COMMAND,
        "run",
    ]
    if think is not None:
        command.append(f"--think={think}")
    command.extend([model, prompt])

    process = subprocess.run(
        command,
        capture_output=True,
        cwd=config.BASE_DIR,
        text=True,
        timeout=timeout,
        check=False,
    )
    return process.stdout.strip(), process.stderr.strip(), process.returncode


def run_ollama(question: str, timeout: float) -> tuple[str, str, int | None]:
    return run_ollama_prompt(
        model=config.OLLAMA_MODEL,
        prompt=build_ollama_prompt(question),
        timeout=timeout,
    )
