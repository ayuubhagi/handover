"""Seed fictional demo data. Run from backend/:  python seed.py

Wipes the handover collections, recreates validators and indexes, then inserts people, session 1 clips,
memories (with Voyage embeddings), runbook steps and the open gaps session 2 should ask about.
Everything here is made up: Northgate Bank, its systems and its clients do not exist.

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
    {"_id": "u_expert", "name": "Dana", "role": "expert", "team": "payments-ops", "successor_of": None},
    {"_id": "u_successor", "name": "Sam", "role": "successor", "team": "payments-ops", "successor_of": "u_expert"},
    {"_id": "u_outsider", "name": "Riley", "role": "outsider", "team": "retail-marketing", "successor_of": None},
]

CLIPS = {
    "c_1": "When the overnight payments batch stalls, restart the payments queue before touching the database. "
           "If you touch the ledger database first you get duplicate postings and a very long morning.",
    "c_2": "The SWIFT queue backs up most month ends. The alert fires at five thousand messages but honestly "
           "you don't need to act until it passes eight thousand. Drain it with the swift-drain job on OPS-BATCH-02.",
    "c_3": "Halvorsen Freight is our touchiest client. Their treasurer, Ingrid, has a standing verbal agreement "
           "that we release their Friday wires up to two million without the second approver. That is not written anywhere.",
    "c_4": "The reconciliation report from LedgerOne is always wrong on the first business day of the month "
           "because of a timezone bug. Rerun it after ten a.m. Eastern and it comes out right.",
    "c_5": "FaxBridge is the old fax gateway for wire confirmations. It gets switched off at the end of this month, "
           "so until then, if a confirmation is missing, check the FaxBridge spool folder.",
    "c_6": "For a stalled batch, actually the first thing I do is check the ledger database locks, "
           "clear them, and only then worry about the queue.",
    "c_7": "On call escalation goes to the payments ops duty manager first, then to the vendor hotline for LedgerOne "
           "if it is still down after thirty minutes.",
}

# id, clip, kind, scope, text, expires in days (None = default), derived_from
MEMORIES = [
    ("m_1", "c_1", "procedure", "successor",
     "When the overnight payments batch stalls, restart the payments queue before touching the ledger database. "
     "Touching the database first causes duplicate postings.", None, []),
    ("m_2", "c_2", "system", "team",
     "The SWIFT queue backs up at month end. The alert fires at 5,000 messages but action is only needed above 8,000.",
     None, []),
    ("m_3", "c_2", "procedure", "successor",
     "Drain a backed up SWIFT queue by running the swift-drain job on OPS-BATCH-02.", None, []),
    ("m_4", "c_3", "client", "never_transfer",
     "Halvorsen Freight has a verbal agreement with treasurer Ingrid: Friday wires up to 2 million are released "
     "without the second approver. It is not documented anywhere.", None, []),
    ("m_5", "c_4", "workaround", "successor",
     "The LedgerOne reconciliation report is wrong on the first business day of each month because of a timezone bug. "
     "Rerun it after 10 a.m. Eastern.", None, []),
    ("m_6", "c_5", "system", "team",
     "FaxBridge is the legacy fax gateway for wire confirmations and is being retired at the end of the month. "
     "Until then, look for missing confirmations in the FaxBridge spool folder.", 21, []),
    ("m_7", "c_6", "procedure", "successor",
     "For a stalled payments batch, first check and clear the ledger database locks, then deal with the queue.",
     None, []),
    ("m_8", "c_7", "procedure", "team",
     "On call escalation: payments ops duty manager first, then the LedgerOne vendor hotline if the outage "
     "lasts more than 30 minutes.", None, []),
    ("m_9", "c_2", "procedure", "successor",
     "Month end SWIFT playbook: ignore the 5,000 message alert, act above 8,000, and drain the queue with "
     "swift-drain on OPS-BATCH-02.", None, ["m_2", "m_3"]),
]

RUNBOOK = [
    ("r_1", "Stalled overnight batch: restart the payments queue before touching the ledger database.", ["m_1"]),
    ("r_2", "Month end: when the SWIFT queue passes 8,000 messages, run swift-drain on OPS-BATCH-02.", ["m_9"]),
    ("r_3", "First business day of the month: rerun the LedgerOne reconciliation report after 10 a.m. Eastern.", ["m_5"]),
    ("r_4", "Missing wire confirmation: check the FaxBridge spool folder.", ["m_6"]),
    ("r_5", "Outage over 30 minutes: escalate to the duty manager, then the LedgerOne vendor hotline.", ["m_8"]),
    ("r_6", "Friday wires for Halvorsen Freight: follow the release arrangement agreed with their treasurer.", ["m_4"]),
]

GAPS = [
    ("g_1", "contradiction",
     "You told me to restart the payments queue before touching the ledger database, but you also said you clear "
     "the database locks first. Which one comes first when the batch stalls?", ["m_1", "m_7"]),
    ("g_2", "missing",
     "You mentioned the swift-drain job on OPS-BATCH-02. Who has access to run it, and what do you do if it fails?",
     ["m_3"]),
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
    existing = set(database.list_collection_names())
    for name in RESET:
        if name in existing:
            database[name].delete_many({})
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
    docs = []
    for i, ((mid, clip_id, kind, scope, text, days, derived), vec) in enumerate(zip(MEMORIES, vectors)):
        created = now - timedelta(days=3) + timedelta(minutes=i)
        docs.append(build_memory_doc(
            owner_id=EXPERT, kind=kind, text=text, embedding=vec, scope=scope, source_clip_id=clip_id,
            session_id=SESSION, derived_from=derived, memory_id=mid, created_at=created,
            expires_at=(now + timedelta(days=days)) if days else None,
        ))
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = seed()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not result["search_indexes_ready"]:
        print("Search indexes are still building; /ask will use the fallback path until they are queryable.")
        sys.exit(0)
