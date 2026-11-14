"""The interview agent: a LangGraph loop recall -> ask -> listen -> extract -> detect, checkpointed in Atlas."""
import logging
from datetime import timedelta
from typing import TypedDict

from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import traceable

import db
import detection
import embeddings
import errors
import extraction
import llm
import models
from audit import write_audit
from config import settings

log = logging.getLogger("handover.interview")

STOCK_QUESTIONS = [
    "Tell me about the system you worry about most when you are not here.",
    "Who do you call when something breaks outside office hours, and what do they need to know?",
    "What happens at month end that a newcomer would not expect?",
    "Which vendors or outside contacts does your work depend on, and how do you reach them?",
    "What is a workaround you use that is not written down anywhere?",
    "Which clients need special handling, and what is the arrangement?",
    "What would you check first on a Monday morning, and why?",
    "If you could leave one warning for your successor, what would it be?",
]

FOLLOWUP_SYSTEM = (
    "You are interviewing a retiring expert so a successor can inherit what they know. "
    "Ask ONE short, spoken question about something not yet covered. Good topics: on-call and escalation, "
    "vendors, month-end routines, undocumented workarounds. Never repeat a question already asked. "
    "Output only the question."
)


class State(TypedDict, total=False):
    session_id: str
    expert_id: str
    memory_on: bool
    turn: int
    question: str
    current_gap_id: str | None
    used_memory_ids: list[str]
    transcript: str
    clip_id: str
    new_memory_ids: list[str]
    new_gap_ids: list[str]
    history: list[dict]
    open_gaps: list[dict]  # set by recall: JSON-simple copies of open gap docs
    recent: list[dict]  # set by recall: [{"id", "text"}]


def recall(state: State) -> dict:
    if not state.get("memory_on"):
        return {"open_gaps": [], "recent": []}
    expert = state["expert_id"]
    gaps = list(db.col(db.GAPS).find({"owner_id": expert, "status": "open"}))
    gaps.sort(key=lambda g: (g["kind"] != "contradiction", g.get("created_at") or 0))
    recent = list(db.col(db.MEMORIES).find({"owner_id": expert, "status": "active"}).sort("created_at", -1).limit(8))
    open_gaps = [
        {"id": g["_id"], "question": g["question"], "kind": g["kind"],
         "from_memory_ids": list(g.get("from_memory_ids") or [])}
        for g in gaps
    ]
    ids = [m["_id"] for m in recent] + [i for g in open_gaps for i in g["from_memory_ids"]]
    write_audit(expert, "interview_recall", list(dict.fromkeys(ids)), True,
                f"interviewer loaded {len(open_gaps)} open gaps and {len(recent)} recent memories",
                detail={"session_id": state["session_id"]})
    return {"open_gaps": open_gaps, "recent": [{"id": m["_id"], "text": m["text"]} for m in recent]}


def _followup(state: State) -> str | None:
    recent = state.get("recent") or []
    if not (llm.llm_available() and recent):
        return None
    asked = [h["q"] for h in state.get("history", [])]
    prompt = ("What we already know:\n- " + "\n- ".join(m["text"] for m in recent)
              + "\n\nQuestions already asked:\n- " + ("\n- ".join(asked) or "(none)"))
    try:
        text = llm.generate_text(prompt, system=FOLLOWUP_SYSTEM, temperature=0.5).strip().strip('"')
    except Exception:
        log.exception("follow-up generation failed")
        return None
    return text or None


def ask(state: State) -> dict:
    gaps = state.get("open_gaps") or []
    gap = next((g for g in gaps if g["kind"] == "contradiction"), None) or next(iter(gaps), None)
    if gap:
        db.col(db.GAPS).update_one({"_id": gap["id"]}, {"$set": {"status": "asked"}})
        return {"question": gap["question"], "current_gap_id": gap["id"], "used_memory_ids": gap["from_memory_ids"]}
    question = _followup(state)
    if question:
        return {"question": question, "current_gap_id": None, "used_memory_ids": [m["id"] for m in state["recent"]]}
    stock = STOCK_QUESTIONS[state.get("turn", 0) % len(STOCK_QUESTIONS)]
    return {"question": stock, "current_gap_id": None, "used_memory_ids": []}


def listen(state: State) -> dict:
    # Re-runs from the top on resume, so no side effects here.
    answer = interrupt({"question": state["question"]})
    return {"transcript": answer.get("transcript") or "", "clip_id": answer.get("clip_id") or ""}


def extract(state: State) -> dict:
    expert, transcript = state["expert_id"], state.get("transcript", "")
    items = extraction.extract_memories(transcript, context=[m["text"] for m in state.get("recent") or []])
    if not items:
        return {"new_memory_ids": []}
    now = models.utcnow()
    vectors = embeddings.embed_documents([i["text"] for i in items])
    docs = [
        models.build_memory_doc(
            owner_id=expert, kind=i["kind"], text=i["text"], embedding=vec, scope=i["scope"],
            source_clip_id=state.get("clip_id", ""), session_id=state["session_id"], created_at=now,
            expires_at=now + timedelta(days=i["expires_in_days"]) if i["expires_in_days"] else None,
        )
        for i, vec in zip(items, vectors)
    ]
    db.col(db.MEMORIES).insert_many(docs)
    steps = [d for d in docs if d["kind"] in ("procedure", "workaround") and d["scope"] != "never_transfer"]
    if steps:
        last = db.col(db.RUNBOOK).find_one(sort=[("order", -1)])
        order = float(last["order"]) if last else 0.0
        db.col(db.RUNBOOK).insert_many(
            [models.build_runbook_step(d["text"], [d["_id"]], order=order + n + 1) for n, d in enumerate(steps)]
        )
    return {"new_memory_ids": [d["_id"] for d in docs]}


