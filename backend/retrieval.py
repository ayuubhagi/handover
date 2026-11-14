"""Hybrid retrieval over memories and the /ask endpoint.

Access control lives inside the database query: every mode below filters on owner, status, scope and expiry
in the search stage itself, so a memory the viewer may not read is never returned to Python.

Modes, best first (the first one that works is remembered):
  rank_fusion  $rankFusion over $vectorSearch + $search (MongoDB 8.x)
  manual_rrf   $vectorSearch + $unionWith $search, reciprocal rank fusion in $group
  vector       $vectorSearch only
  keyword      $match + keyword overlap scored in the aggregation (no search indexes needed)
"""
import logging
import re
import time
from datetime import datetime

from langsmith import traceable
from pymongo.errors import OperationFailure

import access
import audit
import db
import embeddings
import llm
from config import settings
from models import clip_url, memory_out, utcnow

log = logging.getLogger("handover.retrieval")

MODES = ("rank_fusion", "manual_rrf", "vector", "keyword")
VECTOR_WEIGHT, TEXT_WEIGHT = 0.6, 0.4
RRF_K = 60                 # standard reciprocal rank fusion constant
RETRY_AFTER = 300.0        # seconds before a failed mode is tried again
INDEX_RECHECK = 30.0       # seconds between search index readiness checks

_failed_until: dict[str, float] = {}
_last_mode: str | None = None
_indexes_ready = False
_indexes_checked_at = 0.0

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how", "i", "if", "in",
    "is", "it", "me", "my", "of", "on", "or", "our", "should", "so", "that", "the", "their", "then", "there",
    "this", "to", "we", "what", "when", "where", "which", "who", "why", "with", "you", "your",
}


# ---------- filters (identical constraints for every mode) ----------

def _mql_filter(owner_id: str, scopes: list[str] | None, now: datetime) -> dict:
    """Valid both as a $vectorSearch pre-filter and as a $match. scopes=None drops the scope clause."""
    clauses = [
        {"owner_id": {"$eq": owner_id}},
        {"status": {"$eq": "active"}},
        {"expires_at": {"$gt": now}},
    ]
    if scopes is not None:
        clauses.append({"scope": {"$in": list(scopes)}})
    return {"$and": clauses}


def _search_filter(owner_id: str, scopes: list[str] | None, now: datetime) -> list[dict]:
    """Same constraints for Atlas Search compound.filter (token fields use equals/in, the date uses range)."""
    clauses = [
        {"equals": {"path": "owner_id", "value": owner_id}},
        {"equals": {"path": "status", "value": "active"}},
        {"range": {"path": "expires_at", "gt": now}},
    ]
    if scopes is not None:
        clauses.append({"in": {"path": "scope", "value": list(scopes)}})
    return clauses


def _vector_stage(qv: list[float], flt: dict, limit: int) -> dict:
    # Approximate nearest neighbour search; the filter is applied during the search, not after it.
    return {"$vectorSearch": {
        "index": db.VECTOR_INDEX, "path": "embedding", "queryVector": qv,
        "numCandidates": max(100, limit * 10), "limit": limit, "filter": flt,
    }}


def _text_stage(question: str, filters: list[dict]) -> dict:
    # Full text relevance on "text"; non-scoring filter clauses enforce access.
    return {"$search": {
        "index": db.TEXT_INDEX,
        "compound": {"must": [{"text": {"query": question, "path": "text"}}], "filter": filters},
    }}


def _tail(k: int, ids_only: bool) -> list[dict]:
    """Common end of every pipeline: cut to k, drop the vector, join the source clip."""
    if ids_only:
        return [{"$limit": k}, {"$project": {"_id": 1, "scope": 1, "_score": 1}}]
    return [
        {"$limit": k},
        {"$project": {"embedding": 0}},
        {"$lookup": {"from": db.CLIPS, "localField": "source_clip_id", "foreignField": "_id", "as": "clip"}},
    ]


# ---------- pipelines ----------

def _rank_fusion_pipeline(question, qv, owner_id, scopes, now, k, ids_only):
    n = max(10, k * 2)
    return [
        # $rankFusion runs both ranked pipelines and merges them by weighted reciprocal rank.
        {"$rankFusion": {
            "input": {"pipelines": {
                "vector": [_vector_stage(qv, _mql_filter(owner_id, scopes, now), n)],
                "text": [_text_stage(question, _search_filter(owner_id, scopes, now)), {"$limit": n}],
            }},
            "combination": {"weights": {"vector": VECTOR_WEIGHT, "text": TEXT_WEIGHT}},
            "scoreDetails": not ids_only,
        }},
        *([] if ids_only else [{"$addFields": {"_score": {"$meta": "scoreDetails"}}}]),
        *_tail(k, ids_only),
    ]


