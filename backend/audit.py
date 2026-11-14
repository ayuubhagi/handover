"""audit_log: every read and every governance action, who and why."""
import db
from models import new_id, utcnow


def write_audit(actor_id: str, action: str, memory_ids: list[str], allowed: bool, reason: str,
                *, session=None, detail: dict | None = None) -> str:
    """Insert one audit entry. Pass session to commit it inside a transaction."""
    doc = {
        "_id": new_id("a"),
        "actor_id": actor_id,
        "action": action,
        "memory_ids": list(memory_ids),
        "allowed": bool(allowed),
        "reason": reason,
        "ts": utcnow(),
    }
    if detail:
        doc["detail"] = detail
    db.col(db.AUDIT).insert_one(doc, session=session)
    return doc["_id"]
