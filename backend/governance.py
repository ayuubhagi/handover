"""Governance: list, re-scope, correct, forget (with its cascade), expiry cascade, runbook, audit, gaps, lineage.

Every change that touches more than one document runs in a single multi-document transaction, and the audit
entry is written inside that same transaction: either the change and its audit record both commit, or neither.
"""
import logging

from langsmith import traceable
from pymongo import ReturnDocument

import access
import audit
import clips
import db
import embeddings
import schemas
from errors import BadRequest, Forbidden, NotFound
from models import audit_out, build_memory_doc, gap_out, iso, memory_out, runbook_out, utcnow

log = logging.getLogger("handover.governance")

NO_EMBEDDING = {"embedding": 0}
FORGOTTEN = "[forgotten]"   # the validator rejects empty text, so content is replaced by tombstones
REMOVED = "[removed]"

_VERBS = {"set_scope": "change the scope of", "correct": "correct", "forget": "forget"}


def _swap(old_id: str, new_id: str) -> dict:
    """Aggregation expression: derived_from with old_id replaced by new_id."""
    return {"$map": {"input": "$derived_from", "as": "d",
                     "in": {"$cond": [{"$eq": ["$$d", old_id]}, new_id, "$$d"]}}}


def _load_for_governance(viewer: dict, memory_id: str, action: str) -> dict:
    """The memory, if viewer owns it. A refused attempt is audited outside any transaction so the record persists."""
    doc = db.col(db.MEMORIES).find_one({"_id": memory_id}, NO_EMBEDDING)
    if doc is None:
        raise NotFound(f"memory {memory_id} not found")
    if not access.can_govern(viewer, doc):
        audit.write_audit(viewer["_id"], action, [memory_id], False,
                          f"{viewer['_id']} is not the owner; only the owner may {_VERBS[action]} a memory")
        raise Forbidden(f"only the owner may {_VERBS[action]} this memory")
    return doc


# ---------- reads ----------

def list_memories(viewer: dict, owner_id: str) -> list[dict]:
    """Owner sees every version and status; anyone else only what readable_filter lets through."""
    is_owner = viewer["_id"] == owner_id
    scopes = access.ALL_SCOPES if is_owner else access.allowed_scopes(viewer, owner_id)
    query = {"owner_id": owner_id} if is_owner else access.readable_filter(viewer, owner_id)
    docs = list(db.col(db.MEMORIES).find(query, NO_EMBEDDING).sort([("created_at", -1), ("_id", 1)])) if scopes else []
    audit.write_audit(
        viewer["_id"], "list_memories", [d["_id"] for d in docs], bool(scopes),
        f"{viewer['_id']} listed {owner_id}'s memories with scopes [{', '.join(scopes) or 'none'}]: {len(docs)} returned",
    )
    return [memory_out(d) for d in docs]


def list_runbook(viewer: dict) -> list[dict]:
    """A step is visible only if every memory it was derived from is readable by the viewer."""
    owner_id = access.default_expert_id()
    readable = access.readable_filter(viewer, owner_id)
    pipeline = [
        {"$match": {"status": {"$ne": "removed"}}},
        # Correlated $lookup: join each source memory by _id, keep it only if it passes the access filter.
        {"$lookup": {"from": db.MEMORIES, "localField": "derived_from", "foreignField": "_id",
                     "pipeline": [{"$match": readable}, {"$project": {"_id": 1}}], "as": "readable"}},
        {"$match": {"$expr": {"$eq": [{"$size": "$readable"}, {"$size": "$derived_from"}]}}},
        {"$sort": {"order": 1}},
        {"$project": {"readable": 0}},
    ]
    # Not audited: the UI refetches on every runbook_changed push and would bury governance entries.
    steps = list(db.col(db.RUNBOOK).aggregate(pipeline))
    return [runbook_out(s) for s in steps]


def list_audit(viewer: dict, limit: int = 20) -> list[dict]:
    """Newest first. Outsiders only see their own entries."""
    limit = max(1, min(20 if limit is None else int(limit), 200))
    query = {"actor_id": viewer["_id"]} if viewer.get("role") == "intern" else {}
    return [audit_out(d) for d in db.col(db.AUDIT).find(query).sort("ts", -1).limit(limit)]


