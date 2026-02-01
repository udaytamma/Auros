from __future__ import annotations

from typing import Any

import httpx

from ..config import settings
from ..logging import configure_logging
from ..utils.json import safe_json_parse
from ..utils.retry import retry_async


EXTRACTION_PROMPT = """
You are extracting structured information from a job description.
Return ONLY valid JSON with these fields:
{{
  "primary_function": "TPM|PM|Platform|SRE|AI/ML|Other",
  "yoe_required": {{"min": int, "max": int}} | null,
  "work_mode": "remote|hybrid|onsite|unclear",
  "location": string,
  "relevance_score": number,
  "key_requirements": [string, ...]
}}

Rules:
- relevance_score is 0.0 to 1.0 for Principal TPM targeting AI/Platform roles.
- If YOE not specified, return null.
- If location not specified, return "Unknown".
- Use "unclear" for work_mode if not explicit.

Job Description:
{job_description}
""".strip()


async def extract_job_info(job_description: str) -> dict[str, Any]:
    prompt = EXTRACTION_PROMPT.format(job_description=job_description)
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
            "llm_extract_failed",
            model=settings.OLLAMA_MODEL,
            raw_response_length=len(raw),
        )
        return {
            "primary_function": "Other",
            "yoe_required": None,
            "work_mode": "unclear",
            "location": "Unknown",
            "relevance_score": 0.0,
            "key_requirements": [],
        }

    return parsed
