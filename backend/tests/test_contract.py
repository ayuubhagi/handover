"""End to end check of the TEAM.md contract against a running, freshly seeded server.

    python seed.py
    uvicorn main:app --port 8000
    pytest tests/test_contract.py -v

Tests run in file order and mutate data (correct, forget), so reseed before running again.
"""
import os

import httpx
import pytest

BASE = os.getenv("HANDOVER_BASE_URL", "http://localhost:8000")
EXPERT = {"X-User-Id": "u_expert"}
SUCCESSOR = {"X-User-Id": "u_successor"}
OUTSIDER = {"X-User-Id": "u_outsider"}

MEMORY_KEYS = {"id", "owner_id", "kind", "text", "scope", "status", "version", "supersedes", "derived_from",
               "source_clip_id", "session_id", "created_at", "expires_at"}
GAP_KEYS = {"id", "question", "kind", "from_memory_ids", "status"}


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=BASE, timeout=120) as client:
        yield client


def assert_memory(m: dict):
    assert set(m) == MEMORY_KEYS, set(m) ^ MEMORY_KEYS
    assert m["kind"] in {"procedure", "system", "client", "workaround"}
    assert m["scope"] in {"successor", "team", "never_transfer"}
    assert m["status"] in {"active", "corrected", "forgotten"}
    assert m["created_at"].endswith("Z") and m["expires_at"].endswith("Z")


def test_unknown_user_rejected(api):
    assert api.get("/memories", headers={"X-User-Id": "u_nobody"}).status_code == 401
    assert api.get("/memories").status_code == 401


def test_memories_scoped_per_viewer(api):
    mine = api.get("/memories", params={"owner_id": "u_expert"}, headers=EXPERT).json()
    assert len(mine) >= 9
    for m in mine:
        assert_memory(m)
    theirs = api.get("/memories", params={"owner_id": "u_expert"}, headers=SUCCESSOR).json()
    assert theirs and all(m["scope"] in {"successor", "team"} and m["status"] == "active" for m in theirs)
    assert "m_4" not in {m["id"] for m in theirs}
    assert api.get("/memories", params={"owner_id": "u_expert"}, headers=OUTSIDER).json() == []


def test_ask_successor_gets_sources(api):
    r = api.post("/ask", json={"question": "What do I do when the SWIFT queue backs up?", "memory": True},
                 headers=SUCCESSOR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"answer_text", "sources", "blocked_count", "audit_id"}
    assert body["answer_text"] and body["sources"]
    for s in body["sources"]:
        assert set(s) == {"memory", "clip_url", "transcript"}
        assert_memory(s["memory"])
        assert s["memory"]["scope"] != "never_transfer"
        assert s["clip_url"].endswith("/clips/" + s["memory"]["source_clip_id"])
    assert {"m_2", "m_3", "m_9"} & {s["memory"]["id"] for s in body["sources"]}


def test_ask_never_transfer_stays_private(api):
    q = {"question": "What is the arrangement with Halvorsen Freight for Friday wires?", "memory": True}
    owner = api.post("/ask", json=q, headers=EXPERT).json()
    assert "m_4" in {s["memory"]["id"] for s in owner["sources"]}
    succ = api.post("/ask", json=q, headers=SUCCESSOR).json()
    assert "m_4" not in {s["memory"]["id"] for s in succ["sources"]}
    assert succ["blocked_count"] >= 1


def test_ask_outsider_blocked_and_audited(api):
    r = api.post("/ask", json={"question": "What do I do when the SWIFT queue backs up?", "memory": True},
                 headers=OUTSIDER).json()
    assert r["sources"] == [] and r["blocked_count"] >= 1
    audit = api.get("/audit", params={"limit": 50}, headers=EXPERT).json()
    assert set(audit[0]) == {"actor_id", "action", "memory_ids", "allowed", "reason", "ts"}
    assert any(a["actor_id"] == "u_outsider" and a["action"] == "ask" and a["allowed"] is False for a in audit)


def test_ask_memory_off(api):
    r = api.post("/ask", json={"question": "What do I do when the SWIFT queue backs up?", "memory": False},
                 headers=SUCCESSOR).json()
    assert r["sources"] == [] and r["blocked_count"] == 0 and r["answer_text"]


def test_runbook_visibility(api):
    full = api.get("/runbook", headers=EXPERT).json()
    assert set(full[0]) == {"id", "text", "derived_from", "status"}
    assert {"r_1", "r_6"} <= {s["id"] for s in full}
    succ = {s["id"] for s in api.get("/runbook", headers=SUCCESSOR).json()}
    assert "r_1" in succ and "r_6" not in succ  # r_6 is built from a never_transfer memory
    assert api.get("/runbook", headers=OUTSIDER).json() == []


def test_gaps(api):
    gaps = api.get("/gaps", params={"owner_id": "u_expert"}, headers=EXPERT).json()
    assert {"g_1", "g_2"} <= {g["id"] for g in gaps}
    assert all(set(g) == GAP_KEYS for g in gaps)
    assert api.get("/gaps", params={"owner_id": "u_expert"}, headers=OUTSIDER).json() == []


def test_governance_is_owner_only(api):
    assert api.patch("/memories/m_2/scope", json={"scope": "successor"}, headers=SUCCESSOR).status_code == 403
    assert api.post("/memories/m_2/correct", json={"text": "x"}, headers=SUCCESSOR).status_code == 403
    assert api.post("/memories/m_2/forget", headers=OUTSIDER).status_code == 403
    assert api.patch("/memories/m_2/scope", json={"scope": "everyone"}, headers=EXPERT).status_code == 422
    assert api.post("/memories/m_nope/forget", headers=EXPERT).status_code == 404