def list_gaps(viewer: dict, owner_id: str) -> list[dict]:
    """Gaps quote unreleased memories, so only the owner sees them."""
    if viewer["_id"] != owner_id:
        return []
    docs = db.col(db.GAPS).find({"owner_id": owner_id}).sort([("created_at", -1), ("_id", 1)])
    return [gap_out(d) for d in docs]


@traceable(name="lineage", run_type="chain")
def lineage(memory_id: str) -> dict:
    """Why does the agent know this: the memories it was derived from (recursively) and its older versions."""
    pipeline = [
        {"$match": {"_id": memory_id}},
        # Walk derived_from upward to the original memories.
        {"$graphLookup": {"from": db.MEMORIES, "startWith": "$derived_from", "connectFromField": "derived_from",
                          "connectToField": "_id", "as": "sources", "depthField": "depth"}},
        # Walk the supersedes chain back to version 1.
        {"$graphLookup": {"from": db.MEMORIES, "startWith": "$supersedes", "connectFromField": "supersedes",
                          "connectToField": "_id", "as": "older_versions", "depthField": "depth"}},
        {"$project": {"embedding": 0, "sources.embedding": 0, "older_versions.embedding": 0}},
    ]
    found = list(db.col(db.MEMORIES).aggregate(pipeline))
    if not found:
        raise NotFound(f"memory {memory_id} not found")
    doc = found[0]
    sources = sorted(doc.pop("sources"), key=lambda d: (d["depth"], d["_id"]))
    older = sorted(doc.pop("older_versions"), key=lambda d: d["depth"])
    every = [doc, *sources, *older]
    return {
        "memory": memory_out(doc),
        "sources": [{**memory_out(d), "depth": int(d["depth"])} for d in sources],
        "older_versions": [memory_out(d) for d in older],
        "clip_ids": sorted({d["source_clip_id"] for d in every}),
    }


# ---------- governance actions ----------

def set_scope(viewer: dict, memory_id: str, scope: str) -> dict:
    if scope not in schemas.SCOPES:
        raise BadRequest(f"scope must be one of {', '.join(schemas.SCOPES)}")
    doc = _load_for_governance(viewer, memory_id, "set_scope")

    def txn(s):
        updated = db.col(db.MEMORIES).find_one_and_update(
            {"_id": memory_id, "status": "active"}, {"$set": {"scope": scope}},
            projection=NO_EMBEDDING, return_document=ReturnDocument.AFTER, session=s,
        )
        if updated is None:
            raise BadRequest("only an active memory can be re-scoped")
        audit.write_audit(viewer["_id"], "set_scope", [memory_id], True,
                          f"scope changed from {doc['scope']} to {scope}",
                          session=s, detail={"from": doc["scope"], "to": scope})
        return updated

    return memory_out(db.run_in_transaction(txn))


