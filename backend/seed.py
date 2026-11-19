"""Seed fictional demo data. Run from backend/:  python seed.py

Wipes the handover collections, recreates validators and indexes, then inserts people, session 1 clips,
memories (with Voyage embeddings), runbook steps and the open gaps session 2 should ask about.
Everything here is made up: Northgate Bank, its systems and its clients do not exist.
Content comes from demo/seed_content.py (each memory is a fictional version of a real incident).

Real expert recordings: drop files named after the clip id into backend/seed_audio/
(c_1.mp3, c_2.webm, ...). Clips without a file are seeded with a transcript only.
"""
import logging
import mimetypes
import sys
from datetime import timedelta
from pathlib import Path

import clips
import db
import embeddings
from models import build_gap, build_memory_doc, build_runbook_step, clip_url, utcnow

log = logging.getLogger("handover.seed")
AUDIO_DIR = Path(__file__).resolve().parent / "seed_audio"
EXPERT = "u_expert"
SESSION = "s_1"

PEOPLE = [
    # Ids stay u_expert / u_successor / u_outsider so tokens and DEMO_PASSCODES don't change.
    # Access: Dana (senior) reads everything she owns; Sam (junior, her successor) reads successor + team;
    # Jordan (intern, same team) reads team only. never_transfer stays with Dana.
    {"_id": "u_expert", "name": "Dana", "role": "senior", "team": "payments-ops", "successor_of": None},
    {"_id": "u_successor", "name": "Sam", "role": "junior", "team": "payments-ops", "successor_of": "u_expert"},
    {"_id": "u_outsider", "name": "Jordan", "role": "intern", "team": "payments-ops", "successor_of": None},
]

CLIPS = {
    "c_1": "When the overnight payments batch stalls, restart the payments queue before you touch the ledger "
           "database. If you restart the database first, the batch reloads and every payment in it posts twice. "
           "Then you spend the whole morning reversing them.",
    "c_2": "When a payment gets held by sanctions screening and compliance tells you to push it through by hand, "
           "you re-key it on the LoanDesk backup screen. Almost nobody uses that screen, so nobody remembers this: "
           "the amount field comes pre-filled with zeros. Delete them before you type the amount. "
           "The approvers will look right past it, because the screen looks completely normal.",
    "c_3": "Halvorsen Freight is our touchiest client. Their treasurer, Ingrid, has a standing verbal agreement "
           "that we release their Friday wires up to two million without the second approver. "
           "That is not written down anywhere.",
    "c_4": "Never reuse routing flag R7 for anything new. It used to switch on the old auto-release router. "
           "That code is dead everywhere except PAY-08, which nobody has switched off yet. If R7 gets turned on "
           "and PAY-08 picks up the job, it starts releasing payments on its own. PAY-08 is supposed to be "
           "decommissioned at the end of the month.",
    "c_5": "The reconciliation report from LedgerOne is always wrong on the first business day of the month, "
           "because of a timezone bug. Rerun it after ten a.m. Eastern and it comes out right.",
    "c_6": "For a stalled batch, actually, the first thing I do is check the ledger database locks, clear them, "
           "and only then worry about the queue.",
    "c_7": "On-call escalation goes to the payments ops duty manager first, then to the LedgerOne vendor hotline "
           "if it's still down after thirty minutes. The hotline is useless before then.",
}

# id, clip, kind, scope, text, expires in days (None = default), derived_from
MEMORIES = [
    ("m_1", "c_1", "procedure", "successor",
     "When the overnight payments batch stalls, restart the payments queue before touching the ledger database. "
     "Restarting the database first reloads the batch and every payment posts twice.", None, []),
    ("m_2", "c_2", "procedure", "successor",
     "To push through a payment held by sanctions screening, re-key it on the LoanDesk backup screen. The amount "
     "field there comes pre-filled with zeros: delete them before typing the amount.", None, []),
    ("m_3", "c_2", "workaround", "successor",
     "Approvers routinely miss the pre-filled zeros on the LoanDesk backup screen because the screen looks normal. "
     "Do not rely on the approvers to catch it.", None, []),
    ("m_4", "c_3", "client", "never_transfer",
     "Halvorsen Freight has a verbal agreement with treasurer Ingrid: Friday wires up to 2 million are released "
     "without the second approver. It is not documented anywhere.", None, []),
    ("m_5", "c_4", "system", "team",
     "Never reuse routing flag R7. It used to enable the old auto-release router, and that code still runs on "
     "PAY-08. If R7 is turned on and PAY-08 picks up the job, it releases payments on its own. "
     "PAY-08 is decommissioned at the end of the month.", 21, []),
    ("m_6", "c_5", "workaround", "team",
     "The LedgerOne reconciliation report is wrong on the first business day of each month because of a timezone bug. "
     "Rerun it after 10 a.m. Eastern.", None, []),
    ("m_7", "c_6", "procedure", "successor",
     "For a stalled payments batch, first check and clear the ledger database locks, then deal with the queue.",
     None, []),
    ("m_8", "c_7", "procedure", "team",
     "On-call escalation: payments ops duty manager first, then the LedgerOne vendor hotline if the outage "
     "lasts more than 30 minutes.", None, []),
    ("m_9", "c_2", "procedure", "successor",
     "Backup screen checklist: delete the pre-filled zeros in the amount field, type the amount, and check it "
     "yourself before approval. The approvers will not catch it.", None, ["m_2", "m_3"]),
]

