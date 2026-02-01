from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

import asyncio
import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Company, Job, ScanLog, ScanState
from ..logging import configure_logging, set_correlation_id
from ..metrics import SCANS_RUNNING, SCANS_TOTAL, SCRAPE_ERRORS, JOBS_FOUND, JOBS_NEW
from .scraper import scrape_jobs_with_descriptions, ScrapeError
from .llm import extract_job_info
from .salary import extract_salary_from_text, estimate_salary_with_llm, apply_confidence_threshold
from .scorer import compute_match_score
from .slack import notify_new_job


@dataclass
class ScanContext:
    """Per-scan context to track state without global mutable state."""
    scan_id: str
    started_at: datetime
    companies_scanned: int = 0
    jobs_found: int = 0
    jobs_new: int = 0
    errors: list[str] = field(default_factory=list)


_POTENTIAL_KEYWORDS = [
    "program",
    "tpm",
    "technical program",
    "product manager",
    "platform",
    "infrastructure",
    "infra",
    "ai",
    "ml",
    "reliability",
    "sre",
    "principal",
    "senior",
]


def _compile_patterns(keywords: list[str]) -> list:
    import re

    patterns = []
    for kw in keywords:
        pattern = r"\b" + re.escape(kw).replace("\\ ", r"\s+") + r"\b"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    return patterns


_POTENTIAL_PATTERNS = _compile_patterns(_POTENTIAL_KEYWORDS)


def is_potential_match(title: str) -> bool:
    return any(pattern.search(title) for pattern in _POTENTIAL_PATTERNS)


async def _get_current_scan_state(session: AsyncSession) -> ScanState | None:
    """Get the current scan state from DB."""
    result = await session.execute(select(ScanState).where(ScanState.id == "current"))
    return result.scalars().first()


async def _is_scan_running(session: AsyncSession) -> bool:
    """Check if a scan is currently running (thread-safe DB check)."""
    state = await _get_current_scan_state(session)
    return state is not None and state.status == "running"


async def _reset_scan_state(session: AsyncSession, scan_id: str) -> ScanContext:
    """Initialize scan state in database and return a new ScanContext."""
    started_at = datetime.now(UTC)

    # Get or create the scan state record
    existing = await _get_current_scan_state(session)
    if not existing:
        existing = ScanState(id="current")
        session.add(existing)

    # Reset to running state with new scan_id
    existing.status = "running"
    existing.started_at = started_at
    existing.completed_at = None
    existing.companies_scanned = 0
    existing.jobs_found = 0
    existing.jobs_new = 0
    existing.errors = json.dumps([])

    await session.commit()

    return ScanContext(scan_id=scan_id, started_at=started_at)


async def _update_scan_state(session: AsyncSession, ctx: ScanContext) -> None:
    """Persist current scan context to database."""
    existing = await _get_current_scan_state(session)
    if existing:
        existing.companies_scanned = ctx.companies_scanned
        existing.jobs_found = ctx.jobs_found
        existing.jobs_new = ctx.jobs_new
        existing.errors = json.dumps(ctx.errors)
        await session.commit()


async def _complete_scan_state(session: AsyncSession, ctx: ScanContext) -> None:
    """Mark scan as completed in database."""
    existing = await _get_current_scan_state(session)
    if existing:
        existing.status = "completed"
        existing.completed_at = datetime.now(UTC)
        existing.companies_scanned = ctx.companies_scanned
        existing.jobs_found = ctx.jobs_found
        existing.jobs_new = ctx.jobs_new
        existing.errors = json.dumps(ctx.errors)
        await session.commit()


async def _process_job(
    session: AsyncSession,
    company: Company,
    job_data: dict[str, Any],
    ctx: ScanContext,
) -> bool:
    """
    Process a single job posting.

    Returns True if this was a new job that was added, False otherwise.
    """
    url = job_data["url"]
    title = job_data["title"]
    description = job_data["description"]

    # Check if job already exists
    existing_job = (await session.execute(select(Job).where(Job.url == url))).scalars().first()
    if existing_job:
        # Update last_seen and raw_description if missing
        existing_job.last_seen = datetime.now(UTC)
        if not existing_job.raw_description:
            existing_job.raw_description = description
        await session.commit()
        return False

    # Skip if title doesn't match our criteria
    if not is_potential_match(title):
        return False

    # Extract job information using LLM
    extracted = await extract_job_info(description)
    yoe = extracted.get("yoe_required") or None
    yoe_min = yoe.get("min") if isinstance(yoe, dict) else None
    yoe_max = yoe.get("max") if isinstance(yoe, dict) else None

    work_mode = extracted.get("work_mode")
    location = extracted.get("location")
    primary_function = extracted.get("primary_function")

    # Extract or estimate salary
    salary = extract_salary_from_text(description)
    if not salary:
        salary = await estimate_salary_with_llm(title, company.name, description)
    salary = apply_confidence_threshold(salary)

    salary_min = salary[0] if salary else None
    salary_max = salary[1] if salary else None
    salary_source = salary[2] if salary else None
    salary_confidence = salary[3] if salary else None
    salary_estimated = salary_source == "ai" if salary_source else False

    # Compute match score
    score = compute_match_score(
        title=title,
        description=description,
        yoe_min=yoe_min,
        yoe_max=yoe_max,
        company_tier=company.tier,
        work_mode=work_mode,
    )

    # Create and persist the new job
    new_job = Job(
        id=str(uuid4()),
        company_id=company.id,
        title=title,
        primary_function=primary_function,
        url=url,
        yoe_min=yoe_min,
        yoe_max=yoe_max,
        yoe_source="extracted" if yoe_min or yoe_max else None,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_source=salary_source,
        salary_confidence=salary_confidence,
        salary_estimated=salary_estimated,
        work_mode=work_mode,
        location=location,
        match_score=score,
        raw_description=description,
        status="new",
        notified=False,
    )

    session.add(new_job)
    await session.commit()

    # Send Slack notification if score meets threshold
    if score >= settings.SLACK_MIN_SCORE:
        message = _format_slack_message(company.name, new_job)
        sent = await notify_new_job(message)
        if sent:
            new_job.notified = True
            await session.commit()

    return True


