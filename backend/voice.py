"""Speech to text for the expert (Groq Whisper or ElevenLabs Scribe), and the ElevenLabs interviewer voice.

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


def _stt_order() -> list[str]:
    """Configured provider first, the other as fallback, skipping any without a key."""
    keys = {"groq": bool(settings.GROQ_API_KEYS), "elevenlabs": bool(settings.ELEVENLABS_API_KEY)}
    order = [settings.STT_PROVIDER] + [p for p in ("groq", "elevenlabs") if p != settings.STT_PROVIDER]
    return [p for p in order if keys.get(p)]


def _stt_request(provider: str, audio: bytes, filename: str, content_type: str) -> str:
    if provider == "groq":
        resp = httpx.post(
            f"{settings.GROQ_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEYS[0]}"},
            data={"model": settings.GROQ_STT_MODEL, "response_format": "json", "language": "en"},
            files={"file": (filename, audio, content_type)},
            timeout=120,
        )
    else:
        resp = httpx.post(
            f"{API}/speech-to-text",
            headers=_headers(),
            data={"model_id": settings.ELEVENLABS_STT_MODEL},
            files={"file": (filename, audio, content_type)},
            timeout=120,
        )
    resp.raise_for_status()
    return (resp.json().get("text") or "").strip()


def transcribe(audio: bytes, filename: str = "answer.webm", content_type: str = "audio/webm") -> str:
    """Speech to text with Groq Whisper or ElevenLabs Scribe (STT_PROVIDER), falling back to the other."""
    providers = _stt_order()
    if not providers:
        raise BadRequest("No speech to text key (GROQ_API_KEY or ELEVENLABS_API_KEY); send a 'transcript' form field")
    digest = hashlib.sha256(audio).hexdigest()
    hit = cache.get("stt", digest)
    if hit is not None:
        return hit
    last: Exception | None = None
    for provider in providers:
        try:
            text = _stt_request(provider, audio, filename, content_type)
            cache.put("stt", text, digest)
            return text
        except httpx.HTTPError as exc:
            log.warning("speech to text via %s failed: %s", provider, exc)
            last = exc
    raise BadRequest(f"Speech to text failed: {last}")


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
