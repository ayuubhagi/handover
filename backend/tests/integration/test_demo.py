"""Public demo hardening: passcode-free demo login only in DEMO_MODE, rate limits, and the in-place reset."""
import pytest

import ratelimit
from config import settings
from seed_facts import READABLE


@pytest.fixture()
def demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_RESET_ENABLED", True)
    monkeypatch.setattr(settings, "DEMO_RESET_MIN_INTERVAL_S", 0)


def test_demo_login_does_not_exist_outside_demo_mode(client, seeded):
    assert client.post("/demo/login", json={"user_id": "u_expert"}).status_code == 404
    assert client.post("/demo/reset").status_code == 404
    assert client.get("/demo").json() == {"demo_mode": False, "reset_enabled": False}


def test_demo_login_issues_a_short_lived_token_with_the_same_access_rules(client, seeded, demo_mode):
    resp = client.post("/demo/login", json={"user_id": "u_outsider"})
    assert resp.status_code == 200
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert {m["id"] for m in client.get("/memories", params={"owner_id": "u_expert"}, headers=headers).json()} \
        == READABLE["u_outsider"]
    assert client.post("/demo/login", json={"user_id": "u_nobody"}).status_code == 401


def test_rate_limit_returns_429(client, login, seeded, monkeypatch):
    headers = login("u_successor")
    ratelimit.reset()
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
    codes = [client.post("/ask", json={"question": "R7?"}, headers=headers).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    ratelimit.reset()


def test_reset_restores_the_demo_without_dropping_search_indexes(client, login, fresh, demo_mode, llm_spy):
    import db

    senior, junior = login("u_expert"), login("u_successor")
    client.post("/memories/m_2/forget", headers=senior)
    client.post("/memories/m_1/correct", json={"text": "Clear the locks first."}, headers=senior)
    client.patch("/memories/m_5/scope", json={"scope": "never_transfer"}, headers=senior)

    resp = client.post("/demo/reset")
    assert resp.status_code == 200, resp.text
    assert resp.json()["visitor_memories_removed"] == 1  # the corrected version of m_1

    assert {m["id"] for m in client.get("/memories", params={"owner_id": "u_expert"}, headers=junior).json()} \
        == READABLE["u_successor"]
    assert {s["id"] for s in client.get("/runbook", headers=junior).json()} == {"r_1", "r_2", "r_3", "r_4", "r_5"}
    assert all(s["status"] == "active" for s in client.get("/runbook", headers=junior).json())
    assert client.get("/clips/c_2", headers=junior).status_code == 200
    assert db.search_indexes_ready(), "a reset must not drop the Atlas Search indexes"
