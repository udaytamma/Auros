from __future__ import annotations

import re
from typing import Optional, Tuple

import httpx

from ..config import settings
from ..logging import configure_logging
from ..utils.json import safe_json_parse
from ..utils.retry import retry_async


SALARY_PROMPT = """
You are estimating total compensation for a US tech role.
Return ONLY valid JSON with:
{
  "salary_min": int,
  "salary_max": int,
  "confidence": number
}
Rules:
- Use annual base salary in USD.
- confidence is 0.0 to 1.0.
- If you cannot estimate, return null.

Role Title: {title}
Company: {company}
Job Description:
{description}
""".strip()


def extract_salary_from_text(text: str) -> Optional[Tuple[int, int, str, float]]:
    if not text:
        return None

    # Common salary patterns: $150,000 - $200,000, 150k-200k, $150k–$200k
    patterns = [
        r"\$\s?(\d{2,3}(?:,\d{3})?)\s?[-–]\s?\$\s?(\d{2,3}(?:,\d{3})?)",
        r"(\d{2,3})\s?k\s?[-–]\s?(\d{2,3})\s?k",
        r"\$\s?(\d{2,3})\s?k\s?[-–]\s?\$\s?(\d{2,3})\s?k",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        raw_min, raw_max = match.groups()
        min_val = _normalize_salary(raw_min)
        max_val = _normalize_salary(raw_max)
        if min_val and max_val:
            return min_val, max_val, "jd", 0.9

    return None


async def estimate_salary_with_llm(title: str, company: str, description: str) -> Optional[Tuple[int, int, str, float]]:
    prompt = SALARY_PROMPT.format(title=title, company=company, description=description)
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    logger = configure_logging()

    async def _call():
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()

    data = await retry_async(_call, (httpx.HTTPError, TimeoutError))
    raw = data.get("response", "")
    parsed = safe_json_parse(raw)
    if parsed is None:
        logger.warning_structured(
            "llm_salary_parse_failed",
            title=title,
            company=company,
            model=settings.OLLAMA_MODEL,
            raw_response_length=len(raw),
        )
        return None

    salary_min = parsed.get("salary_min")
    salary_max = parsed.get("salary_max")
    confidence = parsed.get("confidence")
    if not isinstance(salary_min, int) or not isinstance(salary_max, int):
        return None
    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    return salary_min, salary_max, "ai", float(confidence)


def apply_confidence_threshold(
    salary_tuple: Optional[Tuple[int, int, str, float]]
) -> Optional[Tuple[int, int, str, float]]:
    if not salary_tuple:
        return None
    _, _, _, confidence = salary_tuple
    if confidence < settings.MIN_SALARY_CONFIDENCE:
        return None
    return salary_tuple


def _normalize_salary(value: str) -> Optional[int]:
    v = value.replace(",", "").lower().strip()
    if v.endswith("k"):
        v = v[:-1]
        try:
            return int(v) * 1000
        except ValueError:
            return None
    try:
        return int(v)
    except ValueError:
        return None
