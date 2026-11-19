"""Signed bearer tokens. Identity comes from a token the server issued, never from a header the browser asserts.

POST /login checks the demo user's passcode (DEMO_PASSCODES in .env) and returns
    <base64url(json {"sub", "exp"})>.<base64url(HMAC-SHA256(AUTH_SECRET, payload))>
Every other route verifies the signature and expiry, then loads the person from MongoDB.
"""
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

import access
import audit
from config import settings
from errors import Unauthorized

log = logging.getLogger("handover.auth")

_secret = settings.AUTH_SECRET.encode() if settings.AUTH_SECRET else None
if _secret is None:
    _secret = secrets.token_bytes(32)
    log.warning("AUTH_SECRET not set: using a random per-process secret, tokens reset on every restart")
if not settings.DEMO_PASSCODES:
    log.warning("DEMO_PASSCODES not set: /login accepts any seeded user without a passcode (dev only)")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(_secret, payload.encode(), hashlib.sha256).digest())


def issue_token(user_id: str, ttl_seconds: int | None = None) -> tuple[str, int]:
    exp = int(time.time()) + (settings.TOKEN_TTL_SECONDS if ttl_seconds is None else ttl_seconds)
    payload = _b64(json.dumps({"sub": user_id, "exp": exp}, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload)}", exp


def verify_token(token: str | None) -> str:
    """Returns the user id inside a valid, unexpired token."""
    if not token or token.count(".") != 1:
        raise Unauthorized("Missing or malformed token; POST /login first")
    payload, signature = token.split(".")
    if not hmac.compare_digest(signature, _sign(payload)):
        raise Unauthorized("Invalid token signature")
    try:
        claims = json.loads(_unb64(payload))
    except ValueError as exc:
        raise Unauthorized("Malformed token") from exc
    if int(claims.get("exp", 0)) < time.time():
        raise Unauthorized("Token expired; log in again")
    return str(claims["sub"])


def login(user_id: str, passcode: str | None) -> dict:
    person = access.get_person(user_id)
    expected = settings.DEMO_PASSCODES.get(user_id)
    if person is None or (settings.DEMO_PASSCODES and not hmac.compare_digest(passcode or "", expected or "")):
        if person is not None:
            audit.write_audit(user_id, "login", [], False, "wrong passcode")
        raise Unauthorized("Unknown user or wrong passcode")
    token, exp = issue_token(user_id)
    return {"token": token, "expires_at": exp,
            "user": {"id": person["_id"], "name": person["name"], "role": person["role"]}}


def demo_login(user_id: str) -> dict:
    """Public demo only (DEMO_MODE): pick a seeded role without a passcode, get a short-lived token."""
    person = access.get_person(user_id)
    if person is None:
        raise Unauthorized("Unknown demo user")
    token, exp = issue_token(user_id, settings.DEMO_TOKEN_TTL_SECONDS)
    return {"token": token, "expires_at": exp,
            "user": {"id": person["_id"], "name": person["name"], "role": person["role"]}}


def person_from_token(token: str | None) -> dict:
    return access.require_person(verify_token(token))


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None
