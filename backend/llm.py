"""Gemini wrapper. Calls are traced in LangSmith when LANGSMITH_TRACING=true.

Free-tier quotas are per key and per model per day. A (key, model) pair that returns 429 (or 503) is benched for
a while and the next one is tried: every key in GOOGLE_API_KEYS for the main model, then the fallback models.
Identical inputs are served from the response cache (cache.py), so rehearsals don't spend quota.
"""
import json
import logging
import time
from typing import TypeVar

from langsmith import traceable
from pydantic import BaseModel

import cache
from config import settings

log = logging.getLogger("handover.llm")
M = TypeVar("M", bound=BaseModel)
_clients: dict[str, object] = {}
_benched: dict[tuple[str, str], float] = {}  # (key, model) -> time it may be retried
BENCH_SECONDS = {429: 3600.0, 500: 120.0, 503: 300.0, 504: 300.0}  # quota, server error, overloaded, deadline


def llm_available() -> bool:
    return bool(settings.GOOGLE_API_KEYS)


def _client(key: str):
    if key not in _clients:
        from google import genai

        from google.genai import types

        # Fail fast instead of waiting on an overloaded model: one attempt, GEMINI_TIMEOUT_S per request.
        _clients[key] = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=int(settings.GEMINI_TIMEOUT_S * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
    return _clients[key]


def _config(system: str | None, temperature: float, **extra):
    from google.genai import types

    return types.GenerateContentConfig(system_instruction=system, temperature=temperature, **extra)


def _attempts() -> list[tuple[str, str]]:
    models = list(dict.fromkeys([settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]))
    chain = [(key, model) for model in models for key in settings.GOOGLE_API_KEYS]
    ready = [a for a in chain if _benched.get(a, 0) <= time.time()]
    return ready or chain[:1]


def _generate(prompt: str, config):
    """generate_content on the first (key, model) with quota left. Returns (response, model)."""
    from google.genai import errors

    if not llm_available():
        raise RuntimeError("GOOGLE_API_KEY is not set")
    last: Exception | None = None
    for key, model in _attempts():
        try:
            return _client(key).models.generate_content(model=model, contents=prompt, config=config), model
        except Exception as exc:
            code = exc.code if isinstance(exc, errors.APIError) else (503 if "timeout" in type(exc).__name__.lower() else None)
            if code not in BENCH_SECONDS:
                raise
            _benched[(key, model)] = time.time() + BENCH_SECONDS[code]
            log.warning("Gemini %s (key ...%s) returned %s, trying the next key/model", model, key[-4:],
                        code if isinstance(exc, errors.APIError) else type(exc).__name__)
            last = exc
    raise last  # every key and model is out of quota


@traceable(run_type="llm", name="gemini_generate_text")
def generate_text(prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
    """Plain text completion. Raises RuntimeError if no GOOGLE_API_KEY (check llm_available() first).
    Identical inputs are served from the response cache (any model in the chain answers the same input)."""
    hit = cache.get("gemini_text", prompt, system, temperature)
    cache.mark_trace(hit is not None)
    if hit is not None:
        return hit
    resp, _ = _generate(prompt, _config(system, temperature))
    text = (resp.text or "").strip()
    cache.put("gemini_text", text, prompt, system, temperature)
    return text


@traceable(run_type="llm", name="gemini_generate_json")
def generate_json(prompt: str, schema: type[M], *, system: str | None = None, temperature: float = 0.1) -> M:
    """Structured output validated against a pydantic model. Cached like generate_text."""
    parts = (prompt, system, temperature, schema.__name__, json.dumps(schema.model_json_schema(), sort_keys=True))
    hit = cache.get("gemini_json", *parts)
    cache.mark_trace(hit is not None)
    if hit is not None:
        try:
            return schema.model_validate_json(hit)
        except ValueError:
            pass  # schema changed since it was stored: ask again
    resp, _ = _generate(
        prompt, _config(system, temperature, response_mime_type="application/json", response_schema=schema)
    )
    result = resp.parsed if isinstance(resp.parsed, schema) else schema.model_validate_json(resp.text or "{}")
    cache.put("gemini_json", result.model_dump_json(), *parts)
    return result
