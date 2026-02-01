from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "auros_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "auros_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

REQUEST_IN_PROGRESS = Gauge(
    "auros_http_requests_in_progress",
    "In-progress HTTP requests",
)

SCANS_RUNNING = Gauge(
    "auros_scans_running",
    "Number of scans currently running",
)

SCANS_TOTAL = Counter(
    "auros_scans_total",
    "Total scans started",
)

SCRAPE_ERRORS = Counter(
    "auros_scrape_errors_total",
    "Total scraping errors",
    ["source"],
)

JOBS_FOUND = Counter(
    "auros_jobs_found_total",
    "Total jobs found during scans",
)

JOBS_NEW = Counter(
    "auros_jobs_new_total",
    "Total new jobs added during scans",
)
