"""
Comprehensive tests for the scorer service.

Tests cover edge cases for title scoring, YOE scoring, keyword scoring,
work mode scoring, company tier scoring, and the composite match score.
"""

from api.services.scorer import (
    compute_match_score,
    score_title,
    score_yoe,
    score_keywords,
    score_work_mode,
    score_company_tier,
)


class TestScoreTitle:
    """Tests for score_title function."""

    def test_hits_multiple_keywords(self):
        """Title with multiple keywords should score high."""
        assert score_title("Principal Technical Program Manager") > 0.5

    def test_empty_title(self):
        """Empty title should return 0."""
        assert score_title("") == 0.0

    def test_no_keywords(self):
        """Title without relevant keywords should score 0."""
        assert score_title("Software Engineer") == 0.0

    def test_case_insensitive(self):
        """Title matching should be case insensitive."""
        assert score_title("PRINCIPAL TPM") > 0
        assert score_title("principal tpm") > 0
        assert score_title("Principal TPM") > 0

    def test_single_keyword(self):
        """Single keyword hit should give partial score."""
        score = score_title("Senior Engineer")
        assert 0 < score < 1.0

    def test_three_keywords_maxes_out(self):
        """Three keywords should max out at 1.0."""
        # principal, senior, tpm = 3 hits -> score = min(1.0, 3/3) = 1.0
        score = score_title("Principal Senior TPM Lead")
        assert score == 1.0

    def test_program_manager_keyword(self):
        """'program manager' as multi-word keyword should match."""
        score = score_title("Program Manager")
        assert score > 0

    def test_technical_program_keyword(self):
        """'technical program' as multi-word keyword should match."""
        score = score_title("Technical Program Manager")
        assert score > 0


class TestScoreYoe:
    """Tests for score_yoe function."""

    def test_exact_match(self):
        """YOE range fully within target range should score high."""
        # Range 8-15 fully overlaps with target 8-15
        assert score_yoe(8, 15) == 1.0

    def test_overlap(self):
        """Partial overlap should give partial score."""
        # Range 10-12 has overlap of 2 (10-12) out of span 2, so 1.0
        assert score_yoe(10, 12) > 0.5

    def test_no_overlap_below(self):
        """YOE range below target should score 0."""
        # Range 1-5 has no overlap with 8-15
        assert score_yoe(1, 5) == 0.0

    def test_no_overlap_above(self):
        """YOE range above target should score 0."""
        # Range 20-25 has no overlap with 8-15
        assert score_yoe(20, 25) == 0.0

    def test_none_values(self):
        """Both None values should return default 0.5."""
        assert score_yoe(None, None) == 0.5

    def test_partial_none_min(self):
        """None min with valid max should still compute."""
        # When min is None, it defaults to target_min (8)
        # So effective range is 8-12, full overlap, score should be high
        assert score_yoe(None, 12) > 0

    def test_partial_none_max(self):
        """Valid min with None max should still compute."""
        # When max is None, it defaults to target_max (15)
        # So effective range is 10-15, mostly overlapping
        assert score_yoe(10, None) > 0

    def test_partial_overlap_low(self):
        """Range starting below target should get partial credit."""
        # Range 5-10 overlaps 8-10 (2 years) out of span 5
        score = score_yoe(5, 10)
        assert 0 < score < 1.0

    def test_partial_overlap_high(self):
        """Range extending above target should get partial credit."""
        # Range 12-20 overlaps 12-15 (3 years) out of span 8
        score = score_yoe(12, 20)
        assert 0 < score < 1.0

    def test_single_year_range(self):
        """Single year in range should work."""
        # Range 10-10 has span of 1, overlap of 0 (min=max=10 means overlap calculation may vary)
        score = score_yoe(10, 10)
        # Should be 0/1 = 0 because overlap = max(0, min(10,15) - max(10,8)) = max(0, 10-10) = 0
        assert score == 0.0


