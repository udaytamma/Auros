from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("careers_url", sa.String(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_scraped", sa.DateTime(), nullable=True),
        sa.Column("scrape_status", sa.String(), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.String(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("primary_function", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("yoe_min", sa.Integer(), nullable=True),
        sa.Column("yoe_max", sa.Integer(), nullable=True),
        sa.Column("yoe_source", sa.String(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_source", sa.String(), nullable=True),
        sa.Column("salary_confidence", sa.Float(), nullable=True),
        sa.Column("salary_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("work_mode", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="new"),
        sa.Column("first_seen", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_jobs_company_status", "jobs", ["company_id", "status"])
    op.create_index("ix_jobs_url", "jobs", ["url"], unique=True)

    op.create_table(
        "scan_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("companies_scanned", sa.Integer(), nullable=True),
        sa.Column("jobs_found", sa.Integer(), nullable=True),
        sa.Column("jobs_new", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Text(), nullable=True),
    )

    op.create_table(
        "scan_state",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("companies_scanned", sa.Integer(), nullable=True),
        sa.Column("jobs_found", sa.Integer(), nullable=True),
        sa.Column("jobs_new", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scan_state")
    op.drop_table("scan_logs")
    op.drop_index("ix_jobs_url", table_name="jobs")
    op.drop_index("ix_jobs_company_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("companies")
