"""Per-client sliding-window rate limits for the routes that cost money (LLM, speech, embeddings) or change data.

In-process, so it holds per server instance: right for the single-instance public demo. Behind a proxy (Render,
Fly, Railway) set TRUST_PROXY_HEADERS=true so the client IP comes from the first X-Forwarded-For hop.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from config import settings
from errors import HandoverError


class TooManyRequests(HandoverError):
    status_code = 429


_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()
WINDOW_SECONDS = 60.0


def client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, bucket: str, per_minute: int) -> None:
    """Raise 429 if `key` has used `bucket` per_minute times in the last minute."""
    if per_minute <= 0:
        return
    now = time.monotonic()
    with _lock:
        hits = _hits[(bucket, key)]
        while hits and now - hits[0] > WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= per_minute:
            retry = int(WINDOW_SECONDS - (now - hits[0])) + 1
            raise TooManyRequests(f"Too many requests; try again in {retry} s")
        hits.append(now)


def limit(bucket: str, per_minute: int | None = None):
    """FastAPI dependency: Depends(limit("ask"))."""

    def dependency(request: Request) -> None:
        check(client_ip(request), bucket, settings.RATE_LIMIT_PER_MINUTE if per_minute is None else per_minute)

    return dependency


def reset() -> None:
    with _lock:
        _hits.clear()
