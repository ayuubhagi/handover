"""Find contradictions and missing information after a new answer."""
import logging
import re
from typing import Literal

from pydantic import BaseModel

import llm

log = logging.getLogger("handover.detection")

SYSTEM = """You are an interviewer checking a retiring expert's knowledge base for problems.
You get NEW memories (just said) and RELATED older memories, each with an id.
Return gaps of two kinds:
- contradiction: a new memory conflicts with an older one. Phrase the question the way an interviewer would say it
  out loud, quoting both versions ("You told me X, but you also said Y. Which is right?").
  from_memory_ids = [older id, new id].
- missing: at most 2 questions about information a successor would need but is absent: an unnamed owner, a missing
  threshold, what to do if it fails, where access or credentials live. from_memory_ids = [new id].
Use only ids from the input. Return an empty list if there are no real problems."""


class _Gap(BaseModel):
    question: str
    kind: Literal["missing", "contradiction"]
    from_memory_ids: list[str]


class _Result(BaseModel):
    gaps: list[_Gap]


def _heuristic(new_memories: list[dict]) -> list[dict]:
    for m in new_memories:
        low = m["text"].lower()
        if m.get("kind") == "procedure" and re.search(r"\b(run|running|script|job)\b", low) \
                and not re.search(r"\b(access|permission|fails?|failure|owner)\b", low):
            return [{
                "question": f"You described this step: \"{m['text']}\" Who is allowed to run it, and what do you do if it fails?",
                "kind": "missing",
                "from_memory_ids": [m["_id"]],
            }]
    return []


def detect_gaps(new_memories: list[dict], related: list[dict], transcript: str) -> list[dict]:
    if not new_memories:
        return []
    if not llm.llm_available():
        return _heuristic(new_memories)
    new_ids = {m["_id"] for m in new_memories}
    valid = new_ids | {m["_id"] for m in related}
    fmt = lambda ms: "\n".join(f"[{m['_id']}] ({m.get('kind', '')}) {m['text']}" for m in ms) or "(none)"
    prompt = (f"NEW memories:\n{fmt(new_memories)}\n\nRELATED older memories:\n{fmt(related)}\n\n"
              f"Transcript of the latest answer:\n{transcript}")
    try:
        result = llm.generate_json(prompt, _Result, system=SYSTEM)
    except Exception:
        log.exception("LLM gap detection failed, using heuristic")
        return _heuristic(new_memories)
    gaps, missing = [], 0
    for g in result.gaps:
        ids = list(dict.fromkeys(i for i in g.from_memory_ids if i in valid))
        question = g.question.strip()
        if not question or not ids:
            continue
        if g.kind == "contradiction":
            if len(ids) < 2 or not (set(ids) & new_ids):
                continue
        else:
            if missing >= 2:
                continue
            missing += 1
        gaps.append({"question": question, "kind": g.kind, "from_memory_ids": ids})
    return gaps