def _ranked(weight: float, ids_only: bool) -> list[dict]:
    """Turn one ranked result list into {doc fields..., _rrf: weight / (60 + rank)}."""
    keep = {"_id": 1, "scope": 1} if ids_only else {"embedding": 0}
    return [
        {"$project": keep},
        {"$group": {"_id": None, "docs": {"$push": "$$ROOT"}}},
        {"$unwind": {"path": "$docs", "includeArrayIndex": "rank"}},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": [
            "$docs", {"_rrf": {"$divide": [weight, {"$add": ["$rank", RRF_K + 1]}]}},
        ]}}},
    ]


def _manual_rrf_pipeline(question, qv, owner_id, scopes, now, k, ids_only):
    n = max(10, k * 2)
    pipeline = [
        _vector_stage(qv, _mql_filter(owner_id, scopes, now), n),
        *_ranked(VECTOR_WEIGHT, ids_only),
        # $unionWith appends the keyword results from the same collection.
        {"$unionWith": {"coll": db.MEMORIES, "pipeline": [
            _text_stage(question, _search_filter(owner_id, scopes, now)),
            {"$limit": n},
            *_ranked(TEXT_WEIGHT, ids_only),
        ]}},
        # A memory found by both sides gets both contributions.
        {"$group": {"_id": "$_id", "doc": {"$first": "$$ROOT"}, "score": {"$sum": "$_rrf"}}},
        {"$sort": {"score": -1, "_id": 1}},
        {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$doc", {"_score": "$score"}]}}},
        {"$unset": "_rrf"},
    ]
    return pipeline + _tail(k, ids_only)


def _vector_pipeline(question, qv, owner_id, scopes, now, k, ids_only):
    return [
        _vector_stage(qv, _mql_filter(owner_id, scopes, now), k),
        {"$addFields": {"_score": {"$meta": "vectorSearchScore"}}},
        *_tail(k, ids_only),
    ]


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _keyword_pipeline(question, qv, owner_id, scopes, now, k, ids_only):
    base = sorted(set(_tokens(question)))
    variants = sorted({v for t in base for v in (t, t[:-1] if t.endswith("s") else t + "s")})
    words = {"$map": {"input": {"$regexFindAll": {"input": {"$toLower": "$text"}, "regex": "[a-z0-9]+"}},
                      "as": "m", "in": "$$m.match"}}
    return [
        {"$match": _mql_filter(owner_id, scopes, now)},
        # Keyword overlap is computed in the database, so even this mode never ships unreadable text out.
        {"$addFields": {"_score": {"$divide": [{"$size": {"$setIntersection": [words, variants]}}, len(base) or 1]}}},
        {"$match": {"_score": {"$gt": 0}}},
        {"$sort": {"_score": -1, "created_at": -1}},
        *_tail(k, ids_only),
    ]


_PIPELINES = {
    "rank_fusion": _rank_fusion_pipeline,
    "manual_rrf": _manual_rrf_pipeline,
    "vector": _vector_pipeline,
    "keyword": _keyword_pipeline,
}


# ---------- mode selection ----------

def _search_indexes_ready() -> bool:
    global _indexes_ready, _indexes_checked_at
    if not _indexes_ready and time.monotonic() - _indexes_checked_at > INDEX_RECHECK:
        _indexes_checked_at = time.monotonic()
        _indexes_ready = db.search_indexes_ready()
        if not _indexes_ready:
            log.warning("search indexes not queryable yet, retrieval uses keyword mode")
    return _indexes_ready


def _query_vector(question: str, given: list[float] | None) -> list[float] | None:
    if given is not None:
        return given
    if not _search_indexes_ready():
        return None
    try:
        return embeddings.embed_query(question)
    except Exception as exc:  # embedding provider down: degrade to keyword mode
        log.warning("query embedding failed, using keyword mode: %s", exc)
        return None


def _run(question: str, qv: list[float] | None, owner_id: str, scopes: list[str] | None, k: int,
         *, ids_only: bool = False, start: str | None = None,
         capture: list | None = None) -> tuple[list[dict], str]:
    """Try each mode in order (from `start`), skipping ones that recently failed. Returns (docs, mode).
    If `capture` is given, the pipeline that actually ran is appended to it (for the /ask "query" field)."""
    global _last_mode
    now = utcnow()
    modes = MODES[MODES.index(start):] if start else MODES
    for mode in modes:
        if mode != "keyword" and (qv is None or not _search_indexes_ready()
                                  or _failed_until.get(mode, 0) > time.monotonic()):
            continue
        pipeline = _PIPELINES[mode](question, qv, owner_id, scopes, now, k, ids_only)
        try:
            docs = list(db.col(db.MEMORIES).aggregate(pipeline))
        except OperationFailure as exc:
            if mode == "keyword":
                raise
            log.warning("retrieval mode %s failed (%s), falling back", mode, exc.details or exc)
            _failed_until[mode] = time.monotonic() + RETRY_AFTER
            continue
        if mode != _last_mode and not ids_only:
            log.info("retrieval mode: %s", mode)
            _last_mode = mode
        if capture is not None:
            capture.append({"mode": mode, "pipeline": pipeline})
        return docs, mode
    return [], "keyword"


def _shape(doc: dict) -> dict:
    """clip array -> dict or None; scoreDetails -> float _score (details kept for traces)."""
    clips = doc.pop("clip", None) or []
    doc["clip"] = clips[0] if clips else None
    score = doc.get("_score")
    if isinstance(score, dict):  # $rankFusion scoreDetails: {value, description, details: [...]}
        doc["_score_details"] = score
        score = score.get("value")
    doc["_score"] = float(score or 0.0)
    return doc


# ---------- public API ----------

def _search(question: str, owner_id: str, scopes: list[str], k: int,
            qv: list[float] | None, capture: list | None = None) -> tuple[list[dict], str | None]:
    if not scopes or not question.strip():
        return [], None
    docs, mode = _run(question, qv, owner_id, scopes, k, capture=capture)
    return [_shape(d) for d in docs], mode


def hybrid_search(question: str, *, owner_id: str, scopes: list[str], k: int = 5,
                  query_vector: list[float] | None = None) -> list[dict]:
    """Top k readable memories (no embedding) with "clip" (dict or None) and "_score" (float)."""
    if not scopes or not question.strip():
        return []
    docs, _ = _search(question, owner_id, scopes, k, _query_vector(question, query_vector))
    return docs


def _count_blocked(question: str, *, owner_id: str, scopes: list[str], k: int = 5,
                   query_vector: list[float] | None = None, mode: str | None = None,
                   capture: list | None = None) -> list[str]:
    """Scopes of the top k hits, ignoring scope, that the viewer may not read (one entry per hit).
    Only _id and scope are projected, so blocked text never leaves the database."""
    if set(access.ALL_SCOPES) <= set(scopes) or not question.strip():
        return []
    hits, _ = _run(question, query_vector, owner_id, None, k, ids_only=True, start=mode, capture=capture)
    return [h.get("scope") for h in hits if h.get("scope") not in scopes]


def _relevance(qv: list[float], owner_id: str, k: int = 10,
               capture: list | None = None) -> tuple[dict[str, tuple[str, float]], float]:
    """Vector similarity of the top k memories across ALL scopes: {id: (scope, vectorSearchScore)} and the cutoff.
    Only _id, scope and the score leave the database. A memory counts as relevant when its score is at least
    RELEVANCE_MIN and within RELEVANCE_MARGIN of the best match, so one shared cutoff decides both which sources
    are shown and which withheld memories are counted."""
    hits, _ = _run("", qv, owner_id, None, k, ids_only=True, start="vector", capture=capture)
    scores = {h["_id"]: (h.get("scope"), float(h.get("_score") or 0.0)) for h in hits}
    top = max((s for _, s in scores.values()), default=0.0)
    return scores, max(settings.RELEVANCE_MIN, top - settings.RELEVANCE_MARGIN)


def related_memories(text: str, owner_id: str, *, k: int = 5, exclude_ids=()) -> list[dict]:
    """Owner level search (all scopes, active only) used by the interview agent."""
    exclude = set(exclude_ids)
    docs = hybrid_search(text, owner_id=owner_id, scopes=list(access.ALL_SCOPES), k=k + len(exclude))
    return [d for d in docs if d["_id"] not in exclude][:k]


# ---------- /ask ----------

_NO_MEMORY_FALLBACK = ("Generally, follow your team's standard procedure for this: fix the issue through the normal "
                       "system, get the usual approvals, and document what you did.")

# Memory off = a capable assistant with no handover knowledge. It must still answer, so the side-by-side shows
# what the handover memory adds, not a refusal.
MEMORY_OFF_SYSTEM = (
    "You are a general-purpose assistant helping someone at a bank's payments operations team. You know common "
    "industry practice but nothing specific about this company, its systems, clients or past incidents. "
    "Give your best practical general answer in 2-3 sentences, as if from general banking operations experience. "
    "Do not mention that you lack access, do not say you don't know their systems, and do not tell them to ask "
    "someone else or contact IT."
)


def _answer_without_memory(question: str) -> str:
    if not llm.llm_available():
        return _NO_MEMORY_FALLBACK
    try:
        return llm.generate_text(question, system=MEMORY_OFF_SYSTEM, temperature=0.4) or _NO_MEMORY_FALLBACK
    except Exception as exc:
        log.warning("llm failed for memory-off answer: %s", exc)
        return _NO_MEMORY_FALLBACK


def _open_gaps_for_docs(owner_id: str, docs: list[dict]) -> list[dict]:
    """Open gaps are safe to surface only when every referenced memory is already in this answer."""
    visible_ids = {d["_id"] for d in docs}
    if not visible_ids:
        return []
    gaps = db.col(db.GAPS).find({"owner_id": owner_id, "status": {"$in": ["open", "asked"]}})
    return [g for g in gaps if g.get("from_memory_ids") and set(g["from_memory_ids"]) <= visible_ids]


def _grounded_answer(question: str, docs: list[dict], owner_name: str, gaps: list[dict]) -> str:
    quote = f'{owner_name}\'s handover notes say: "{docs[0]["text"]}"'
    if not llm.llm_available():
        answer = quote
    else:
        context = "\n".join(f"[{i}] ({d['kind']}) {d['text']}" for i, d in enumerate(docs, 1))
        try:
            answer = llm.generate_text(
                f"Handover memories:\n{context}\n\nQuestion: {question}",
                system=f"You help a successor take over {owner_name}'s work. Answer using ONLY the numbered handover "
                       "memories provided. If they do not answer the question, say the handover memory does not cover it. "
                       "Be concise and practical, 2-4 sentences, and cite memories like [1].",
            ) or quote
        except Exception as exc:
            log.warning("llm failed, quoting top source: %s", exc)
            answer = quote
    if gaps:
        answer += "\n\n" + "\n".join(f"Open question: {gap['question']}" for gap in gaps)
    return answer


def _nothing_available(blocked: int) -> str:
    if not blocked:
        return "The handover doesn't cover this."
    noun = "memory exists" if blocked == 1 else "memories exist"
    return (f"The handover doesn't cover this for you: {blocked} related {noun} but "
            f"{'is' if blocked == 1 else 'are'} not shared with you.")


def _annotate_trace(**metadata) -> None:
    """Attach ids and counts to the current LangSmith run (no-op when tracing is off)."""
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.add_metadata(metadata)
    except Exception:
        pass


def _public(value):
    """JSON-safe copy of a pipeline for the UI: dates as ISO strings, the query vector summarised."""
    if isinstance(value, dict):
        return {k: (f"<{len(v)}-dim {settings.VOYAGE_MODEL} embedding of the question>"
                    if k == "queryVector" and isinstance(v, list) else _public(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_public(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return value


def _prefilter(pipeline: list[dict]):
    """The access filter as the database applied it: the $vectorSearch pre-filter, or the $match in keyword mode."""
    for stage in pipeline:
        if "$vectorSearch" in stage:
            return stage["$vectorSearch"].get("filter")
        if "$rankFusion" in stage:
            for sub_pipeline in stage["$rankFusion"]["input"]["pipelines"].values():
                found = _prefilter(sub_pipeline)
                if found is not None:
                    return found
        if "$match" in stage:
            return stage["$match"]
    return None


def _describe_query(main: list, check: list, cutoff: float | None) -> dict:
    ran = main[0] if main else None
    out = {
        "collection": db.MEMORIES,
        "mode": ran["mode"] if ran else None,
        "prefilter": _public(_prefilter(ran["pipeline"])) if ran else None,
        "pipeline": _public(ran["pipeline"]) if ran else None,
        "note": None if ran else "No readable scopes for this person, so the search did not run.",
        "relevance_check": None,
    }
    if check:
        out["relevance_check"] = {
            "mode": check[0]["mode"],
            "pipeline": _public(check[0]["pipeline"]),
            "cutoff": round(cutoff, 3) if cutoff is not None else None,
            "rule": (f"score >= {settings.RELEVANCE_MIN} and within {settings.RELEVANCE_MARGIN} of the best match; "
                     "same filter without the scope clause, returns only _id, scope and score"),
        }
    return out


def _trace_url() -> str | None:
    """LangSmith URL of the current ask run, or None when tracing is off."""
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        return run.get_url() if run is not None else None
    except Exception as exc:
        log.debug("no trace url: %s", exc)
        return None


@traceable(
    name="ask",
    run_type="chain",
    process_inputs=lambda inp: {"viewer_id": (inp.get("viewer") or {}).get("_id"),
                                "question": inp.get("question"), "memory_on": inp.get("memory_on", True)},
    process_outputs=lambda out: {**out, "used_memory_ids": [s["memory"]["id"] for s in out.get("sources", [])]},
)
def ask(viewer: dict, question: str, memory_on: bool = True) -> dict:
    """Contract response: {answer_text, sources: [{memory, clip_url, transcript}], blocked_count, audit_id,
    viewer, allowed_scopes, used_memory_ids, withheld_scopes, trace_url, query}."""
    viewer_id = viewer["_id"]
    owner_id = access.default_expert_id()
    scopes = access.allowed_scopes(viewer, owner_id)
    who = {"id": viewer_id, "name": viewer.get("name", viewer_id)}

    if not memory_on:
        answer = _answer_without_memory(question)
        audit_id = audit.write_audit(viewer_id, "ask", [], True, "memory off: answered without retrieval",
                                     detail={"memory_on": False, "question": question[:500]})
        _annotate_trace(viewer_id=viewer_id, viewer_name=who["name"], allowed_scopes=scopes, used_memory_ids=[],
                        blocked_count=0, withheld_scopes=[], retrieval_mode=None, memory_on=False)
        return {"answer_text": answer, "sources": [], "blocked_count": 0, "audit_id": audit_id,
                "viewer": who, "allowed_scopes": scopes, "used_memory_ids": [], "withheld_scopes": [],
                "trace_url": _trace_url(), "query": None}

    main_q: list = []
    check_q: list = []
    cutoff = None
    qv = _query_vector(question, None)
    docs, mode = _search(question, owner_id, scopes, 5, qv, capture=main_q)
    if qv is not None:
        # Relevance cutoff: drop off-topic hits, and only count withheld memories that are actually on topic.
        scores, cutoff = _relevance(qv, owner_id, capture=check_q)
        docs = [d for d in docs if scores.get(d["_id"], (None, 0.0))[1] >= cutoff]
        withheld = sorted(scope for scope, s in scores.values() if s >= cutoff and scope not in scopes)
    else:  # keyword fallback: no similarity scores to cut on
        withheld = sorted(_count_blocked(question, owner_id=owner_id, scopes=scopes, k=5, query_vector=qv,
                                         mode=mode, capture=check_q))
    blocked = len(withheld)

    sources = [{
        "memory": memory_out(d),
        "clip_url": clip_url(d.get("source_clip_id")),
        "transcript": (d.get("clip") or {}).get("transcript"),
    } for d in docs]
    used_ids = [s["memory"]["id"] for s in sources]

    if docs:
        owner = access.get_person(owner_id) or {}
        gaps = _open_gaps_for_docs(owner_id, docs)
        answer = _grounded_answer(question, docs, owner.get("name", "The expert"), gaps)
    else:
        answer = _nothing_available(blocked)

    reason = (f"scopes [{', '.join(scopes) or 'none'}] for {viewer_id}: "
              f"{len(sources)} source(s) returned, {blocked} withheld by scope")
    # allowed=false whenever the query pre-filter withheld anything, so every denial is visible in the audit log.
    audit_id = audit.write_audit(
        viewer_id, "ask", used_ids, blocked == 0, reason,
        detail={"memory_on": True, "question": question[:500], "retrieval_mode": mode, "blocked_count": blocked},
    )
    _annotate_trace(viewer_id=viewer_id, viewer_name=who["name"], allowed_scopes=scopes, used_memory_ids=used_ids,
                    blocked_count=blocked, withheld_scopes=withheld, retrieval_mode=mode, memory_on=True,
                    scores={d["_id"]: d["_score"] for d in docs})
    return {"answer_text": answer, "sources": sources, "blocked_count": blocked, "audit_id": audit_id,
            "viewer": who, "allowed_scopes": scopes, "used_memory_ids": used_ids, "withheld_scopes": withheld,
            "trace_url": _trace_url(), "query": _describe_query(main_q, check_q, cutoff)}
