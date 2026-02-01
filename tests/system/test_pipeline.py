import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from api.models import Company, Job
from api.services import pipeline


@pytest.mark.system
@pytest.mark.asyncio
async def test_run_full_scan_inserts_jobs(monkeypatch, test_app):
    # Set up DB with a single company
    from api.db import SessionLocal

    async with SessionLocal() as session:
        existing = (await session.execute(select(Company))).scalars().all()
        for c in existing:
            c.enabled = False
        await session.commit()

        company = Company(id="testco", name="TestCo", careers_url="https://example.com/jobs")
        session.add(company)
        await session.commit()

        async def fake_scrape(*args, **kwargs):
            return [
                {
                    "title": "Principal Technical Program Manager",
                    "url": "https://example.com/jobs/1",
                    "description": "We are building AI platform infrastructure. Salary $150,000 - $200,000.",
                }
            ]

        async def fake_extract(description):
            return {
                "primary_function": "TPM",
                "yoe_required": {"min": 10, "max": 15},
                "work_mode": "remote",
                "location": "Remote",
                "relevance_score": 0.85,
                "key_requirements": ["AI", "Platform"],
            }

        async def fake_salary(*args, **kwargs):
            return (160000, 210000, "ai", 0.9)

        async def fake_notify(*args, **kwargs):
            return True

        monkeypatch.setattr(pipeline, "scrape_jobs_with_descriptions", fake_scrape)
        monkeypatch.setattr(pipeline, "extract_job_info", fake_extract)
        monkeypatch.setattr(pipeline, "estimate_salary_with_llm", fake_salary)
        monkeypatch.setattr(pipeline, "notify_new_job", fake_notify)

        result = await pipeline.run_full_scan(session)
        assert result["jobs_new"] == 1

        jobs = (await session.execute(select(Job))).scalars().all()
        assert len(jobs) == 1
        assert jobs[0].title.startswith("Principal")
