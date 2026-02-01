"""Unit tests for the scraper service."""

import pytest
from api.services.scraper import _looks_like_job_link, _normalize_text, JobLink


class TestLooksLikeJobLink:
    """Tests for the _looks_like_job_link helper function."""

    def test_job_url_pattern(self):
        """Test that URLs with /jobs/ path are recognized."""
        assert _looks_like_job_link("https://company.com/jobs/123", "Software Engineer") is True

    def test_job_singular_url_pattern(self):
        """Test that URLs with /job/ path are recognized."""
        assert _looks_like_job_link("https://company.com/job/456", "Product Manager") is True

    def test_careers_url_pattern(self):
        """Test that URLs with /careers/ path are recognized."""
        assert _looks_like_job_link("https://company.com/careers/engineer", "Engineer") is True

    def test_greenhouse_url(self):
        """Test that Greenhouse URLs are recognized."""
        assert _looks_like_job_link("https://boards.greenhouse.io/company/jobs/123", "TPM") is True

    def test_lever_url(self):
        """Test that Lever URLs are recognized."""
        assert _looks_like_job_link("https://jobs.lever.co/company/123", "Manager") is True

    def test_workday_url(self):
        """Test that Workday URLs are recognized."""
        assert _looks_like_job_link("https://company.workdayjobs.com/en-US/job/123", "Engineer") is True

    def test_privacy_link(self):
        """Test that privacy links are filtered out."""
        assert _looks_like_job_link("https://company.com/privacy", "Privacy Policy") is False

    def test_cookie_link(self):
        """Test that cookie-related links are filtered out."""
        assert _looks_like_job_link("https://company.com/page", "Cookie Settings") is False

    def test_terms_link(self):
        """Test that terms of service links are filtered out."""
        assert _looks_like_job_link("https://company.com/legal", "Terms of Service") is False

    def test_policy_link(self):
        """Test that policy links are filtered out."""
        assert _looks_like_job_link("https://company.com/legal", "Data Policy") is False

    def test_benefits_link(self):
        """Test that benefits page links are filtered out."""
        assert _looks_like_job_link("https://company.com/careers/benefits", "Benefits") is False

    def test_equal_employment_link(self):
        """Test that equal employment links are filtered out."""
        assert _looks_like_job_link("https://company.com/careers", "Equal Employment Opportunity") is False

    def test_title_with_manager(self):
        """Test that titles with 'manager' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Program Manager") is True

    def test_title_with_tpm(self):
        """Test that titles with 'tpm' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Senior TPM") is True

    def test_title_with_principal(self):
        """Test that titles with 'principal' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Principal Engineer") is True

    def test_title_with_senior(self):
        """Test that titles with 'senior' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Senior Developer") is True

    def test_title_with_product(self):
        """Test that titles with 'product' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Product Designer") is True

    def test_title_with_program(self):
        """Test that titles with 'program' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Program Coordinator") is True

    def test_title_with_technical(self):
        """Test that titles with 'technical' are recognized."""
        assert _looks_like_job_link("https://company.com/apply", "Technical Lead") is True

    def test_generic_link_no_keywords(self):
        """Test that generic links without job keywords are filtered."""
        assert _looks_like_job_link("https://company.com/about", "About Us") is False

    def test_url_with_job_in_path(self):
        """Test that URLs containing 'job' anywhere are recognized."""
        assert _looks_like_job_link("https://company.com/open-job-positions", "View Openings") is True

    def test_case_insensitive_url(self):
        """Test that URL matching is case insensitive."""
        assert _looks_like_job_link("https://company.com/JOBS/123", "Role") is True

    def test_case_insensitive_title(self):
        """Test that title matching is case insensitive."""
        assert _looks_like_job_link("https://company.com/apply", "SENIOR MANAGER") is True


class TestNormalizeText:
    """Tests for the _normalize_text helper function."""

    def test_collapses_whitespace(self):
        """Test that multiple whitespace characters are collapsed."""
        result = _normalize_text("Hello    World\n\nNew Line")
        assert result == "Hello World New Line"

    def test_collapses_tabs(self):
        """Test that tabs are normalized to spaces."""
        result = _normalize_text("Hello\t\tWorld")
        assert result == "Hello World"

    def test_collapses_mixed_whitespace(self):
        """Test that mixed whitespace is normalized."""
        result = _normalize_text("Hello  \n\t  World")
        assert result == "Hello World"

    def test_truncates_long_text(self):
        """Test that text longer than 50000 chars is truncated."""
        long_text = "x" * 60000
        result = _normalize_text(long_text)
        assert len(result) == 50000

    def test_does_not_truncate_short_text(self):
        """Test that short text is not truncated."""
        short_text = "x" * 100
        result = _normalize_text(short_text)
        assert len(result) == 100

    def test_empty_text(self):
        """Test handling of empty string."""
        assert _normalize_text("") == ""

    def test_whitespace_only_text(self):
        """Test handling of whitespace-only string."""
        assert _normalize_text("   \n\t   ") == ""

    def test_preserves_words(self):
        """Test that word content is preserved."""
        text = "The quick brown fox jumps over the lazy dog"
        assert _normalize_text(text) == text

    def test_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is handled."""
        result = _normalize_text("   Hello World   ")
        assert result == "Hello World"


class TestJobLink:
    """Tests for the JobLink dataclass."""

    def test_creation(self):
        """Test creating a JobLink instance."""
        link = JobLink(title="Engineer", url="https://example.com/job/1")
        assert link.title == "Engineer"
        assert link.url == "https://example.com/job/1"

    def test_immutable(self):
        """Test that JobLink is immutable (frozen=True)."""
        link = JobLink(title="Engineer", url="https://example.com")
        with pytest.raises(Exception):
            # Frozen dataclass should raise an exception on attribute assignment
            link.title = "New Title"

    def test_equality(self):
        """Test that two JobLinks with same values are equal."""
        link1 = JobLink(title="Engineer", url="https://example.com")
        link2 = JobLink(title="Engineer", url="https://example.com")
        assert link1 == link2

    def test_inequality_different_title(self):
        """Test that JobLinks with different titles are not equal."""
        link1 = JobLink(title="Engineer", url="https://example.com")
        link2 = JobLink(title="Manager", url="https://example.com")
        assert link1 != link2

    def test_inequality_different_url(self):
        """Test that JobLinks with different URLs are not equal."""
        link1 = JobLink(title="Engineer", url="https://example1.com")
        link2 = JobLink(title="Engineer", url="https://example2.com")
        assert link1 != link2

    def test_hashable(self):
        """Test that JobLink is hashable (can be used in sets)."""
        link = JobLink(title="Engineer", url="https://example.com")
        # Should not raise an exception
        link_set = {link}
        assert link in link_set

    def test_hash_equality(self):
        """Test that equal JobLinks have equal hashes."""
        link1 = JobLink(title="Engineer", url="https://example.com")
        link2 = JobLink(title="Engineer", url="https://example.com")
        assert hash(link1) == hash(link2)
