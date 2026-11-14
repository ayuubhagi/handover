"""Gemini wrapper. Calls are traced in LangSmith when LANGSMITH_TRACING=true.

Free-tier quotas are per model per day, so a model that returns 429 (or 503) is skipped for a while and
the next one in GEMINI_FALLBACK_MODELS is used.
"""
import logging
import time
from typing import TypeVar

from langsmith import traceable
from pydantic import BaseModel

from config import settings

log = logging.getLogger("handover.llm")
M = TypeVar("M", bound=BaseModel)
_client = None
_benched: dict[str, float] = {}  # model -> time it may be retried
BENCH_SECONDS = {429: 3600.0, 503: 60.0}


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


def _models() -> list[str]:
    chain = list(dict.fromkeys([settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]))
    ready = [m for m in chain if _benched.get(m, 0) <= time.time()]
    return ready or chain[:1]


def _generate(prompt: str, config):
    """generate_content on the first model with quota left. Returns (response, model)."""
    from google.genai import errors

    if not llm_available():
        raise RuntimeError("GOOGLE_API_KEY is not set")
    last: Exception | None = None
    for model in _models():
        try:
            return _get_client().models.generate_content(model=model, contents=prompt, config=config), model
        except errors.APIError as exc:
            if exc.code not in BENCH_SECONDS:
                raise
            _benched[model] = time.time() + BENCH_SECONDS[exc.code]
            log.warning("Gemini %s returned %s, falling back to the next model", model, exc.code)
            last = exc
    raise last  # every model is out of quota


@traceable(run_type="llm", name="gemini_generate_text")
def generate_text(prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
    """Plain text completion. Raises RuntimeError if no GOOGLE_API_KEY (check llm_available() first)."""
    resp, _ = _generate(prompt, _config(system, temperature))
    return (resp.text or "").strip()


@traceable(run_type="llm", name="gemini_generate_json")
def generate_json(prompt: str, schema: type[M], *, system: str | None = None, temperature: float = 0.1) -> M:
    """Structured output validated against a pydantic model."""
    resp, _ = _generate(
        prompt, _config(system, temperature, response_mime_type="application/json", response_schema=schema)
    )
    if isinstance(resp.parsed, schema):
        return resp.parsed
    return schema.model_validate_json(resp.text or "{}")
