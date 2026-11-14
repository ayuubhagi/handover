"""Turn an interview answer into atomic memories (LLM with a keyword fallback)."""
import logging
import re
from typing import Literal

from pydantic import BaseModel

import llm
import schemas

log = logging.getLogger("handover.extraction")
MIN_CHARS = 15

SYSTEM = """You extract durable knowledge from an exit interview with a retiring expert.
Return atomic, self-contained statements a successor could act on without hearing the recording.
Rules:
- One fact or step per statement. Write plain imperative or declarative sentences, no "he said" or "the speaker".
- Keep system, job and host names exactly as spoken (for example "SWIFT queue", "swift-drain", "OPS-BATCH-02").
- kind: procedure (steps to follow), system (facts about a system), client (anything about a client), workaround (known bug or rerun trick).
- scope: client-confidential or undocumented client arrangements -> kind "client" and scope "never_transfer";
  general system facts -> "team"; procedures and workarounds -> "successor".
- expires_in_days: null, unless the speaker says a system is being retired or switched off; then a small number such as 30.
- Skip small talk and anything that is not knowledge. Return an empty list if there is nothing."""


class _Item(BaseModel):
    kind: Literal["procedure", "system", "client", "workaround"]
    text: str
    scope: Literal["successor", "team", "never_transfer"]
    expires_in_days: int | None = None


class _Result(BaseModel):
    memories: list[_Item]


def _clean(item: dict) -> dict | None:
    text = " ".join(str(item.get("text", "")).split())
    kind, scope = item.get("kind"), item.get("scope")
    if len(text) < MIN_CHARS or kind not in schemas.KINDS or scope not in schemas.SCOPES:
        return None
    days = item.get("expires_in_days")
    days = days if isinstance(days, int) and not isinstance(days, bool) and days > 0 else None
    return {"kind": kind, "text": text, "scope": scope, "expires_in_days": days}


def _heuristic(transcript: str) -> list[dict]:
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", transcript.strip()):
        low = sentence.lower()
        if len(sentence) < MIN_CHARS:
            continue
        if "client" in low or re.search(r"\b[A-Z][a-z]+ (Freight|Bank|Corp|Ltd|Inc|Group)\b", sentence):
            kind, scope = "client", "never_transfer"
        elif any(w in low for w in ("workaround", "bug", "rerun", "re-run")):
            kind, scope = "workaround", "successor"
        elif any(w in low for w in ("queue", "system", "server", "gateway")):
            kind, scope = "system", "team"
        else:
            kind, scope = "procedure", "successor"
        days = 30 if re.search(r"switched off|retired|decommission|shut down", low) else None
        out.append({"kind": kind, "text": sentence, "scope": scope, "expires_in_days": days})
    return out


def extract_memories(transcript: str, *, context=()) -> list[dict]:
    transcript = (transcript or "").strip()
    if len(transcript) < MIN_CHARS:
        return []
    items = None
    if llm.llm_available():
        try:
            prompt = f"Transcript of the expert's answer:\n{transcript}"
            if context:
                prompt = "Already known (do not repeat):\n- " + "\n- ".join(context) + "\n\n" + prompt
            items = [i.model_dump() for i in llm.generate_json(prompt, _Result, system=SYSTEM).memories]
        except Exception:
            log.exception("LLM extraction failed, using heuristic")
    if items is None:
        items = _heuristic(transcript)
    return [c for c in map(_clean, items) if c]
