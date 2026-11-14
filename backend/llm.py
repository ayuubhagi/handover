"""Gemini wrapper. Calls are traced in LangSmith when LANGSMITH_TRACING=true."""
import logging
from typing import TypeVar

from langsmith import traceable
from pydantic import BaseModel

from config import settings

log = logging.getLogger("handover.llm")
M = TypeVar("M", bound=BaseModel)
_client = None


def llm_available() -> bool:
    return bool(settings.GOOGLE_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    return _client


def _config(system: str | None, temperature: float, **extra):
    from google.genai import types

    return types.GenerateContentConfig(system_instruction=system, temperature=temperature, **extra)


@traceable(run_type="llm", name="gemini_generate_text")
def generate_text(prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
    """Plain text completion. Raises RuntimeError if no GOOGLE_API_KEY (check llm_available() first)."""
    if not llm_available():
        raise RuntimeError("GOOGLE_API_KEY is not set")
    resp = _get_client().models.generate_content(
        model=settings.GEMINI_MODEL, contents=prompt, config=_config(system, temperature)
    )
    return (resp.text or "").strip()


@traceable(run_type="llm", name="gemini_generate_json")
def generate_json(prompt: str, schema: type[M], *, system: str | None = None, temperature: float = 0.1) -> M:
    """Structured output validated against a pydantic model."""
    if not llm_available():
        raise RuntimeError("GOOGLE_API_KEY is not set")
    resp = _get_client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=_config(system, temperature, response_mime_type="application/json", response_schema=schema),
    )
    if isinstance(resp.parsed, schema):
        return resp.parsed
    return schema.model_validate_json(resp.text or "{}")
