from __future__ import annotations

import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..auth import require_api_key
from ..models import Job

router = APIRouter(prefix="/jobs", tags=["export"], dependencies=[Depends(require_api_key)])


@router.get("/export/csv")
async def export_jobs_csv(session: AsyncSession = Depends(get_session)):
    jobs = (await session.execute(select(Job))).scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "company_id",
        "title",
        "url",
        "location",
        "work_mode",
        "match_score",
        "salary_min",
        "salary_max",
        "salary_source",
        "status",
        "first_seen",
        "last_seen",
    ])
    for job in jobs:
        writer.writerow([
            job.company_id,
            job.title,
            job.url,
            job.location,
            job.work_mode,
            job.match_score,
            job.salary_min,
            job.salary_max,
            job.salary_source,
            job.status,
            job.first_seen,
            job.last_seen,
        ])

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auros-jobs.csv"},
    )
