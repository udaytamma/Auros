from __future__ import annotations

from typing import Any

from lama import OllamaClient
from lama.exceptions import LamaError

from ..config import settings
from ..logging import configure_logging
from ..utils.json import safe_json_parse

# Module-level client reference, set during app lifespan
_client: OllamaClient | None = None


def set_ollama_client(client: OllamaClient) -> None:
    """Called from app lifespan to inject the shared client."""
    global _client  # noqa: PLW0603
    _client = client


def get_ollama_client() -> OllamaClient:
    """Get the shared OllamaClient. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("OllamaClient not initialized -- call set_ollama_client() during app startup")
    return _client


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
    logger = configure_logging()
    client = get_ollama_client()
    prompt = EXTRACTION_PROMPT.format(job_description=job_description)

    try:
        data = await client.generate(
            settings.OLLAMA_MODEL,
            prompt,
            format="json",
        )
    except LamaError as exc:
        logger.warning_structured(
            "llm_extract_failed",
            model=settings.OLLAMA_MODEL,
            error=str(exc),
        )
        return {
            "primary_function": "Other",
            "yoe_required": None,
            "work_mode": "unclear",
            "location": "Unknown",
            "relevance_score": 0.0,
            "key_requirements": [],
        }

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
