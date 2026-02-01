from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from pathlib import Path
from time import monotonic

import httpx

from ..config import settings
from ..logging import configure_logging


async def _is_ollama_running(timeout: float = 1.5) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def _start_ollama() -> bool:
    if not settings.OLLAMA_START_COMMAND:
        return False

    log_path = Path("data") / "ollama-serve.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "ab")  # noqa: SIM115 - long-lived process

    try:
        subprocess.Popen(
            shlex.split(settings.OLLAMA_START_COMMAND),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return True


async def ensure_ollama_running() -> None:
    logger = configure_logging()

    if os.getenv("PYTEST_CURRENT_TEST") or not settings.OLLAMA_AUTO_START:
        logger.info_structured(
            "ollama_autostart_skipped",
            reason="pytest" if os.getenv("PYTEST_CURRENT_TEST") else "disabled",
        )
        return

    if await _is_ollama_running():
        logger.info_structured("ollama_ready", status="already_running")
        return

    if not _start_ollama():
        logger.warning_structured("ollama_autostart_failed", reason="start_command_failed")
        return

    deadline = monotonic() + settings.OLLAMA_START_TIMEOUT
    while monotonic() < deadline:
        if await _is_ollama_running(timeout=1.0):
            logger.info_structured("ollama_ready", status="started")
            return
        await asyncio.sleep(0.5)

    logger.warning_structured(
        "ollama_autostart_timeout",
        timeout_seconds=settings.OLLAMA_START_TIMEOUT,
    )
