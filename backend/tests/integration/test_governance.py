"""Forget, correct, re-scope and expiry, checked from the other roles' point of view afterwards."""
from datetime import timedelta

from models import utcnow


def ids(client, headers, path="/memories"):
    return {m["id"] for m in client.get(path, params={"owner_id": "u_expert"}, headers=headers).json()}


def test_forget_cascades_to_derived_memories_steps_and_gaps(client, login, fresh, llm_spy):
    senior, junior = login("u_expert"), login("u_successor")
    resp = client.post("/memories/m_2/forget", headers=senior)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["forgotten_ids"]) == {"m_2", "m_9"}  # m_9 was derived from m_2
    assert body["runbook_steps_removed"] == ["r_2"]       # r_2 was built on m_9
    assert "m_2" not in ids(client, junior) and "m_9" not in ids(client, junior)
    assert "r_2" not in {s["id"] for s in client.get("/runbook", headers=junior).json()}
    assert all("m_2" not in g["from_memory_ids"] for g in client.get(
        "/gaps", params={"owner_id": "u_expert"}, headers=senior).json())

    llm_spy.prompts.clear()
    answer = client.post("/ask", json={"question": "How do I push a sanctions-held payment through the backup "
                                                   "screen?"}, headers=junior).json()
    assert not {"m_2", "m_9"} & {s["memory"]["id"] for s in answer["sources"]}
    assert not any("sanctions screening, re-key" in p for p in llm_spy.prompts)

    forget = next(e for e in client.get("/audit", headers=senior).json() if e["action"] == "forget")
    assert forget["allowed"] and set(forget["memory_ids"]) == {"m_2", "m_9"}


def test_forget_keeps_a_recording_another_memory_still_cites(client, login, fresh):
    client.post("/memories/m_2/forget", headers=login("u_expert"))
    assert client.get("/clips/c_2", headers=login("u_successor")).status_code == 200  # m_3 still cites c_2


def test_correction_versions_the_memory_and_flags_dependent_steps(client, login, fresh):
    senior, junior = login("u_expert"), login("u_successor")
    resp = client.post("/memories/m_1/correct", json={"text": "Clear the ledger locks first, then restart the "
                                                              "payments queue."}, headers=senior)
    assert resp.status_code == 200
    old, new = resp.json()["old"], resp.json()["new"]
    assert old["status"] == "corrected" and new["supersedes"] == "m_1" and new["version"] == old["version"] + 1
    visible = ids(client, junior)
    assert new["id"] in visible and "m_1" not in visible
    step = next(s for s in client.get("/runbook", headers=junior).json() if s["id"] == "r_1")
    assert step["status"] == "needs_review" and step["derived_from"] == [new["id"]]


def test_rescoping_takes_effect_immediately(client, login, fresh):
    senior, intern = login("u_expert"), login("u_outsider")
    assert "m_5" in ids(client, intern)
    assert client.patch("/memories/m_5/scope", json={"scope": "successor"}, headers=senior).status_code == 200
    assert "m_5" not in ids(client, intern)
    assert "r_4" not in {s["id"] for s in client.get("/runbook", headers=intern).json()}
    assert "m_5" in ids(client, login("u_successor"))


def test_expired_memories_are_filtered_before_the_ttl_monitor_deletes_them(client, login, fresh):
    import db

    db.col(db.MEMORIES).update_one({"_id": "m_8"}, {"$set": {"expires_at": utcnow() - timedelta(minutes=1)}})
    intern = login("u_outsider")
    assert "m_8" not in ids(client, intern)
    assert "r_5" not in {s["id"] for s in client.get("/runbook", headers=intern).json()}


def test_interview_turn_creates_governed_memories(client, login, fresh):
    senior = login("u_expert")
    session = client.post("/sessions", json={"expert_id": "u_expert"}, headers=senior)
    assert session.status_code == 200
    sid = session.json()["session_id"]
    answer = client.post(f"/sessions/{sid}/answer", headers=senior, data={
        "transcript": "Every Monday I export the SWIFT exceptions report from LedgerOne and email it to the "
                      "compliance team before nine."})
    assert answer.status_code == 200, answer.text
    created = answer.json()["memories_created"]
    assert created, "the heuristic extractor should save at least one memory"
    for memory in created:
        assert memory["owner_id"] == "u_expert"
        assert memory["scope"] in ("successor", "team", "never_transfer")
        assert memory["expires_at"]
    assert client.post(f"/sessions/{sid}/answer", headers=login("u_successor"),
                       data={"transcript": "hi"}).status_code in (401, 403)
