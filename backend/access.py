"""Who may read or govern a memory. The filters built here go straight into the database queries."""
from datetime import datetime

import db
from errors import Unauthorized
from models import utcnow

ALL_SCOPES = ["successor", "team", "never_transfer"]


def get_person(user_id: str | None) -> dict | None:
    if not user_id:
        return None
    return db.col(db.PEOPLE).find_one({"_id": user_id})


def require_person(user_id: str | None) -> dict:
    person = get_person(user_id)
    if person is None:
        raise Unauthorized("Unknown or missing X-User-Id")
    return person


def default_expert_id() -> str:
    expert = db.col(db.PEOPLE).find_one({"role": "expert"}, sort=[("_id", 1)])
    return expert["_id"] if expert else "u_expert"


def allowed_scopes(viewer: dict | None, owner_id: str) -> list[str]:
    """Scopes of owner_id's memories that viewer may read."""
    if viewer is None:
        return []
    if viewer["_id"] == owner_id:
        return list(ALL_SCOPES)
    if viewer.get("successor_of") == owner_id:
        return ["successor", "team"]
    owner = get_person(owner_id)
    if owner and viewer.get("team") and viewer.get("team") == owner.get("team"):
        return ["team"]
    return []


def readable_filter(viewer: dict | None, owner_id: str, now: datetime | None = None) -> dict:
    """MQL filter for memories of owner_id that viewer may read. Valid as a $vectorSearch filter."""
    return {
        "owner_id": owner_id,
        "status": "active",
        "scope": {"$in": allowed_scopes(viewer, owner_id)},
        "expires_at": {"$gt": now or utcnow()},
    }


def can_read(viewer: dict | None, memory: dict, now: datetime | None = None) -> bool:
    if viewer is None:
        return False
    if viewer["_id"] == memory["owner_id"]:
        return True
    expires = memory.get("expires_at")
    return (
        memory.get("status") == "active"
        and memory.get("scope") in allowed_scopes(viewer, memory["owner_id"])
        and (expires is None or expires > (now or utcnow()))
    )


def can_govern(viewer: dict | None, memory: dict) -> bool:
    """Only the owner may change scope, correct or forget."""
    return viewer is not None and viewer["_id"] == memory["owner_id"]
