"""LLM provider chain: Groq first (fast, generous free tier), Gemini as fallback.

Every caller uses three functions: llm_available(), generate_text() and generate_json(). Each request walks the
chain of (provider, key, model) attempts in LLM_PROVIDERS order. An attempt that hits a quota (429), an overloaded
model (503) or a timeout is benched for a while and the next one is tried, so one exhausted free tier never takes
the app down. Identical inputs are served from the response cache (cache.py) whichever model first answered them.
Calls are traced in LangSmith when LANGSMITH_TRACING=true.
"""
import copy
import json
import logging
import time
from typing import Callable, TypeVar

import httpx
from langsmith import traceable
from pydantic import BaseModel

import cache
from config import settings

log = logging.getLogger("handover.llm")
M = TypeVar("M", bound=BaseModel)
BENCH_SECONDS = {429: 3600.0, 500: 120.0, 502: 120.0, 503: 300.0, 504: 300.0}  # quota, server error, overloaded
_benched: dict[tuple[str, str, str], float] = {}  # (provider, key, model) -> time it may be retried


class _Retryable(Exception):
    def __init__(self, code: int, detail: str = ""):
        super().__init__(f"{code} {detail}".strip())
        self.code = code


# ---------------------------------------------------------------- Groq (OpenAI-compatible chat completions)

def strict_schema(schema: dict) -> dict:
    """Pydantic JSON schema -> the form strict structured outputs require: $refs inlined, every property listed
    in `required` (optional ones stay nullable through their anyOf null), additionalProperties false."""
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
        out = {k: walk(v) for k, v in node.items() if k not in ("$defs", "title", "default")}
        if out.get("type") == "object" and "properties" in out:
            out["required"] = list(out["properties"])
            out["additionalProperties"] = False
        return out

    return walk(schema)


def _groq(key: str, model: str, prompt: str, system: str | None, temperature: float,
          schema: type[BaseModel] | None) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body: dict = {"model": model, "messages": messages, "temperature": temperature}
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"  # these are reasoning models; low keeps voice turns snappy
    if schema is not None:
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": schema.__name__.strip("_") or "result", "strict": True,
            "schema": strict_schema(schema.model_json_schema())}}
    try:
        resp = httpx.post(f"{settings.GROQ_BASE_URL}/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {key}"}, timeout=settings.LLM_TIMEOUT_S)
    except httpx.TimeoutException as exc:
        raise _Retryable(504, "timeout") from exc
    except httpx.TransportError as exc:
        raise _Retryable(503, str(exc)) from exc
    if resp.status_code in BENCH_SECONDS:
        raise _Retryable(resp.status_code, resp.text[:200])
    resp.raise_for_status()
    return (resp.json()["choices"][0]["message"].get("content") or "").strip()


# ---------------------------------------------------------------- Gemini (google-genai)

_gemini_clients: dict[str, object] = {}


def _gemini(key: str, model: str, prompt: str, system: str | None, temperature: float,
            schema: type[BaseModel] | None) -> str:
    from google import genai
    from google.genai import errors, types

    if key not in _gemini_clients:
        _gemini_clients[key] = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=int(settings.LLM_TIMEOUT_S * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
    extra = {"response_mime_type": "application/json", "response_schema": schema} if schema else {}
    config = types.GenerateContentConfig(system_instruction=system, temperature=temperature, **extra)
    try:
        resp = _gemini_clients[key].models.generate_content(model=model, contents=prompt, config=config)
    except errors.APIError as exc:
        if exc.code in BENCH_SECONDS:
            raise _Retryable(exc.code, str(exc)[:200]) from exc
        raise
    except Exception as exc:
        if "timeout" in type(exc).__name__.lower():
            raise _Retryable(504, "timeout") from exc
        raise
    if schema is not None and isinstance(resp.parsed, schema):
        return resp.parsed.model_dump_json()
    return (resp.text or "").strip()


# ---------------------------------------------------------------- the chain

_CALLERS: dict[str, Callable] = {"groq": _groq, "gemini": _gemini}


def _provider_chain() -> list[tuple[str, str, str]]:
    chain = []
    for provider in settings.LLM_PROVIDERS:
        if provider == "groq":
            models, keys = [settings.GROQ_MODEL, *settings.GROQ_FALLBACK_MODELS], settings.GROQ_API_KEYS
        elif provider == "gemini":
            models, keys = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS], settings.GOOGLE_API_KEYS
        else:
            continue
        chain += [(provider, key, model) for model in dict.fromkeys(models) for key in keys]
    return chain


_budget = {"day": "", "used": 0}


def _budget_left() -> bool:
    """LLM_DAILY_BUDGET caps provider calls per UTC day (cache hits are free). 0 means no cap."""
    if settings.LLM_DAILY_BUDGET <= 0:
        return True
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _budget["day"] != today:
        _budget.update(day=today, used=0)
    return _budget["used"] < settings.LLM_DAILY_BUDGET


def llm_available() -> bool:
    """False with no key, or once today's budget is spent: callers then take their non-LLM fallback path."""
    return bool(_provider_chain()) and _budget_left()


def _attempts() -> list[tuple[str, str, str]]:
    chain = _provider_chain()
    ready = [a for a in chain if _benched.get(a, 0) <= time.time()]
    return ready or chain[:1]


def _complete(prompt: str, system: str | None, temperature: float, schema: type[BaseModel] | None) -> str:
    if not _provider_chain():
        raise RuntimeError("No LLM key set: add GROQ_API_KEY (or GOOGLE_API_KEY) to .env")
    if not _budget_left():
        raise RuntimeError("LLM_DAILY_BUDGET reached for today")
    _budget["used"] += 1
    last: Exception | None = None
    for attempt in _attempts():
        provider, key, model = attempt
        try:
            text = _CALLERS[provider](key, model, prompt, system, temperature, schema)
            if schema is not None:
                schema.model_validate_json(text)  # a malformed reply falls through to the next model
            return text
        except _Retryable as exc:
            _benched[attempt] = time.time() + BENCH_SECONDS.get(exc.code, 300.0)
            log.warning("%s %s (key ...%s) returned %s, trying the next one", provider, model, key[-4:], exc.code)
            last = exc
        except ValueError as exc:  # schema validation failed: don't bench, just try the next model
            log.warning("%s %s returned output that doesn't match %s", provider, model, schema.__name__)
            last = exc
    raise RuntimeError(f"every LLM provider failed: {last}")


@traceable(run_type="llm", name="llm_generate_text")
def generate_text(prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
    """Plain text completion. Raises RuntimeError if no key is set (check llm_available() first)."""
    hit = cache.get("llm_text", prompt, system, temperature)
    cache.mark_trace(hit is not None)
    if hit is not None:
        return hit
    text = _complete(prompt, system, temperature, None)
    cache.put("llm_text", text, prompt, system, temperature)
    return text


@traceable(run_type="llm", name="llm_generate_json")
def generate_json(prompt: str, schema: type[M], *, system: str | None = None, temperature: float = 0.1) -> M:
    """Structured output validated against a pydantic model. Cached like generate_text."""
    parts = (prompt, system, temperature, schema.__name__, json.dumps(schema.model_json_schema(), sort_keys=True))
    hit = cache.get("llm_json", *parts)
    cache.mark_trace(hit is not None)
    if hit is not None:
        try:
            return schema.model_validate_json(hit)
        except ValueError:
            pass  # schema changed since it was stored: ask again
    result = schema.model_validate_json(_complete(prompt, system, temperature, schema))
    cache.put("llm_json", result.model_dump_json(), *parts)
    return result
