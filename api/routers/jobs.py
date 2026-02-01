from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..auth import require_api_key
from ..models import Job
from ..schemas import JobOut, JobListOut, JobStatusUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])


def _escape_like_pattern(value: str) -> str:
    """Escape wildcard characters in user input for safe use in LIKE patterns."""
    # Escape the backslash first, then the SQL LIKE wildcards
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=JobListOut)
async def list_jobs(
    status: str | None = None,
    company_id: str | None = None,
    min_score: float | None = None,
    query: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Job)
    if status:
        stmt = stmt.where(Job.status == status)
    if company_id:
        stmt = stmt.where(Job.company_id == company_id)
    if min_score is not None:
        stmt = stmt.where(Job.match_score >= min_score)
    if query:
        escaped_query = _escape_like_pattern(query)
        stmt = stmt.where(Job.title.ilike(f"%{escaped_query}%", escape="\\"))

    stmt = stmt.order_by(Job.match_score.desc().nullslast(), Job.last_seen.desc())
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    results = (await session.execute(stmt.offset(offset).limit(limit))).scalars().all()

    return JobListOut(jobs=results, total=total)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/status", response_model=JobOut)
async def update_status(
    job_id: str,
    payload: JobStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = payload.status.value
    await session.commit()
    await session.refresh(job)
    return job
