from __future__ import annotations

import re

from ..config import settings


TITLE_WEIGHT = 0.30
KEYWORD_WEIGHT = 0.25
YOE_WEIGHT = 0.20
TIER_WEIGHT = 0.15
WORK_MODE_WEIGHT = 0.10


TITLE_KEYWORDS = [
    "principal",
    "senior",
    "staff",
    "lead",
    "tpm",
    "technical program",
    "program manager",
    "product manager",
]

AI_PLATFORM_KEYWORDS = [
    "ai",
    "ml",
    "machine learning",
    "platform",
    "infrastructure",
    "infra",
    "sre",
    "reliability",
    "observability",
    "cloud",
    "data",
    "genai",
    "llm",
    "ops",
    "devops",
]


def _compile_patterns(keywords: list[str]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for kw in keywords:
        pattern = r"\b" + re.escape(kw).replace("\\ ", r"\s+") + r"\b"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    return patterns


TITLE_PATTERNS = _compile_patterns(TITLE_KEYWORDS)
AI_PATTERNS = _compile_patterns(AI_PLATFORM_KEYWORDS)


def score_title(title: str) -> float:
    hits = 0
    for pattern in TITLE_PATTERNS:
        if pattern.search(title):
            hits += 1
    return min(1.0, hits / 3)


def score_keywords(text: str) -> float:
    hits = 0
    for pattern in AI_PATTERNS:
        if pattern.search(text):
            hits += 1
    return min(1.0, hits / 5)


def score_yoe(yoe_min: int | None, yoe_max: int | None, target_min: int = 8, target_max: int = 15) -> float:
    if yoe_min is None and yoe_max is None:
        return 0.5
    low = yoe_min if yoe_min is not None else target_min
    high = yoe_max if yoe_max is not None else target_max
    overlap = max(0, min(high, target_max) - max(low, target_min))
    span = max(1, high - low)
    return min(1.0, overlap / span)


def score_company_tier(tier: int) -> float:
    if tier == 1:
        return 1.0
    if tier == 2:
        return 0.8
    return 0.6


def score_work_mode(work_mode: str | None) -> float:
    preferred = settings.PREFERRED_WORK_MODE.lower()
    if preferred == "any":
        return 1.0
    if not work_mode:
        return 0.5
    return 1.0 if work_mode.lower() == preferred else 0.2


def compute_match_score(
    title: str,
    description: str,
    yoe_min: int | None,
    yoe_max: int | None,
    company_tier: int,
    work_mode: str | None,
) -> float:
    title_score = score_title(title)
    keyword_score = score_keywords(description)
    yoe_score = score_yoe(yoe_min, yoe_max)
    tier_score = score_company_tier(company_tier)
    work_mode_score = score_work_mode(work_mode)

    total = (
        title_score * TITLE_WEIGHT
        + keyword_score * KEYWORD_WEIGHT
        + yoe_score * YOE_WEIGHT
        + tier_score * TIER_WEIGHT
        + work_mode_score * WORK_MODE_WEIGHT
    )

    return round(max(0.0, min(1.0, total)), 4)