def correct_memory(viewer: dict, memory_id: str, text: str) -> dict:
    """Old version -> corrected, new version inserted, every dependent re-pointed to it, in one transaction."""
    text = (text or "").strip()
    if not text:
        raise BadRequest("text must not be empty")
    doc = _load_for_governance(viewer, memory_id, "correct")
    if doc["status"] != "active":
        raise BadRequest(f"only an active memory can be corrected (this one is {doc['status']})")

    # Embedding is a network call: do it before the transaction so the transaction stays short.
    vector = embeddings.embed_documents([text])[0]
    new = build_memory_doc(
        owner_id=doc["owner_id"], kind=doc["kind"], text=text, embedding=vector, scope=doc["scope"],
        source_clip_id=doc["source_clip_id"], session_id=doc["session_id"], expires_at=doc["expires_at"],
        derived_from=doc.get("derived_from"), supersedes=memory_id, version=int(doc["version"]) + 1,
    )
    new_id = new["_id"]

    def txn(s):
        memories, runbook = db.col(db.MEMORIES), db.col(db.RUNBOOK)
        old = memories.find_one_and_update(
            {"_id": memory_id, "status": "active"}, {"$set": {"status": "corrected"}},
            projection=NO_EMBEDDING, return_document=ReturnDocument.AFTER, session=s,
        )
        if old is None:
            raise BadRequest("memory changed while correcting it, try again")
        memories.insert_one(dict(new), session=s)
        # Update with an aggregation pipeline: swap the old id for the new one inside derived_from.
        dependents = memories.update_many(
            {"derived_from": memory_id, "_id": {"$ne": new_id}}, [{"$set": {"derived_from": _swap(memory_id, new_id)}}],
            session=s,
        )
        steps = [d["_id"] for d in runbook.find({"derived_from": memory_id, "status": {"$ne": "removed"}},
                                                {"_id": 1}, session=s)]
        if steps:
            runbook.update_many(
                {"_id": {"$in": steps}},
                [{"$set": {"derived_from": _swap(memory_id, new_id), "status": "needs_review", "updated_at": utcnow()}}],
                session=s,
            )
        audit.write_audit(
            viewer["_id"], "correct", [memory_id, new_id], True,
            f"v{old['version']} corrected to v{new['version']}; {len(steps)} runbook step(s) flagged for review",
            session=s,
            detail={"old_id": memory_id, "new_id": new_id, "runbook_steps_flagged": steps,
                    "dependent_memories_repointed": dependents.modified_count},
        )
        return old

    old = db.run_in_transaction(txn)
    return {"old": memory_out(old), "new": memory_out(new)}


def _blast_radius(memory_id: str) -> tuple[list[str], list[str], list[str]]:
    """(memory ids to forget, runbook step ids to remove, source clip ids) from one aggregation."""
    pipeline = [
        {"$match": {"_id": memory_id}},
        # Every version of this memory: older ones via supersedes, newer ones that supersede it.
        {"$graphLookup": {"from": db.MEMORIES, "startWith": "$supersedes", "connectFromField": "supersedes",
                          "connectToField": "_id", "as": "older_versions"}},
        {"$graphLookup": {"from": db.MEMORIES, "startWith": "$_id", "connectFromField": "_id",
                          "connectToField": "supersedes", "as": "newer_versions"}},
        {"$addFields": {"chain_ids": {"$setUnion": [["$_id"], "$older_versions._id", "$newer_versions._id"]}}},
        # Everything derived from any version, recursively (derived_from is an array, matched per element).
        {"$graphLookup": {"from": db.MEMORIES, "startWith": "$chain_ids", "connectFromField": "_id",
                          "connectToField": "derived_from", "as": "descendants"}},
        {"$addFields": {
            "all_ids": {"$setUnion": ["$chain_ids", "$descendants._id"]},
            "clip_ids": {"$setUnion": [["$source_clip_id"], "$older_versions.source_clip_id",
                                       "$newer_versions.source_clip_id", "$descendants.source_clip_id"]},
        }},
        # Runbook steps built on any of them.
        {"$lookup": {"from": db.RUNBOOK, "let": {"ids": "$all_ids"}, "pipeline": [
            {"$match": {"$expr": {"$and": [
                {"$ne": ["$status", "removed"]},
                {"$gt": [{"$size": {"$setIntersection": ["$derived_from", "$$ids"]}}, 0]},
            ]}}},
            {"$project": {"_id": 1}},
        ], "as": "steps"}},
        {"$project": {"all_ids": 1, "clip_ids": 1, "step_ids": "$steps._id"}},
    ]
    found = list(db.col(db.MEMORIES).aggregate(pipeline))
    if not found:
        raise NotFound(f"memory {memory_id} not found")
    r = found[0]
    ids = [memory_id] + sorted(i for i in r["all_ids"] if i != memory_id)
    return ids, sorted(r["step_ids"]), sorted(r["clip_ids"])


