"""Ids, time helpers, API serializers, document builders and request bodies."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field

from config import settings


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def utcnow() -> datetime:
    # Millisecond precision, same as BSON dates.
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=(now.microsecond // 1000) * 1000)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clip_url(clip_id: str | None) -> str | None:
    return f"{settings.PUBLIC_BASE_URL}/clips/{clip_id}" if clip_id else None


def memory_out(doc: dict) -> dict:
    """The Memory object from TEAM.md. Never includes the embedding."""
    return {
        "id": doc["_id"],
        "owner_id": doc["owner_id"],
        "kind": doc["kind"],
        "text": doc["text"],
        "scope": doc["scope"],
        "status": doc["status"],
        "version": int(doc.get("version", 1)),
        "supersedes": doc.get("supersedes"),
        "derived_from": list(doc.get("derived_from") or []),
        "source_clip_id": doc["source_clip_id"],
        "session_id": doc["session_id"],
        "created_at": iso(doc["created_at"]),
        "expires_at": iso(doc["expires_at"]),
    }


def hidden_memory(mem: dict) -> dict:
    """Same Memory shape with the content removed, for viewers who may not read it."""
    return {**mem, "text": "[hidden]"}


def gap_out(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "question": doc["question"],
        "kind": doc["kind"],
        "from_memory_ids": list(doc.get("from_memory_ids") or []),
        "status": doc["status"],
    }


def runbook_out(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "text": doc["text"],
        "derived_from": list(doc.get("derived_from") or []),
        "status": doc["status"],
    }


def audit_out(doc: dict) -> dict:
    return {
        "actor_id": doc["actor_id"],
        "action": doc["action"],
        "memory_ids": list(doc.get("memory_ids") or []),
        "allowed": bool(doc["allowed"]),
        "reason": doc.get("reason", ""),
        "ts": iso(doc["ts"]),
    }


def default_expiry(now: datetime | None = None) -> datetime:
    return (now or utcnow()) + timedelta(days=settings.MEMORY_TTL_DAYS)


def build_memory_doc(
    *,
    owner_id: str,
    kind: str,
    text: str,
    embedding: list[float],
    scope: str,
    source_clip_id: str,
    session_id: str,
    expires_at: datetime | None = None,
    derived_from: list[str] | None = None,
    supersedes: str | None = None,
    version: int = 1,
    memory_id: str | None = None,
    created_at: datetime | None = None,
) -> dict:
    now = created_at or utcnow()
    return {
        "_id": memory_id or new_id("m"),
        "owner_id": owner_id,
        "kind": kind,
        "text": text,
        "embedding": [float(x) for x in embedding],
        "scope": scope,
        "status": "active",
        "version": int(version),
        "supersedes": supersedes,
        "derived_from": list(derived_from or []),
        "source_clip_id": source_clip_id,
        "session_id": session_id,
        "created_at": now,
        "expires_at": expires_at or default_expiry(now),
    }


def build_runbook_step(text: str, derived_from: list[str], order: float, step_id: str | None = None) -> dict:
    now = utcnow()
    return {
        "_id": step_id or new_id("r"),
        "text": text,
        "derived_from": list(derived_from),
        "status": "active",
        "order": float(order),
        "created_at": now,
        "updated_at": now,
    }


def build_gap(owner_id: str, question: str, kind: str, from_memory_ids: list[str],
              session_id: str | None = None, gap_id: str | None = None) -> dict:
    return {
        "_id": gap_id or new_id("g"),
        "owner_id": owner_id,
        "question": question,
        "kind": kind,
        "from_memory_ids": list(from_memory_ids),
        "status": "open",
        "session_id": session_id,
        "created_at": utcnow(),
    }


Scope = Literal["successor", "team", "never_transfer"]


class SessionCreate(BaseModel):
    expert_id: str = "u_expert"
    memory: bool = True  # optional, not in the contract: lets the demo run the interviewer with memory off


class ScopeBody(BaseModel):
    scope: Scope


class CorrectBody(BaseModel):
    text: str = Field(min_length=1)


class AskBody(BaseModel):
    question: str = Field(min_length=1)
    memory: bool = True
