from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    new = "new"
    bookmarked = "bookmarked"
    applied = "applied"
    hidden = "hidden"


class WorkMode(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"
    unclear = "unclear"


class SalarySource(str, Enum):
    jd = "jd"
    ai = "ai"


class ScanStatus(str, Enum):
    idle = "idle"
    running = "running"
    completed = "completed"


class CompanyOut(BaseModel):
    id: str
    name: str
    careers_url: str
    tier: int
    enabled: bool
    last_scraped: Optional[datetime] = None
    scrape_status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class JobOut(BaseModel):
    id: str
    company_id: str
    title: str
    primary_function: Optional[str] = None
    url: str
    yoe_min: Optional[int] = None
    yoe_max: Optional[int] = None
    yoe_source: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_source: Optional[SalarySource] = None
    salary_confidence: Optional[float] = None
    salary_estimated: Optional[bool] = None
    work_mode: Optional[WorkMode] = None
    location: Optional[str] = None
    match_score: Optional[float] = None
    raw_description: Optional[str] = None
    status: JobStatus
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    notified: bool
    model_config = ConfigDict(from_attributes=True)


class JobListOut(BaseModel):
    jobs: List[JobOut]
    total: int


class JobStatusUpdate(BaseModel):
    status: JobStatus = Field(..., description="new|bookmarked|applied|hidden")


class CompanyUpdate(BaseModel):
    enabled: bool


class ScanStatusOut(BaseModel):
    status: ScanStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    companies_scanned: Optional[int] = None
    jobs_found: Optional[int] = None
    jobs_new: Optional[int] = None
    errors: Optional[list[str]] = None


class StatsOut(BaseModel):
    total_jobs: int
    new_jobs: int
    bookmarked: int
    applied: int
    hidden: int
    last_scan: Optional[datetime] = None
    by_company: dict[str, int]
    score_buckets: dict[str, int]
    new_jobs_by_day: dict[str, int]
