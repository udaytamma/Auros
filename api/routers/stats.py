from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..auth import require_api_key
from ..models import Job, ScanLog
from ..schemas import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=StatsOut)
async def get_stats(session: AsyncSession = Depends(get_session)):
    # Total count using SQL aggregation
    total_result = await session.execute(select(func.count()).select_from(Job))
    total = total_result.scalar_one()

    # Status counts using GROUP BY
    status_query = select(Job.status, func.count()).group_by(Job.status)
    status_result = await session.execute(status_query)
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # By company counts using GROUP BY
    company_query = select(Job.company_id, func.count()).group_by(Job.company_id)
    company_result = await session.execute(company_query)
    by_company = {row[0]: row[1] for row in company_result.all()}

    # Score buckets using CASE WHEN aggregation
    score_bucket_query = select(
        func.count().filter(Job.match_score.isnot(None), Job.match_score * 100 < 50).label("bucket_0_49"),
        func.count().filter(Job.match_score.isnot(None), Job.match_score * 100 >= 50, Job.match_score * 100 < 70).label("bucket_50_69"),
        func.count().filter(Job.match_score.isnot(None), Job.match_score * 100 >= 70, Job.match_score * 100 < 80).label("bucket_70_79"),
        func.count().filter(Job.match_score.isnot(None), Job.match_score * 100 >= 80, Job.match_score * 100 < 90).label("bucket_80_89"),
        func.count().filter(Job.match_score.isnot(None), Job.match_score * 100 >= 90).label("bucket_90_100"),
    )
    score_result = await session.execute(score_bucket_query)
    score_row = score_result.one()
    score_buckets = {
        "0-49": score_row.bucket_0_49,
        "50-69": score_row.bucket_50_69,
        "70-79": score_row.bucket_70_79,
        "80-89": score_row.bucket_80_89,
        "90-100": score_row.bucket_90_100,
    }

    # New jobs by day using GROUP BY with date cast
    day_query = select(
        func.date(Job.first_seen).label("day"),
        func.count()
    ).where(Job.first_seen.isnot(None)).group_by(func.date(Job.first_seen))
    day_result = await session.execute(day_query)
    new_jobs_by_day = {str(row[0]): row[1] for row in day_result.all()}

    # Last scan - only fetch one row
    last_scan = (await session.execute(
        select(ScanLog).order_by(ScanLog.completed_at.desc()).limit(1)
    )).scalars().first()

    return StatsOut(
        total_jobs=total,
        new_jobs=status_counts.get("new", 0),
        bookmarked=status_counts.get("bookmarked", 0),
        applied=status_counts.get("applied", 0),
        hidden=status_counts.get("hidden", 0),
        last_scan=last_scan.completed_at if last_scan else None,
        by_company=by_company,
        score_buckets=score_buckets,
        new_jobs_by_day=new_jobs_by_day,
    )
