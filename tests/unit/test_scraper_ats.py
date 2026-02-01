"""Unit tests for ATS parsing helpers."""

from api.services.scraper import (
    detect_ats,
    _extract_greenhouse_board,
    _extract_lever_company,
    _parse_workday_context,
    _strip_html,
    _extract_workday_postings,
)


def test_detect_ats_greenhouse():
    assert detect_ats("https://boards.greenhouse.io/stripe") == "greenhouse"


def test_detect_ats_lever():
    assert detect_ats("https://jobs.lever.co/datadog") == "lever"


def test_detect_ats_workday():
    assert detect_ats("https://company.wd1.myworkdayjobs.com/en-US/Careers") == "workday"


def test_detect_ats_unknown():
    assert detect_ats("https://example.com/careers") is None


def test_extract_greenhouse_board_from_path():
    assert _extract_greenhouse_board("https://boards.greenhouse.io/stripe") == "stripe"


def test_extract_greenhouse_board_from_job_path():
    assert _extract_greenhouse_board("https://boards.greenhouse.io/stripe/jobs/12345") == "stripe"


def test_extract_greenhouse_board_from_query():
    assert _extract_greenhouse_board("https://boards.greenhouse.io/embed/job_board?for=airbnb") == "airbnb"


def test_extract_lever_company_from_root():
    assert _extract_lever_company("https://jobs.lever.co/datadog") == "datadog"


def test_extract_lever_company_from_job():
    assert _extract_lever_company("https://jobs.lever.co/datadog/abc123") == "datadog"


def test_parse_workday_context_with_locale():
    ctx = _parse_workday_context("https://company.wd1.myworkdayjobs.com/en-US/Careers")
    assert ctx is not None
    assert ctx.tenant == "company"
    assert ctx.site == "Careers"
    assert ctx.locale == "en-US"


def test_parse_workday_context_without_locale():
    ctx = _parse_workday_context("https://company.wd1.myworkdayjobs.com/Careers")
    assert ctx is not None
    assert ctx.site == "Careers"
    assert ctx.locale is None


def test_parse_workday_context_from_api_url():
    ctx = _parse_workday_context("https://company.wd1.myworkdayjobs.com/wday/cxs/company/External/jobs")
    assert ctx is not None
    assert ctx.tenant == "company"
    assert ctx.site == "External"


def test_strip_html():
    raw = "<p>Hello <strong>World</strong></p>"
    assert _strip_html(raw) == "Hello World"


def test_extract_workday_postings_top_level():
    data = {"jobPostings": [{"title": "Role 1"}, {"title": "Role 2"}]}
    postings = _extract_workday_postings(data)
    assert len(postings) == 2


def test_extract_workday_postings_nested():
    data = {"data": {"jobs": [{"title": "Role 1"}]}}
    postings = _extract_workday_postings(data)
    assert len(postings) == 1
