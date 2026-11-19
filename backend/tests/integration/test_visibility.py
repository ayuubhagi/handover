"""Each role sees exactly the memories, runbook steps, clips and gaps its scope allows, on every route."""
import pytest

from seed_facts import READABLE

ROLES = ["u_expert", "u_successor", "u_outsider"]
RUNBOOK = {  # step -> the memories it was derived from
    "r_1": {"m_1"}, "r_2": {"m_9"}, "r_3": {"m_6"}, "r_4": {"m_5"}, "r_5": {"m_8"}, "r_6": {"m_4"},
}
CLIP_OF = {"m_1": "c_1", "m_2": "c_2", "m_3": "c_2", "m_9": "c_2", "m_4": "c_3", "m_5": "c_4", "m_6": "c_5",
           "m_7": "c_6", "m_8": "c_7"}


@pytest.mark.parametrize("user", ROLES)
def test_memories_listing(client, login, seeded, user):
    resp = client.get("/memories", params={"owner_id": "u_expert"}, headers=login(user))
    assert resp.status_code == 200
    assert {m["id"] for m in resp.json()} == READABLE[user]


@pytest.mark.parametrize("user", ROLES)
def test_runbook_steps_inherit_their_strictest_source(client, login, seeded, user):
    resp = client.get("/runbook", headers=login(user))
    visible = {s["id"] for s in resp.json()}
    expected = {step for step, sources in RUNBOOK.items() if sources <= READABLE[user]}
    assert visible == expected


@pytest.mark.parametrize("user", ROLES)
def test_clip_access_follows_memory_access(client, login, seeded, user):
    headers = login(user)
    for clip in sorted(set(CLIP_OF.values())):
        cited_by = {m for m, c in CLIP_OF.items() if c == clip}
        status = client.get(f"/clips/{clip}", headers=headers).status_code
        if cited_by & READABLE[user]:
            assert status == 200, f"{user} should hear {clip}"
        else:
            assert status in (403, 404), f"{user} must not hear {clip} (got {status})"


def test_gaps_are_owner_only(client, login, seeded):
    assert len(client.get("/gaps", params={"owner_id": "u_expert"}, headers=login("u_expert")).json()) == 2
    for user in ("u_successor", "u_outsider"):
        assert client.get("/gaps", params={"owner_id": "u_expert"}, headers=login(user)).json() == []


def test_identity_comes_only_from_the_token(client, login, seeded):
    assert client.get("/memories", params={"owner_id": "u_expert"}).status_code == 401
    spoofed = client.get("/memories", params={"owner_id": "u_expert"},
                         headers={"X-User-Id": "u_expert", **login("u_outsider")})
    assert {m["id"] for m in spoofed.json()} == READABLE["u_outsider"]


def test_wrong_passcode_is_rejected_and_audited(client, login, seeded):
    assert client.post("/login", json={"user_id": "u_expert", "passcode": "guess"}).status_code == 401
    entries = client.get("/audit", params={"limit": 50}, headers=login("u_expert")).json()
    assert any(e["action"] == "login" and not e["allowed"] for e in entries)


@pytest.mark.parametrize("user", ["u_successor", "u_outsider"])
def test_only_the_owner_can_govern(client, login, seeded, user):
    headers = login(user)
    assert client.post("/memories/m_5/forget", headers=headers).status_code == 403
    assert client.patch("/memories/m_5/scope", json={"scope": "successor"}, headers=headers).status_code == 403
    assert client.post("/memories/m_5/correct", json={"text": "x"}, headers=headers).status_code == 403