def test_scope_change_hides_and_restores(api):
    r = api.patch("/memories/m_8/scope", json={"scope": "never_transfer"}, headers=EXPERT)
    assert r.status_code == 200, r.text
    assert_memory(r.json())
    assert r.json()["scope"] == "never_transfer"
    assert "r_5" not in {s["id"] for s in api.get("/runbook", headers=SUCCESSOR).json()}
    assert "m_8" not in {m["id"] for m in api.get("/memories", headers=SUCCESSOR).json()}
    api.patch("/memories/m_8/scope", json={"scope": "team"}, headers=EXPERT)
    assert "r_5" in {s["id"] for s in api.get("/runbook", headers=SUCCESSOR).json()}


def test_correct_versions_memory(api):
    r = api.post("/memories/m_5/correct",
                 json={"text": "Rerun the LedgerOne reconciliation report after 11 a.m. Eastern on the first business day."},
                 headers=EXPERT)
    assert r.status_code == 200, r.text
    old, new = r.json()["old"], r.json()["new"]
    assert_memory(old), assert_memory(new)
    assert old["id"] == "m_5" and old["status"] == "corrected"
    assert new["status"] == "active" and new["version"] == 2 and new["supersedes"] == "m_5"
    step = next(s for s in api.get("/runbook", headers=EXPERT).json() if s["id"] == "r_3")
    assert step["derived_from"] == [new["id"]] and step["status"] == "needs_review"
    succ_ids = {m["id"] for m in api.get("/memories", headers=SUCCESSOR).json()}
    assert new["id"] in succ_ids and "m_5" not in succ_ids


def test_forget_cascades(api):
    r = api.post("/memories/m_3/forget", headers=EXPERT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"forgotten_ids", "runbook_steps_removed", "audit_id"}
    assert {"m_3", "m_9"} <= set(body["forgotten_ids"])  # m_9 was derived from m_3
    assert "r_2" in body["runbook_steps_removed"]         # r_2 was built from m_9
    assert "r_2" not in {s["id"] for s in api.get("/runbook", headers=EXPERT).json()}
    mems = {m["id"]: m for m in api.get("/memories", headers=EXPERT).json()}
    assert mems["m_3"]["status"] == "forgotten" and "swift-drain" not in mems["m_3"]["text"]
    assert "g_2" not in {g["id"] for g in api.get("/gaps", headers=EXPERT).json()}
    audit = api.get("/audit", params={"limit": 10}, headers=EXPERT).json()
    assert any(a["action"] == "forget" and "m_3" in a["memory_ids"] for a in audit)
    again = api.post("/ask", json={"question": "How do I drain the SWIFT queue with swift-drain?", "memory": True},
                     headers=SUCCESSOR).json()
    assert not {"m_3", "m_9"} & {s["memory"]["id"] for s in again["sources"]}


def test_clip_access(api):
    r = api.get("/clips/c_3", headers=OUTSIDER)
    assert r.status_code == 403
    assert api.get("/clips/c_3", headers=SUCCESSOR).status_code == 403  # only backs a never_transfer memory
    assert api.get("/clips/c_1", headers=SUCCESSOR).status_code in (200, 404)  # 404 until a recording is seeded
    assert api.get("/clips/c_missing", headers=EXPERT).status_code == 404


def test_interview_session_asks_about_seeded_gap(api):
    assert api.post("/sessions", json={"expert_id": "u_expert"}, headers=SUCCESSOR).status_code == 403
    r = api.post("/sessions", json={"expert_id": "u_expert"}, headers=EXPERT)
    assert r.status_code == 200, r.text
    start = r.json()
    assert set(start) == {"session_id", "first_question_text", "first_question_audio_url"}
    assert "database" in start["first_question_text"].lower()  # g_1, the contradiction from session 1

    answer = ("The queue comes first, always. Restart the payments queue, then clear the ledger database locks. "
              "Also, the swift-drain job needs the OPS-BATCH service account and the password is in the team vault.")
    r = api.post(f"/sessions/{start['session_id']}/answer", data={"transcript": answer},
                 files={"audio": ("answer.webm", b"", "audio/webm")}, headers=EXPERT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"transcript", "memories_created", "gaps_created", "next_question_text",
                         "next_question_audio_url", "used_memory_ids"}
    assert body["transcript"] == answer and body["next_question_text"]
    assert body["memories_created"]
    for m in body["memories_created"]:
        assert_memory(m)
        assert m["session_id"] == start["session_id"]
    assert all(set(g) == GAP_KEYS for g in body["gaps_created"])
    gaps = {g["id"]: g for g in api.get("/gaps", headers=EXPERT).json()}
    assert gaps["g_1"]["status"] == "answered"


def test_live_websocket_pushes_changes(api):
    from websockets.sync.client import connect
    import json

    url = BASE.replace("http", "ws", 1) + "/live?user_id=u_expert"
    with connect(url) as ws:
        api.patch("/memories/m_2/scope", json={"scope": "successor"}, headers=EXPERT)
        seen = set()
        for _ in range(6):
            try:
                msg = json.loads(ws.recv(timeout=15))
            except TimeoutError:
                break
            seen.add(msg["type"])
            if msg["type"] == "memory_changed":
                assert_memory(msg["memory"])
                assert msg["memory"]["id"] == "m_2" and msg["memory"]["scope"] == "successor"
            if seen >= {"memory_changed", "runbook_changed"}:
                break
        assert "memory_changed" in seen
    api.patch("/memories/m_2/scope", json={"scope": "team"}, headers=EXPERT)
