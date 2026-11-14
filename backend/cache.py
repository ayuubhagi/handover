"""Response cache in Atlas for paid calls (Gemini, ElevenLabs speech to text).

Rehearsals repeat the same questions and answers, so identical inputs return the stored result instead of spending
quota. The key is the exact input (prompt, system prompt, settings, audio bytes), so anything that changes the input,
like a forgotten or corrected memory feeding /ask, misses the cache and gets a fresh answer. Entries expire through a
TTL index (CACHE_TTL_HOURS), and seed.py does not clear them. Set RESPONSE_CACHE=false to turn it off.
"""
import hashlib
import json
import logging

import db
from config import settings
from models import utcnow

log = logging.getLogger("handover.cache")
COLLECTION = "response_cache"


def _key(kind: str, parts: tuple) -> str:
    raw = json.dumps([kind, *parts], sort_keys=True, default=str, ensure_ascii=False)
    return f"{kind}:{hashlib.sha256(raw.encode()).hexdigest()}"


def get(kind: str, *parts) -> str | None:
    if not settings.RESPONSE_CACHE:
        return None
    try:
        doc = db.col(COLLECTION).find_one({"_id": _key(kind, parts)}, {"value": 1})
    except Exception as exc:  # the cache must never break a request
        log.debug("cache read failed: %s", exc)
        return None
    if doc:
        log.info("cache hit: %s", kind)
    return doc["value"] if doc else None


def put(kind: str, value: str, *parts) -> None:
    if not settings.RESPONSE_CACHE or not value:
        return
    try:
        db.col(COLLECTION).update_one(
            {"_id": _key(kind, parts)},
            {"$set": {"kind": kind, "value": value, "created_at": utcnow()}},
            upsert=True,
        )
    except Exception as exc:
        log.debug("cache write failed: %s", exc)


def mark_trace(hit: bool) -> None:
    """Record on the current LangSmith run whether the result came from the cache."""
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.add_metadata({"cache_hit": hit})
    except Exception:
        pass
