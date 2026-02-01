"""Comprehensive integration tests for Auros API endpoints."""

from fastapi.testclient import TestClient
import pytest


class TestRootEndpoints:
    """Tests for root API endpoints."""

    def test_root(self, client: TestClient):
        """Test the root API endpoint returns service info."""
        resp = client.get("/api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Auros API"


class TestCompanies:
    """Tests for company-related endpoints."""

    def test_list_companies(self, client: TestClient):
        """Test listing all seeded companies."""
        resp = client.get("/companies")
        assert resp.status_code == 200
        companies = resp.json()
        assert len(companies) >= 10

    def test_update_company_enable_disable(self, client: TestClient):
        """Test enabling and disabling a company."""
        # Get a company first
        resp = client.get("/companies")
        companies = resp.json()
        company_id = companies[0]["id"]

        # Disable it
        resp = client.patch(f"/companies/{company_id}", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        # Re-enable it
        resp = client.patch(f"/companies/{company_id}", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_update_company_not_found(self, client: TestClient):
        """Test updating a non-existent company returns 404."""
        resp = client.patch("/companies/nonexistent", json={"enabled": False})
        assert resp.status_code == 404

    def test_company_response_structure(self, client: TestClient):
        """Test that company response has expected fields."""
        resp = client.get("/companies")
        assert resp.status_code == 200
        companies = resp.json()
        assert len(companies) > 0

        company = companies[0]
        expected_fields = ["id", "name", "careers_url", "tier", "enabled"]
        for field in expected_fields:
            assert field in company, f"Missing field: {field}"


class TestJobs:
    """Tests for job-related endpoints."""

    def test_list_jobs_empty(self, client: TestClient):
        """Test listing jobs when database is empty."""
        resp = client.get("/jobs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["jobs"] == []

    def test_list_jobs_with_filters(self, client: TestClient):
        """Test listing jobs with various query filters."""
        resp = client.get("/jobs?status=new&min_score=0.5&limit=10")
        assert resp.status_code == 200
        assert "jobs" in resp.json()
        assert "total" in resp.json()

    def test_list_jobs_with_query_filter(self, client: TestClient):
        """Test listing jobs with a search query."""
        resp = client.get("/jobs?query=engineer")
        assert resp.status_code == 200
        assert "jobs" in resp.json()

    def test_list_jobs_with_company_filter(self, client: TestClient):
        """Test listing jobs filtered by company."""
        resp = client.get("/jobs?company_id=google")
        assert resp.status_code == 200
        assert "jobs" in resp.json()

    def test_list_jobs_pagination(self, client: TestClient):
        """Test listing jobs with pagination."""
        resp = client.get("/jobs?limit=5&offset=0")
        assert resp.status_code == 200
        assert "jobs" in resp.json()
        assert "total" in resp.json()

    def test_get_job_not_found(self, client: TestClient):
        """Test getting a non-existent job returns 404."""
        resp = client.get("/jobs/nonexistent")
        assert resp.status_code == 404

    def test_update_job_status_not_found(self, client: TestClient):
        """Test updating status of a non-existent job returns 404."""
        resp = client.patch("/jobs/missing/status", json={"status": "applied"})
        assert resp.status_code == 404

    def test_update_job_status_invalid(self, client: TestClient):
        """Test updating job with invalid status returns 422."""
        resp = client.patch("/jobs/some-id/status", json={"status": "invalid_status"})
        assert resp.status_code == 422  # Validation error


class TestStats:
    """Tests for statistics endpoint."""

    def test_stats_empty(self, client: TestClient):
        """Test stats endpoint when no jobs exist."""
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_jobs"] == 0
        assert "by_company" in data
        assert "score_buckets" in data
        assert "new_jobs_by_day" in data

    def test_stats_response_structure(self, client: TestClient):
        """Test stats response has all expected fields."""
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()

        expected_fields = [
            "total_jobs",
            "new_jobs",
            "bookmarked",
            "applied",
            "hidden",
            "by_company",
            "score_buckets",
            "new_jobs_by_day",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestSearch:
    """Tests for search/scan endpoints."""

    def test_search_status_idle(self, client: TestClient):
        """Test search status when no scan is running."""
        resp = client.get("/search/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["idle", "completed", "running"]

    def test_trigger_scan(self, client: TestClient):
        """Test triggering a new scan."""
        resp = client.post("/search/trigger")
        assert resp.status_code == 200
        assert resp.json()["status"] in ["started", "running"]

    def test_trigger_scan_while_running(self, client: TestClient):
        """Test triggering scan while another is running."""
        # Trigger first scan
        resp1 = client.post("/search/trigger")
        assert resp1.status_code == 200

        # Try to trigger again - should return running status
        resp2 = client.post("/search/trigger")
        assert resp2.status_code == 200
        # Either "running" (already running) or "started" (if first completed quickly)
        assert resp2.json()["status"] in ["started", "running"]


class TestHealth:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns status for all services."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "db" in data
        assert "ollama" in data
        assert "slack" in data

    def test_health_db_status(self, client: TestClient):
        """Test that database health is ok in test environment."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db"] == "ok"


class TestExport:
    """Tests for export endpoints."""

    def test_export_csv(self, client: TestClient):
        """Test exporting jobs as CSV."""
        resp = client.get("/jobs/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_export_csv_filename(self, client: TestClient):
        """Test exported CSV has correct filename."""
        resp = client.get("/jobs/export/csv")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "auros-jobs.csv" in disposition

    def test_export_csv_headers(self, client: TestClient):
        """Test exported CSV has correct column headers."""
        resp = client.get("/jobs/export/csv")
        assert resp.status_code == 200
        content = resp.text
        first_line = content.split("\n")[0]
        expected_columns = [
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
        ]
        for col in expected_columns:
            assert col in first_line, f"Missing column: {col}"


class TestAuthentication:
    """Tests for API authentication."""

    def test_without_api_key_when_required(self, client: TestClient, monkeypatch):
        """Test that auth works (if API_KEY is set).

        In test env, API_KEY is empty so auth is skipped.
        This test verifies the setup is correct.
        """
        # In test environment, API_KEY is empty, so all endpoints should work
        resp = client.get("/api")
        assert resp.status_code == 200

    def test_all_protected_endpoints_accessible(self, client: TestClient):
        """Test that all protected endpoints are accessible in test mode."""
        # These endpoints require auth in production but should work in test
        endpoints = [
            ("GET", "/companies"),
            ("GET", "/jobs"),
            ("GET", "/stats"),
            ("GET", "/health"),
            ("GET", "/search/status"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path)
            assert resp.status_code in [200, 404], f"Failed for {method} {path}: {resp.status_code}"


class TestMetrics:
    """Tests for metrics endpoint."""

    def test_metrics_endpoint(self, client: TestClient):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
        assert "auros_http_requests_total" in resp.text
