from __future__ import annotations

import asyncio
import logging
from typing import Set

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal, get_session
from ..auth import require_api_key
from ..services.pipeline import run_full_scan, get_scan_status

logger = logging.getLogger(__name__)

# Track background tasks to prevent garbage collection and enable monitoring
_background_tasks: Set[asyncio.Task] = set()

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(require_api_key)])


def _task_done_callback(task: asyncio.Task) -> None:
    """Callback to handle task completion and cleanup."""
    _background_tasks.discard(task)
    try:
        exc = task.exception()
        if exc:
            logger.error(f"Background scan task failed: {exc}", exc_info=exc)
        else:
            logger.info("Background scan task completed successfully")
    except asyncio.CancelledError:
        logger.warning("Background scan task was cancelled")


@router.post("/trigger")
async def trigger_scan(session: AsyncSession = Depends(get_session)):
    # Thread-safe check via database
    status = await get_scan_status(session)
    if status.get("status") == "running":
        return {"status": "running"}

    async def _run():
        try:
            logger.info("Starting background scan task")
            async with SessionLocal() as session:
                await run_full_scan(session)
        except Exception as e:
            logger.error(f"Background scan task error: {e}", exc_info=True)
            raise

    task = asyncio.create_task(_run(), name="full_scan")
    _background_tasks.add(task)
    task.add_done_callback(_task_done_callback)
    return {"status": "started"}


@router.post("/stop")
async def stop_scan(session: AsyncSession = Depends(get_session)):
    """Stop any running scan."""
    cancelled = 0
    for task in list(_background_tasks):
        if not task.done():
            task.cancel()
            cancelled += 1

    # Reset scan state to idle
    from ..models import ScanState
    from sqlalchemy import select

    result = await session.execute(select(ScanState).where(ScanState.id == "current"))
    state = result.scalar_one_or_none()
    if state and state.status == "running":
        state.status = "idle"
        await session.commit()

    return {"status": "stopped", "tasks_cancelled": cancelled}


@router.get("/status")
async def get_status(session: AsyncSession = Depends(get_session)):
    return await get_scan_status(session)
