"""End to end check of the TEAM.md contract against a running, freshly seeded server.

    python seed.py
    uvicorn main:app --port 8000
    pytest tests/test_contract.py -v

Tests run in file order and mutate data (correct, forget), so reseed before running again.
"""
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402  (passcodes come from the same .env as the server)

BASE = os.getenv("HANDOVER_BASE_URL", "http://localhost:8000")


def login(user_id: str) -> dict:
    r = httpx.post(f"{BASE}/login", json={"user_id": user_id, "passcode": settings.DEMO_PASSCODES.get(user_id)})
    assert r.status_code == 200, r.text
    return r.json()


TOKENS = {uid: login(uid)["token"] for uid in ("u_expert", "u_successor", "u_outsider")}
EXPERT = {"Authorization": f"Bearer {TOKENS['u_expert']}"}
SUCCESSOR = {"Authorization": f"Bearer {TOKENS['u_successor']}"}
OUTSIDER = {"Authorization": f"Bearer {TOKENS['u_outsider']}"}

MEMORY_KEYS = {"id", "owner_id", "kind", "text", "scope", "status", "version", "supersedes", "derived_from",
               "source_clip_id", "session_id", "created_at", "expires_at"}
GAP_KEYS = {"id", "question", "kind", "from_memory_ids", "status"}

# Set HANDOVER_ANSWER_AUDIO to a recording of Dana's answer to g_1 to exercise speech to text.
ANSWER_AUDIO = os.getenv("HANDOVER_ANSWER_AUDIO")
DANA_ANSWER = ("Good catch. Clear the database locks first, but never restart the database. Clearing locks is safe. "
               "Restarting the database is what reloads the batch and causes the duplicates. "
               "So: clear the locks, then restart the queue.")
# Set HANDOVER_EXPECT_AUDIO=1 when ElevenLabs is configured: interviewer audio urls must then be present.
EXPECT_AUDIO = os.getenv("HANDOVER_EXPECT_AUDIO") == "1"


def assert_audio(api, url):
    if url is None:
        assert not EXPECT_AUDIO, "interviewer audio missing"
        return
    r = api.get(url, headers=EXPERT)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and len(r.content) > 1000


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