def _related(new_docs: list[dict], expert: str) -> list[dict]:
    try:
        import retrieval

        new_ids = [d["_id"] for d in new_docs]
        found: dict[str, dict] = {}
        for d in new_docs:
            for r in retrieval.related_memories(d["text"], expert, k=5, exclude_ids=new_ids):
                found.setdefault(r["_id"], r)
        return list(found.values())
    except Exception:
        log.exception("related_memories unavailable")
        return []


def detect(state: State) -> dict:
    expert, sid = state["expert_id"], state["session_id"]
    gap_ids: list[str] = []
    new_ids = state.get("new_memory_ids") or []
    if state.get("memory_on") and new_ids:
        new_docs = list(db.col(db.MEMORIES).find({"_id": {"$in": new_ids}}))
        found = detection.detect_gaps(new_docs, _related(new_docs, expert), state.get("transcript", ""))
        # This answer resolves the gap that was just asked: don't re-raise a contradiction about the same memories.
        answered = db.col(db.GAPS).find_one({"_id": state["current_gap_id"]}) if state.get("current_gap_id") else None
        resolved = set(answered["from_memory_ids"]) if answered else set()
        found = [g for g in found if not (g["kind"] == "contradiction" and resolved & set(g["from_memory_ids"]))]
        gaps =[models.build_gap(expert, g["question"], g["kind"], g["from_memory_ids"], session_id=sid) for g in found]
        if gaps:
            db.col(db.GAPS).insert_many(gaps)
        gap_ids = [g["_id"] for g in gaps]
    answer = state.get("transcript", "").strip()
    if state.get("current_gap_id") and answer:
        db.col(db.GAPS).update_one({"_id": state["current_gap_id"]}, {"$set": {"status": "answered"}})
    turn = state.get("turn", 0) + 1
    db.col(db.SESSIONS).update_one({"_id": sid}, {"$set": {"turn": turn}})
    history = [*state.get("history", []), {"q": state.get("question", ""), "a": answer}]
    return {"new_gap_ids": gap_ids, "turn": turn, "history": history}


def build_graph(checkpointer):
    g = StateGraph(State)
    for name, fn in [("recall", recall), ("ask", ask), ("listen", listen), ("extract", extract), ("detect", detect)]:
        g.add_node(name, fn)
    g.add_edge(START, "recall")
    for a, b in [("recall", "ask"), ("ask", "listen"), ("listen", "extract"), ("extract", "detect"), ("detect", "recall")]:
        g.add_edge(a, b)
    return g.compile(checkpointer=checkpointer)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph(MongoDBSaver(db.get_client(), db_name=settings.MONGODB_DB))
    return _graph


def _config(session_id: str, expert_id: str, memory_on: bool) -> dict:
    return {
        "configurable": {"thread_id": session_id},
        "tags": ["handover", "interview", "memory_on" if memory_on else "memory_off"],
        "metadata": {"session_id": session_id, "expert_id": expert_id, "memory_on": memory_on},
    }


@traceable(name="start_session")
def start_session(expert_id: str, memory_on: bool = True) -> dict:
    person = db.col(db.PEOPLE).find_one({"_id": expert_id})
    if not person or person.get("role") != "expert":
        raise errors.NotFound(f"expert {expert_id} not found")
    sid = models.new_id("s")
    db.col(db.SESSIONS).insert_one({"_id": sid, "expert_id": expert_id, "memory_on": memory_on,
                                    "status": "active", "turn": 0, "created_at": models.utcnow()})
    init = {"session_id": sid, "expert_id": expert_id, "memory_on": memory_on, "turn": 0, "history": [],
            "new_memory_ids": [], "new_gap_ids": [], "current_gap_id": None, "used_memory_ids": []}
    out = get_graph().invoke(init, _config(sid, expert_id, memory_on))
    return {"session_id": sid, "first_question_text": out["question"], "used_memory_ids": out["used_memory_ids"]}


def _by_ids(collection: str, ids: list[str]) -> list[dict]:
    docs = {d["_id"]: d for d in db.col(collection).find({"_id": {"$in": ids}})} if ids else {}
    return [docs[i] for i in ids if i in docs]


@traceable(name="submit_answer")
def submit_answer(session_id: str, transcript: str, clip_id: str) -> dict:
    session = db.col(db.SESSIONS).find_one({"_id": session_id})
    if not session:
        raise errors.NotFound(f"session {session_id} not found")
    config = _config(session_id, session["expert_id"], bool(session.get("memory_on", True)))
    out = get_graph().invoke(Command(resume={"transcript": transcript or "", "clip_id": clip_id or ""}), config)
    return {
        "memories_created": [models.memory_out(d) for d in _by_ids(db.MEMORIES, out.get("new_memory_ids") or [])],
        "gaps_created": [models.gap_out(d) for d in _by_ids(db.GAPS, out.get("new_gap_ids") or [])],
        "next_question_text": out["question"],
        "used_memory_ids": out.get("used_memory_ids") or [],
    }
