"""Voyage AI embeddings (voyage-3 family) over plain HTTP."""
import hashlib
import logging
import math
import re

import httpx

from config import settings

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


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    if not texts:
        return []
    if not settings.VOYAGE_API_KEY:
        return [_fallback(t) for t in texts]
    resp = httpx.post(
        f"{settings.VOYAGE_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {settings.VOYAGE_API_KEY}"},
        json={
            "input": texts,
            "model": settings.VOYAGE_MODEL,
            "input_type": input_type,
            "output_dimension": settings.EMBED_DIMS,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda d: d["index"])
    return [[float(x) for x in d["embedding"]] for d in data]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(list(texts), "document")


def embed_query(text: str) -> list[float]:
    return _embed([text], "query")[0]
