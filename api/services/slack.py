from __future__ import annotations

import httpx

from ..config import settings


async def notify_new_job(message: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False

    payload = {"text": message}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
        return resp.status_code in (200, 201, 202)
