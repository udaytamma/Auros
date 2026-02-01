from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..config import settings
from ..auth import require_api_key
from ..db import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"], dependencies=[Depends(require_api_key)])


@router.get("")
async def health_check():
    db_status = "ok"
    ollama_status = "unknown"
    slack_status = "disabled"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_status = "ok" if resp.status_code == 200 else "error"
    except httpx.TimeoutException as e:
        logger.warning(f"Ollama health check timed out: {e}")
        ollama_status = "timeout"
    except httpx.HTTPError as e:
        logger.error(f"Ollama health check failed: {e}")
        ollama_status = "error"

    if settings.SLACK_WEBHOOK_URL:
        slack_status = "configured"

    return {
        "db": db_status,
        "ollama": ollama_status,
        "slack": slack_status,
    }