RUNBOOK = [
    ("r_1", "Stalled overnight batch: restart the payments queue before touching the ledger database.", ["m_1"]),
    ("r_2", "Re-keying a held payment on the LoanDesk backup screen: delete the pre-filled zeros in the amount field "
            "and check the amount yourself before approval.", ["m_9"]),
    ("r_3", "First business day of the month: rerun the LedgerOne reconciliation report after 10 a.m. Eastern.", ["m_6"]),
    ("r_4", "Routing flags: never reuse R7 while PAY-08 is still running.", ["m_5"]),
    ("r_5", "Outage over 30 minutes: escalate to the duty manager, then the LedgerOne vendor hotline.", ["m_8"]),
    ("r_6", "Friday wires for Halvorsen Freight: follow the release arrangement agreed with their treasurer.", ["m_4"]),
]

GAPS = [
    ("g_1", "contradiction",
     "You told me to restart the payments queue before touching the ledger database, but you also said you clear "
     "the database locks first. Which one comes first when the batch stalls?", ["m_1", "m_7"]),
    ("g_2", "missing",
     "You said the backup screen pre-fills the amount field with zeros. Is there any way to catch a wrong amount "
     "before the payment actually posts?", ["m_2"]),
]

RESET = [db.PEOPLE, db.CLIPS, db.MEMORIES, db.RUNBOOK, db.GAPS, db.AUDIT, db.SESSIONS,
         "checkpoints", "checkpoint_writes", "clip_audio.files", "clip_audio.chunks"]


def _audio_for(clip_id: str) -> tuple[bytes, str] | tuple[None, str]:
    if AUDIO_DIR.is_dir():
        for path in sorted(AUDIO_DIR.glob(f"{clip_id}.*")):
            ctype = mimetypes.guess_type(path.name)[0] or "audio/mpeg"
            return path.read_bytes(), ctype
    return None, "audio/mpeg"


def seed() -> dict:
    db.ping()
    database = db.get_db()
    # Drop rather than delete_many: a drop emits no per-document delete events, so a running server's
    # change stream never mistakes the reset for TTL expiries. ensure_schema recreates validators and indexes.
    existing = set(database.list_collection_names())
    for name in RESET:
        if name in existing:
            database.drop_collection(name)
    db.ensure_schema(wait_for_search=False)

    db.col(db.PEOPLE).insert_many(PEOPLE)
    now = utcnow()
    db.col(db.SESSIONS).insert_one(
        {"_id": SESSION, "expert_id": EXPERT, "memory_on": True, "status": "closed", "turn": len(CLIPS),
         "created_at": now - timedelta(days=3)}
    )

    with_audio = 0
    for clip_id, transcript in CLIPS.items():
        audio, ctype = _audio_for(clip_id)
        with_audio += bool(audio)
        clips.save_clip(owner_id=EXPERT, session_id=SESSION, transcript=transcript, audio=audio,
                        content_type=ctype, speaker="expert", clip_id=clip_id)

    vectors = embeddings.embed_documents([m[4] for m in MEMORIES])
    docs = _memory_docs(now, vectors)
    db.col(db.MEMORIES).insert_many(docs)

    db.col(db.RUNBOOK).insert_many(
        [build_runbook_step(text, derived, order=i + 1, step_id=rid) for i, (rid, text, derived) in enumerate(RUNBOOK)]
    )
    db.col(db.GAPS).insert_many(
        [build_gap(EXPERT, q, kind, mids, session_id=SESSION, gap_id=gid) for gid, kind, q, mids in GAPS]
    )

    ready = db.wait_for_search_indexes(timeout=240)
    return {"people": len(PEOPLE), "clips": len(CLIPS), "clips_with_audio": with_audio, "memories": len(docs),
            "runbook_steps": len(RUNBOOK), "gaps": len(GAPS), "search_indexes_ready": ready,
            "example_clip_url": clip_url("c_1")}


