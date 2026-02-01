from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from ..db import SessionLocal
from ..services.pipeline import run_full_scan

logger = logging.getLogger(__name__)


def _parse_schedule_hours(hours_str: str) -> str:
    """Validate and parse schedule hours, returning valid cron format."""
    try:
        hours = [int(h.strip()) for h in hours_str.split(",")]
        valid_hours = [h for h in hours if 0 <= h <= 23]
        if len(valid_hours) != len(hours):
            logger.warning(f"Invalid hours in SCAN_SCHEDULE_HOURS: {hours_str}, using valid subset")
        if not valid_hours:
            logger.warning("No valid hours found, using default: 6,12,18")
            valid_hours = [6, 12, 18]
        return ",".join(str(h) for h in valid_hours)
    except ValueError:
        logger.error(f"Cannot parse SCAN_SCHEDULE_HOURS: {hours_str}, using default: 6,12,18")
        return "6,12,18"


async def _scheduled_scan():
    async with SessionLocal() as session:
        await run_full_scan(session)


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.SCAN_TIMEZONE)
    validated_hours = _parse_schedule_hours(settings.SCAN_SCHEDULE_HOURS)
    scheduler.add_job(
        _scheduled_scan,
        trigger=CronTrigger(hour=validated_hours),
        id="scheduled_scan",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
