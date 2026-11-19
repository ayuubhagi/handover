"""Signed bearer tokens: identity comes from a token the server issued, never from a header."""
import time

import pytest

import auth
from errors import Unauthorized


def test_round_trip():
    token, exp = auth.issue_token("u_successor")
    assert auth.verify_token(token) == "u_successor"
    assert exp > time.time()


def test_tampered_payload_is_rejected():
    token, _ = auth.issue_token("u_outsider")
    payload, signature = token.split(".")
    forged, _ = auth.issue_token("u_expert")
    with pytest.raises(Unauthorized):
        auth.verify_token(f"{forged.split('.')[0]}.{signature}")  # intern's signature on the senior's payload


@pytest.mark.parametrize("token", [None, "", "abc", "a.b.c", "x.y"])
def test_malformed_tokens_are_rejected(token):
    with pytest.raises(Unauthorized):
        auth.verify_token(token)


def test_expired_token_is_rejected(monkeypatch):
    token, _ = auth.issue_token("u_successor")
    monkeypatch.setattr(time, "time", lambda: 10**12)
    with pytest.raises(Unauthorized):
        auth.verify_token(token)


def test_bearer_header_parsing():
    assert auth.bearer("Bearer abc.def") == "abc.def"
    assert auth.bearer("bearer  abc.def ") == "abc.def"
    assert auth.bearer("Basic abc") is None
    assert auth.bearer(None) is None
