"""Voyage AI embeddings (voyage-3 family) over plain HTTP."""
import hashlib
import logging
import math
import re
import time
from functools import lru_cache

import httpx

from config import settings
from errors import HandoverError


class EmbeddingUnavailable(HandoverError):
    status_code = 503

log = logging.getLogger("handover.embeddings")
_warned = False


def _fallback(text: str) -> list[float]:
    """Deterministic hashed bag of words. Dev only, used when VOYAGE_API_KEY is missing."""
    global _warned
    if not _warned:
        log.warning("VOYAGE_API_KEY not set: using hashed dev embeddings, not real semantic search")
        _warned = True
    vec = [0.0] * settings.EMBED_DIMS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % settings.EMBED_DIMS] += 1.0 if (h >> 64) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _post(payload: dict) -> httpx.Response:
    """POST with backoff on 429/5xx (free Voyage accounts allow only a few requests per minute)."""
    delay = 2.0
    for attempt in range(6):
        try:
            resp = httpx.post(
                f"{settings.VOYAGE_BASE_URL}/embeddings",
                headers={"Authorization": f"Bearer {settings.VOYAGE_API_KEY}"},
                json=payload,
                timeout=30,
            )
        except httpx.TransportError as exc:
            if attempt == 5:
                raise EmbeddingUnavailable(f"Voyage AI unreachable: {exc}") from exc
            time.sleep(delay)
            delay = min(delay * 2, 20)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == 5:
                break
            wait = float(resp.headers.get("retry-after") or delay)
            log.warning("Voyage AI returned %s, retrying in %.0fs", resp.status_code, wait)
            time.sleep(min(wait, 25))
            delay = min(delay * 2, 20)
            continue
        resp.raise_for_status()
        return resp
    raise EmbeddingUnavailable("Voyage AI is rate limiting requests; try again in a minute")


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    if not texts:
        return []
    if not settings.VOYAGE_API_KEY:
        return [_fallback(t) for t in texts]
    resp = _post({
        "input": texts,
        "model": settings.VOYAGE_MODEL,
        "input_type": input_type,
        "output_dimension": settings.EMBED_DIMS,
    })
    data = sorted(resp.json()["data"], key=lambda d: d["index"])
    return [[float(x) for x in d["embedding"]] for d in data]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(list(texts), "document")


@lru_cache(maxsize=512)
def _embed_query_cached(text: str) -> tuple[float, ...]:
    return tuple(_embed([text], "query")[0])


def embed_query(text: str) -> list[float]:
    # Cached: the demo asks the same questions as successor, outsider and memory off.
    return list(_embed_query_cached(text.strip()))