def _memory_docs(now, vectors: list[list[float]]) -> list[dict]:
    docs = []
    for i, ((mid, clip_id, kind, scope, text, days, derived), vec) in enumerate(zip(MEMORIES, vectors)):
        docs.append(build_memory_doc(
            owner_id=EXPERT, kind=kind, text=text, embedding=vec, scope=scope, source_clip_id=clip_id,
            session_id=SESSION, derived_from=derived, memory_id=mid,
            created_at=now - timedelta(days=3) + timedelta(minutes=i),
            expires_at=(now + timedelta(days=days)) if days else None,
        ))
    return docs


def reset_demo() -> dict:
    """Put the demo data back in place without dropping anything, for POST /demo/reset on a live deploy.

    seed() drops the collections, which also drops the Atlas Search indexes (minutes to rebuild). This instead
    upserts every seeded document over its current state and deletes whatever visitors added, so the indexes
    stay queryable. Order matters for the change stream: runbook steps and gaps are restored before visitor
    memories are deleted, so an expiry cascade for a deleted id never finds a seeded step pointing at it.
    """
    now = utcnow()
    database = db.get_db()
    for person in PEOPLE:
        database[db.PEOPLE].replace_one({"_id": person["_id"]}, person, upsert=True)

    database[db.SESSIONS].delete_many({"_id": {"$ne": SESSION}})
    database[db.SESSIONS].replace_one({"_id": SESSION}, {
        "_id": SESSION, "expert_id": EXPERT, "memory_on": True, "status": "closed", "turn": len(CLIPS),
        "created_at": now - timedelta(days=3)}, upsert=True)

    for clip_id, transcript in CLIPS.items():
        current = database[db.CLIPS].find_one({"_id": clip_id}) or {}
        file_id = current.get("audio_file_id")
        audio, ctype = _audio_for(clip_id)
        if audio and not file_id:  # a forget redacted it: upload the recording again
            file_id = db.audio_bucket().upload_from_stream(clip_id, audio,
                                                           metadata={"content_type": ctype, "clip_id": clip_id})
        database[db.CLIPS].replace_one({"_id": clip_id}, {
            "_id": clip_id, "owner_id": EXPERT, "speaker": "expert", "audio_url": clip_url(clip_id),
            "transcript": transcript, "session_id": SESSION, "audio_file_id": file_id, "content_type": ctype,
            "created_at": current.get("created_at", now)}, upsert=True)
    for extra in database[db.CLIPS].find({"_id": {"$nin": list(CLIPS)}}):
        clips.delete_audio(extra)
    database[db.CLIPS].delete_many({"_id": {"$nin": list(CLIPS)}})

    # Reuse stored embeddings when the text is unchanged; embed only what a forget or correction wiped.
    stored = {d["_id"]: d for d in database[db.MEMORIES].find({"_id": {"$in": [m[0] for m in MEMORIES]}},
                                                               {"text": 1, "embedding": 1})}
    vectors, missing = [], []
    for i, m in enumerate(MEMORIES):
        doc = stored.get(m[0], {})
        ok = doc.get("text") == m[4] and doc.get("embedding")
        vectors.append(doc["embedding"] if ok else None)
        if not ok:
            missing.append(i)
    if missing:
        for i, vec in zip(missing, embeddings.embed_documents([MEMORIES[i][4] for i in missing])):
            vectors[i] = vec
    seed_ids = [m[0] for m in MEMORIES]
    for doc in _memory_docs(now, vectors):
        database[db.MEMORIES].replace_one({"_id": doc["_id"]}, doc, upsert=True)

    for i, (rid, text, derived) in enumerate(RUNBOOK):
        step = build_runbook_step(text, derived, order=i + 1, step_id=rid)
        database[db.RUNBOOK].replace_one({"_id": rid}, step, upsert=True)
    database[db.RUNBOOK].delete_many({"_id": {"$nin": [r[0] for r in RUNBOOK]}})
    for gid, kind, q, mids in GAPS:
        database[db.GAPS].replace_one({"_id": gid}, build_gap(EXPERT, q, kind, mids, session_id=SESSION, gap_id=gid),
                                      upsert=True)
    database[db.GAPS].delete_many({"_id": {"$nin": [g[0] for g in GAPS]}})

    removed = database[db.MEMORIES].delete_many({"_id": {"$nin": seed_ids}}).deleted_count
    database[db.AUDIT].delete_many({})
    return {"memories": len(seed_ids), "visitor_memories_removed": removed, "embedded": len(missing)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = seed()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not result["search_indexes_ready"]:
        print("Search indexes are still building; /ask will use the fallback path until they are queryable.")
        sys.exit(0)
