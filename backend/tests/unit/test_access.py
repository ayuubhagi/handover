"""Who can read and govern which memory. These rules become the $vectorSearch pre-filter."""
from datetime import datetime, timedelta, timezone

import pytest

import access

NOW = datetime(2026, 11, 19, tzinfo=timezone.utc)
SENIOR = {"_id": "u_expert", "role": "senior", "team": "payments"}
JUNIOR = {"_id": "u_successor", "role": "junior", "team": "payments", "successor_of": "u_expert"}
INTERN = {"_id": "u_outsider", "role": "intern", "team": "payments"}
STRANGER = {"_id": "u_other", "role": "intern", "team": "treasury"}
PEOPLE = {p["_id"]: p for p in (SENIOR, JUNIOR, INTERN, STRANGER)}


@pytest.fixture(autouse=True)
def people(monkeypatch):
    monkeypatch.setattr(access, "get_person", lambda user_id: PEOPLE.get(user_id))


def memory(scope: str, *, status="active", expires=NOW + timedelta(days=30), owner="u_expert") -> dict:
    return {"_id": "m_x", "owner_id": owner, "scope": scope, "status": status, "expires_at": expires}


@pytest.mark.parametrize("viewer, expected", [
    (SENIOR, ["successor", "team", "never_transfer"]),
    (JUNIOR, ["successor", "team"]),
    (INTERN, ["team"]),
    (STRANGER, []),
    (None, []),
])
def test_allowed_scopes_by_role(viewer, expected):
    assert sorted(access.allowed_scopes(viewer, "u_expert")) == sorted(expected)


def test_never_transfer_only_reaches_the_owner():
    for viewer in (JUNIOR, INTERN, STRANGER):
        assert "never_transfer" not in access.allowed_scopes(viewer, "u_expert")
        assert not access.can_read(viewer, memory("never_transfer"), NOW)
    assert access.can_read(SENIOR, memory("never_transfer"), NOW)


def test_readable_filter_is_a_complete_prefilter():
    flt = access.readable_filter(INTERN, "u_expert", NOW)
    assert flt == {"owner_id": "u_expert", "status": "active", "scope": {"$in": ["team"]}, "expires_at": {"$gt": NOW}}


def test_stranger_filter_matches_nothing():
    assert access.readable_filter(STRANGER, "u_expert", NOW)["scope"] == {"$in": []}


@pytest.mark.parametrize("mem", [
    memory("team", status="forgotten"),
    memory("team", status="superseded"),
    memory("team", expires=NOW - timedelta(seconds=1)),
])
def test_inactive_or_expired_memories_are_unreadable_to_others(mem):
    assert not access.can_read(JUNIOR, mem, NOW)
    assert not access.can_read(INTERN, mem, NOW)


def test_owner_can_always_read_and_only_owner_can_govern():
    hidden = memory("never_transfer", status="forgotten")
    assert access.can_read(SENIOR, hidden, NOW)
    assert access.can_govern(SENIOR, hidden)
    for viewer in (JUNIOR, INTERN, STRANGER, None):
        assert not access.can_govern(viewer, memory("team"))