class TestScoreKeywords:
    """Tests for score_keywords function."""

    def test_ai_platform_keywords(self):
        """Text with AI/platform keywords should score high."""
        text = "AI platform infrastructure with SRE and observability"
        assert score_keywords(text) > 0.5

    def test_empty_description(self):
        """Empty description should return 0."""
        assert score_keywords("") == 0.0

    def test_no_relevant_keywords(self):
        """Text without relevant keywords should score 0."""
        assert score_keywords("Sales and marketing role") == 0.0

    def test_case_insensitive(self):
        """Keyword matching should be case insensitive."""
        assert score_keywords("AI ML PLATFORM") > 0
        assert score_keywords("ai ml platform") > 0

    def test_multiple_keywords(self):
        """More keywords should increase score."""
        few_keywords = score_keywords("AI platform")
        many_keywords = score_keywords("AI ML platform infrastructure SRE observability cloud")
        assert many_keywords > few_keywords

    def test_five_keywords_maxes_out(self):
        """Five or more keywords should max out at 1.0."""
        text = "AI ML platform infrastructure SRE observability cloud data genai llm"
        assert score_keywords(text) == 1.0

    def test_devops_keyword(self):
        """DevOps keyword should be recognized."""
        assert score_keywords("DevOps practices") > 0

    def test_machine_learning_multiword(self):
        """'machine learning' as multi-word keyword should match."""
        assert score_keywords("machine learning engineer") > 0


class TestScoreWorkMode:
    """Tests for score_work_mode function.

    Note: These tests assume PREFERRED_WORK_MODE is set to 'any' (default).
    When preference is 'any', the function returns 1.0 immediately for ALL inputs.
    """

    def test_any_preference_returns_full_remote(self):
        """When preference is 'any', remote should score 1.0."""
        assert score_work_mode("remote") == 1.0

    def test_any_preference_returns_full_onsite(self):
        """When preference is 'any', onsite should score 1.0."""
        assert score_work_mode("onsite") == 1.0

    def test_any_preference_returns_full_hybrid(self):
        """When preference is 'any', hybrid should score 1.0."""
        assert score_work_mode("hybrid") == 1.0

    def test_none_work_mode_with_any_preference(self):
        """When preference is 'any', even None work mode should score 1.0."""
        # Implementation returns 1.0 early when preference is "any"
        assert score_work_mode(None) == 1.0

    def test_empty_string_work_mode_with_any_preference(self):
        """When preference is 'any', empty string should also score 1.0."""
        # Implementation returns 1.0 early when preference is "any"
        assert score_work_mode("") == 1.0


class TestScoreCompanyTier:
    """Tests for score_company_tier function."""

    def test_tier_1(self):
        """Tier 1 companies should score 1.0."""
        assert score_company_tier(1) == 1.0

    def test_tier_2(self):
        """Tier 2 companies should score 0.8."""
        assert score_company_tier(2) == 0.8

    def test_tier_3(self):
        """Tier 3 companies should score 0.6."""
        assert score_company_tier(3) == 0.6

    def test_tier_4_and_above(self):
        """Tiers above 3 should default to 0.6."""
        assert score_company_tier(4) == 0.6
        assert score_company_tier(5) == 0.6
        assert score_company_tier(100) == 0.6


class TestComputeMatchScore:
    """Tests for compute_match_score function."""

    def test_bounds(self):
        """Match score should always be between 0 and 1."""
        score = compute_match_score(
            title="Principal TPM",
            description="AI platform and reliability",
            yoe_min=10,
            yoe_max=15,
            company_tier=2,
            work_mode="remote",
        )
        assert 0.0 <= score <= 1.0

    def test_all_empty(self):
        """Empty/None values should still produce valid score."""
        score = compute_match_score(
            title="",
            description="",
            yoe_min=None,
            yoe_max=None,
            company_tier=3,
            work_mode=None,
        )
        assert 0.0 <= score <= 1.0

    def test_high_scoring_job(self):
        """Ideal job should score high."""
        score = compute_match_score(
            title="Principal Technical Program Manager",
            description="AI ML platform infrastructure SRE observability cloud",
            yoe_min=8,
            yoe_max=15,
            company_tier=1,
            work_mode="remote",
        )
        assert score > 0.7

    def test_low_scoring_job(self):
        """Non-matching job should score low."""
        score = compute_match_score(
            title="Junior Sales Representative",
            description="Cold calling and lead generation",
            yoe_min=1,
            yoe_max=3,
            company_tier=3,
            work_mode="onsite",
        )
        # With 'any' work mode preference, work_mode still scores 1.0
        # But title=0, keywords=0, yoe=0, tier=0.6
        # Expected: 0*0.3 + 0*0.25 + 0*0.2 + 0.6*0.15 + 1.0*0.1 = 0.09 + 0.1 = 0.19
        assert score < 0.3

    def test_score_is_rounded(self):
        """Score should be rounded to 4 decimal places."""
        score = compute_match_score(
            title="Senior TPM",
            description="Platform work",
            yoe_min=10,
            yoe_max=12,
            company_tier=2,
            work_mode="hybrid",
        )
        # Check that score has at most 4 decimal places
        assert score == round(score, 4)
