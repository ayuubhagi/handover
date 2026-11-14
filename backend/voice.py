"""ElevenLabs speech to text for the expert, and the synthesized interviewer voice.

Only the interviewer is ever synthesized. The expert's voice is always their real recording.
Both calls reuse earlier results for identical input, so rehearsals don't spend ElevenLabs credits twice.
"""
import hashlib
import logging

import httpx

import cache
import clips
import db
from config import settings
from errors import BadRequest
from models import clip_url

log = logging.getLogger("handover.voice")
API = "https://api.elevenlabs.io/v1"


def _headers() -> dict:
    return {"xi-api-key": settings.ELEVENLABS_API_KEY}


def transcribe(audio: bytes, filename: str = "answer.webm", content_type: str = "audio/webm") -> str:
    if not settings.ELEVENLABS_API_KEY:
        raise BadRequest("ELEVENLABS_API_KEY is not set; send a 'transcript' form field instead")
    digest = hashlib.sha256(audio).hexdigest()
    hit = cache.get("stt", digest, settings.ELEVENLABS_STT_MODEL)
    if hit is not None:
        return hit
    try:
        resp = httpx.post(
            f"{API}/speech-to-text",
            headers=_headers(),
            data={"model_id": settings.ELEVENLABS_STT_MODEL},
            files={"file": (filename, audio, content_type)},
            timeout=120,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BadRequest(f"Speech to text failed: {exc}") from exc
    text = (resp.json().get("text") or "").strip()
    cache.put("stt", text, digest, settings.ELEVENLABS_STT_MODEL)
    return text


def synthesize(text: str) -> bytes | None:
    if not settings.ELEVENLABS_API_KEY or not text:
        return None
    try:
        resp = httpx.post(
            f"{API}/text-to-speech/{settings.ELEVENLABS_VOICE_ID}",
            params={"output_format": "mp3_44100_128"},
            headers=_headers(),
            json={"text": text, "model_id": settings.ELEVENLABS_TTS_MODEL},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError as exc:
        log.warning("interviewer voice failed: %s", exc)
        return None


def speak(text: str, session_id: str) -> str | None:
    """The interviewer's question as audio: reuse a stored recording of the same text, else synthesize and store it."""
    if settings.RESPONSE_CACHE:
        existing = db.col(db.CLIPS).find_one(
            {"speaker": "interviewer", "transcript": text, "audio_file_id": {"$ne": None}}, {"_id": 1})
        if existing:
            log.info("cache hit: interviewer voice")
            return clip_url(existing["_id"])
    audio = synthesize(text)
    if not audio:
        return None
    clip = clips.save_clip(owner_id="interviewer", session_id=session_id, transcript=text, audio=audio,
                           content_type="audio/mpeg", speaker="interviewer")
    return clip_url(clip["_id"])