async def _process_company(
    session: AsyncSession,
    company: Company,
    ctx: ScanContext,
    logger: Any,
) -> tuple[int, int]:
    """
    Process a single company - scrape jobs and process each one.

    Returns (jobs_found, jobs_new) for this company.
    """
    jobs_found = 0
    jobs_new = 0

    try:
        logger.info_structured("scan_company_started", company=company.name, url=company.careers_url)
        jobs = await scrape_jobs_with_descriptions(company.careers_url, title_filter=is_potential_match)
        jobs_found = len(jobs)
        JOBS_FOUND.inc(jobs_found)

        # Update company scrape status
        company.scrape_status = "success"
        company.last_scraped = datetime.now(UTC)
        await session.commit()
        logger.info_structured("scan_company_completed", company=company.name, jobs_found=len(jobs))

        # Process each job
        for job_data in jobs:
            is_new = await _process_job(session, company, job_data, ctx)
            if is_new:
                jobs_new += 1
                ctx.jobs_new += 1
                JOBS_NEW.inc()
                await _update_scan_state(session, ctx)

    except (ScrapeError, httpx.HTTPError, asyncio.TimeoutError, SQLAlchemyError) as exc:
        company.scrape_status = "failed"
        company.last_scraped = datetime.now(UTC)
        await session.commit()
        ctx.errors.append(f"{company.name}: {exc}")
        SCRAPE_ERRORS.labels("scrape").inc()
        logger.error_structured("scan_company_failed", company=company.name, error=str(exc), url=company.careers_url)

    return jobs_found, jobs_new


async def get_scan_status(session: AsyncSession) -> dict[str, Any]:
    """Get the current scan status from database."""
    state = await _get_current_scan_state(session)
    if not state:
        return {
            "status": "idle",
            "started_at": None,
            "completed_at": None,
            "companies_scanned": 0,
            "jobs_found": 0,
            "jobs_new": 0,
            "errors": [],
        }

    return {
        "status": state.status,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "companies_scanned": state.companies_scanned or 0,
        "jobs_found": state.jobs_found or 0,
        "jobs_new": state.jobs_new or 0,
        "errors": json.loads(state.errors) if state.errors else [],
    }


async def run_full_scan(session: AsyncSession) -> dict[str, Any]:
    """
    Run a full scan of all enabled companies.

    Uses database-backed state to prevent concurrent scan issues.
    Returns the scan status dict and generates a unique scan_id for tracking.
    """
    # Thread-safe check: is a scan already running?
    if await _is_scan_running(session):
        return await get_scan_status(session)

    logger = configure_logging()

    SCANS_TOTAL.inc()
    SCANS_RUNNING.inc()
    try:
        # Generate unique scan_id and initialize state
        scan_id = str(uuid4())
        set_correlation_id(scan_id[:8])  # Use first 8 chars as correlation ID
        ctx = await _reset_scan_state(session, scan_id)
        logger.info_structured("scan_started", scan_id=scan_id)

        # Get all enabled companies
        companies = (await session.execute(select(Company).where(Company.enabled == True))).scalars().all()  # noqa: E712
        ctx.companies_scanned = len(companies)
        await _update_scan_state(session, ctx)

        # Process each company
        for company in companies:
            jobs_found, _ = await _process_company(session, company, ctx, logger)
            ctx.jobs_found += jobs_found

        # Mark scan as completed
        await _complete_scan_state(session, ctx)

        # Create scan log entry
        scan_log = ScanLog(
            id=scan_id,
            started_at=ctx.started_at,
            completed_at=datetime.now(UTC),
            companies_scanned=ctx.companies_scanned,
            jobs_found=ctx.jobs_found,
            jobs_new=ctx.jobs_new,
            errors=json.dumps(ctx.errors),
        )
        session.add(scan_log)
        await session.commit()
        logger.info_structured(
            "scan_completed",
            scan_id=scan_id,
            companies_scanned=ctx.companies_scanned,
            jobs_found=ctx.jobs_found,
            jobs_new=ctx.jobs_new,
            error_count=len(ctx.errors),
        )

        return await get_scan_status(session)
    finally:
        SCANS_RUNNING.dec()


def _format_slack_message(company: str, job: Job) -> str:
    salary = "Not disclosed"
    if job.salary_min and job.salary_max and job.salary_source:
        salary = f"${job.salary_min//1000}k - ${job.salary_max//1000}k ({job.salary_source})"
    return (
        ":briefcase: *New Job Match Found*\n\n"
        f"*Company:* {company}\n"
        f"*Title:* {job.title}\n"
        f"*Match Score:* {round((job.match_score or 0) * 100)}% :star:\n"
        f"*Salary:* {salary}\n"
        f"*YOE:* {job.yoe_min}-{job.yoe_max} years\n"
        f"*Mode:* {job.work_mode}\n\n"
        f"<{job.url}|View Job Description>"
    )
