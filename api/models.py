from __future__ import annotations

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    careers_url: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=2)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    scrape_status: Mapped[str | None] = mapped_column(String, nullable=True)

    jobs: Mapped[list[Job]] = relationship("Job", back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    primary_function: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    yoe_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yoe_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yoe_source: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_source: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="new")
    first_seen: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped[Company] = relationship("Company", back_populates="jobs")


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    companies_scanned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jobs_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jobs_new: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanState(Base):
    __tablename__ = "scan_state"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    started_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    companies_scanned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jobs_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jobs_new: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_jobs_company_status", Job.company_id, Job.status)
