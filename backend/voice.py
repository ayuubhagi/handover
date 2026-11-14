"""ElevenLabs speech to text for the expert, and the synthesized interviewer voice.

Only the interviewer is ever synthesized. The expert's voice is always their real recording.
"""
import logging

import httpx

import clips
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
    return (resp.json().get("text") or "").strip()


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
    """Synthesize the interviewer's question, store it as a clip, return its URL."""
    audio = synthesize(text)
    if not audio:
        return None
    clip = clips.save_clip(owner_id="interviewer", session_id=session_id, transcript=text, audio=audio,
                           content_type="audio/mpeg", speaker="interviewer")
    return clip_url(clip["_id"])