def test_identity_is_token_not_header(api):
    assert api.get("/memories").status_code == 401
    # Claiming to be the expert in a header is ignored: identity only comes from a signed token.
    assert api.get("/memories", headers={"X-User-Id": "u_expert"}).status_code == 401
    assert api.get("/clips/c_1", params={"user_id": "u_expert"}).status_code == 401
    payload, sig = TOKENS["u_outsider"].split(".")
    forged = TOKENS["u_expert"].split(".")[0] + "." + sig  # expert claims, outsider signature
    assert api.get("/memories", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert api.get("/me", headers=EXPERT).json() == {"id": "u_expert", "name": "Dana", "role": "expert"}


def test_login_requires_passcode(api):
    if not settings.DEMO_PASSCODES:
        pytest.skip("DEMO_PASSCODES not configured")
    assert api.post("/login", json={"user_id": "u_expert", "passcode": "000000x"}).status_code == 401
    assert api.post("/login", json={"user_id": "u_expert"}).status_code == 401
    assert api.post("/login", json={"user_id": "u_nobody", "passcode": "1"}).status_code == 401
    body = login("u_successor")
    assert set(body) == {"token", "expires_at", "user"} and body["user"]["role"] == "successor"


def test_errors_are_json_with_cors(api):
    r = api.get("/memories", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 401 and r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


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
    r = api.post("/ask", json={"question": "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?", "memory": True},
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
    assert {"m_2", "m_9"} & {s["memory"]["id"] for s in body["sources"]}


def test_ask_never_transfer_stays_private(api):
    q = {"question": "What is the arrangement with Halvorsen Freight for Friday wires?", "memory": True}
    owner = api.post("/ask", json=q, headers=EXPERT).json()
    assert "m_4" in {s["memory"]["id"] for s in owner["sources"]}
    succ = api.post("/ask", json=q, headers=SUCCESSOR).json()
    assert "m_4" not in {s["memory"]["id"] for s in succ["sources"]}
    assert succ["blocked_count"] >= 1


def test_ask_outsider_blocked_and_audited(api):
    r = api.post("/ask", json={"question": "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?", "memory": True},
                 headers=OUTSIDER).json()
    assert r["sources"] == [] and r["blocked_count"] >= 1
    audit = api.get("/audit", params={"limit": 50}, headers=EXPERT).json()
    assert set(audit[0]) == {"actor_id", "action", "memory_ids", "allowed", "reason", "ts"}
    assert any(a["actor_id"] == "u_outsider" and a["action"] == "ask" and a["allowed"] is False for a in audit)


def test_ask_memory_off(api):
    r = api.post("/ask", json={"question": "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?", "memory": False},
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
    r = api.post("/memories/m_6/correct",
                 json={"text": "Rerun the LedgerOne reconciliation report after 11 a.m. Eastern on the first business day."},
                 headers=EXPERT)
    assert r.status_code == 200, r.text
    old, new = r.json()["old"], r.json()["new"]
    assert_memory(old), assert_memory(new)
    assert old["id"] == "m_6" and old["status"] == "corrected"
    assert new["status"] == "active" and new["version"] == 2 and new["supersedes"] == "m_6"
    step = next(s for s in api.get("/runbook", headers=EXPERT).json() if s["id"] == "r_3")
    assert step["derived_from"] == [new["id"]] and step["status"] == "needs_review"
    succ_ids = {m["id"] for m in api.get("/memories", headers=SUCCESSOR).json()}
    assert new["id"] in succ_ids and "m_6" not in succ_ids


def test_forget_cascades(api):
    r = api.post("/memories/m_2/forget", headers=EXPERT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"forgotten_ids", "runbook_steps_removed", "audit_id"}
    assert {"m_2", "m_9"} <= set(body["forgotten_ids"])  # m_9 was derived from m_2
    assert "m_3" not in body["forgotten_ids"]            # a sibling source survives
    assert "r_2" in body["runbook_steps_removed"]         # r_2 was built from m_9
    assert "r_2" not in {s["id"] for s in api.get("/runbook", headers=EXPERT).json()}
    mems = {m["id"]: m for m in api.get("/memories", headers=EXPERT).json()}
    assert mems["m_2"]["status"] == "forgotten" and "zeros" not in mems["m_2"]["text"]
    assert mems["m_3"]["status"] == "active"
    assert "g_2" not in {g["id"] for g in api.get("/gaps", headers=EXPERT).json()}
    audit = api.get("/audit", params={"limit": 10}, headers=EXPERT).json()
    assert any(a["action"] == "forget" and "m_2" in a["memory_ids"] for a in audit)
    again = api.post("/ask", json={"question": "How do I re-key a held payment on the LoanDesk backup screen?", "memory": True},
                     headers=SUCCESSOR).json()
    assert not {"m_2", "m_9"} & {s["memory"]["id"] for s in again["sources"]}


def test_clip_access(api):
    r = api.get("/clips/c_3", headers=OUTSIDER)
    assert r.status_code == 403
    assert api.get("/clips/c_3", headers=SUCCESSOR).status_code == 403  # only backs a never_transfer memory
    r = api.get("/clips/c_1", headers=SUCCESSOR)
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/") and len(r.content) > 10_000
    assert r.headers["x-content-type-options"] == "nosniff"
    assert api.get("/clips/c_1", params={"token": TOKENS["u_successor"]}).status_code == 200  # <audio src> fallback
    assert api.get("/clips/c_3", params={"token": TOKENS["u_successor"]}).status_code == 403
    assert api.get("/clips/c_missing", headers=EXPERT).status_code == 404


def test_upload_rejects_non_audio(api):
    sid = api.post("/sessions", json={"expert_id": "u_expert", "memory": False}, headers=EXPERT).json()["session_id"]
    r = api.post(f"/sessions/{sid}/answer", headers=EXPERT,
                 files={"audio": ("x.html", b"<script>alert(1)</script>", "text/html")})
    assert r.status_code == 415, r.text
    r = api.post(f"/sessions/{sid}/answer", headers=EXPERT,
                 files={"audio": ("x.svg", b"<svg onload=alert(1)>", "image/svg+xml")})
    assert r.status_code == 415


def test_interview_session_asks_about_seeded_gap(api):
    assert api.post("/sessions", json={"expert_id": "u_expert"}, headers=SUCCESSOR).status_code == 403
    r = api.post("/sessions", json={"expert_id": "u_expert"}, headers=EXPERT)
    assert r.status_code == 200, r.text
    start = r.json()
    assert set(start) == {"session_id", "first_question_text", "first_question_audio_url"}
    assert "database" in start["first_question_text"].lower()  # g_1, the contradiction from session 1
    assert_audio(api, start["first_question_audio_url"])

    if ANSWER_AUDIO:  # real recording -> ElevenLabs speech to text
        with open(ANSWER_AUDIO, "rb") as f:
            r = api.post(f"/sessions/{start['session_id']}/answer",
                         files={"audio": ("answer.mp3", f.read(), "audio/mpeg")}, headers=EXPERT)
    else:
        r = api.post(f"/sessions/{start['session_id']}/answer", data={"transcript": DANA_ANSWER},
                     files={"audio": ("answer.webm", b"", "audio/webm")}, headers=EXPERT)
    assert r.status_code == 200, r.text
    body = r.json()
    print("\nanswer response:", {k: v for k, v in body.items() if k != "memories_created"})
    print("memories created:", [m["kind"] + "/" + m["scope"] + ": " + m["text"] for m in body["memories_created"]])
    assert set(body) == {"transcript", "memories_created", "gaps_created", "next_question_text",
                         "next_question_audio_url", "used_memory_ids"}
    assert "lock" in body["transcript"].lower() and body["next_question_text"]
    assert_audio(api, body["next_question_audio_url"])
    assert body["memories_created"]
    for m in body["memories_created"]:
        assert_memory(m)
        assert m["session_id"] == start["session_id"]
    assert all(set(g) == GAP_KEYS for g in body["gaps_created"])
    gaps = {g["id"]: g for g in api.get("/gaps", headers=EXPERT).json()}
    assert gaps["g_1"]["status"] == "answered"


def test_interview_memory_off_ignores_gaps(api):
    r = api.post("/sessions", json={"expert_id": "u_expert", "memory": False}, headers=EXPERT)
    assert r.status_code == 200, r.text
    q = r.json()["first_question_text"].lower()
    assert "database" not in q and "zeros" not in q  # no session 1 knowledge


def test_live_websocket_pushes_changes(api):
    from websockets.sync.client import connect
    import json

    url = BASE.replace("http", "ws", 1) + "/live?token=" + TOKENS["u_expert"]
    with connect(url) as ws:
        api.patch("/memories/m_3/scope", json={"scope": "successor"}, headers=EXPERT)
        seen = set()
        for _ in range(6):
            try:
                msg = json.loads(ws.recv(timeout=15))
            except TimeoutError:
                break
            seen.add(msg["type"])
            if msg["type"] == "memory_changed":
                assert_memory(msg["memory"])
                assert msg["memory"]["id"] == "m_3" and msg["memory"]["scope"] == "successor"
            if seen >= {"memory_changed", "runbook_changed"}:
                break
        assert "memory_changed" in seen
    api.patch("/memories/m_3/scope", json={"scope": "team"}, headers=EXPERT)


def test_live_websocket_requires_token():
    from websockets.exceptions import ConnectionClosed
    from websockets.sync.client import connect

    with connect(BASE.replace("http", "ws", 1) + "/live?token=nope") as ws:
        assert ws.recv(timeout=10).startswith('{"type":"error"')
        with pytest.raises(ConnectionClosed) as closed:
            ws.recv(timeout=10)
        assert closed.value.rcvd.code == 4401