def forget_memory(viewer: dict, memory_id: str) -> dict:
    """Forget a memory, all its versions, everything derived from it, and the runbook steps built on them."""
    _load_for_governance(viewer, memory_id, "forget")
    all_ids, step_ids, clip_ids = _blast_radius(memory_id)

    def txn(s):
        memories = db.col(db.MEMORIES)
        memories.update_many({"_id": {"$in": all_ids}},
                             {"$set": {"status": "forgotten", "text": FORGOTTEN}, "$unset": {"embedding": ""}},
                             session=s)
        if step_ids:
            db.col(db.RUNBOOK).update_many({"_id": {"$in": step_ids}},
                                           {"$set": {"status": "removed", "text": REMOVED, "updated_at": utcnow()}},
                                           session=s)
        gaps = db.col(db.GAPS).delete_many({"from_memory_ids": {"$in": all_ids}}, session=s)
        # A recording is redacted only when no surviving memory still cites it.
        still_used = set(memories.distinct("source_clip_id", {"source_clip_id": {"$in": clip_ids},
                                                              "status": {"$ne": "forgotten"}}, session=s))
        redacted = [c for c in clip_ids if c not in still_used]
        if redacted:
            db.col(db.CLIPS).update_many({"_id": {"$in": redacted}}, {"$set": {"transcript": FORGOTTEN}}, session=s)
        audit_id = audit.write_audit(
            viewer["_id"], "forget", all_ids, True,
            f"forgot {memory_id} and {len(all_ids) - 1} linked memor{'y' if len(all_ids) == 2 else 'ies'}; "
            f"{len(step_ids)} runbook step(s) removed, {len(redacted)} recording(s) redacted",
            session=s,
            detail={"requested_id": memory_id, "runbook_steps_removed": step_ids, "clips_redacted": redacted,
                    "gaps_deleted": gaps.deleted_count},
        )
        return audit_id, redacted

    audit_id, redacted = db.run_in_transaction(txn)
    # GridFS deletes span two collections and cannot be undone, so they run only after the commit.
    for clip in db.col(db.CLIPS).find({"_id": {"$in": redacted}}):
        clips.delete_audio(clip)
    return {"forgotten_ids": all_ids, "runbook_steps_removed": step_ids, "audit_id": audit_id}


def cascade_expired(memory_id: str, pre_image: dict | None = None) -> list[str]:
    """After the TTL index deletes a memory: remove runbook steps built on it, drop its gaps, audit once.
    Safe to call again for the same id (change stream replays)."""

    # Only a real expiry cascades. A delete followed by a re-insert of the same id (a reseed) or a delete of a
    # memory that had not expired yet is not a TTL expiry, so it must not touch runbook steps or gaps.
    if pre_image and pre_image.get("expires_at") and pre_image["expires_at"] > utcnow():
        return []

    def txn(s):
        if db.col(db.MEMORIES).find_one({"_id": memory_id}, {"_id": 1}, session=s):
            return []
        runbook = db.col(db.RUNBOOK)
        steps = [d["_id"] for d in runbook.find({"derived_from": memory_id, "status": {"$ne": "removed"}},
                                                {"_id": 1}, session=s)]
        if steps:
            runbook.update_many({"_id": {"$in": steps}},
                                {"$set": {"status": "removed", "text": REMOVED, "updated_at": utcnow()}}, session=s)
        gaps = db.col(db.GAPS).delete_many({"from_memory_ids": memory_id}, session=s)
        already = db.col(db.AUDIT).find_one({"action": "expire", "memory_ids": memory_id}, {"_id": 1}, session=s)
        if steps or gaps.deleted_count or not already:
            detail = {"runbook_steps_removed": steps, "gaps_deleted": gaps.deleted_count}
            if pre_image:
                detail.update(kind=pre_image.get("kind"), scope=pre_image.get("scope"),
                              expires_at=iso(pre_image.get("expires_at")))
            audit.write_audit("system", "expire", [memory_id], True,
                              f"memory {memory_id} reached expires_at and was deleted by the TTL index; "
                              f"{len(steps)} runbook step(s) removed",
                              session=s, detail=detail)
        return steps

    steps = db.run_in_transaction(txn)
    if steps:
        log.info("expired %s: removed runbook steps %s", memory_id, steps)
    return steps
