"""Settings loaded from the repo root .env (or the process environment)."""
import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


class Settings:
    MONGODB_URI = _get("MONGODB_URI")
    MONGODB_DB = _get("MONGODB_DB", "handover")

    VOYAGE_API_KEY = _get("VOYAGE_API_KEY")
    VOYAGE_BASE_URL = _get("VOYAGE_BASE_URL", "https://api.voyageai.com/v1")
    VOYAGE_MODEL = _get("VOYAGE_MODEL", "voyage-3.5")
    EMBED_DIMS = int(_get("EMBED_DIMS", "1024"))

    GOOGLE_API_KEY = _get("GOOGLE_API_KEY")
    # Optional extra keys (comma separated); llm.py rotates to the next key when one runs out of quota.
    GOOGLE_API_KEYS = list(dict.fromkeys(
        k.strip() for k in [_get("GOOGLE_API_KEY"), *_get("GOOGLE_API_KEYS").split(",")] if k.strip()))
    # LLM providers, tried in this order (llm.py benches one that runs out of quota and moves on).
    LLM_PROVIDERS = [p.strip().lower() for p in _get("LLM_PROVIDERS", "groq,gemini").split(",") if p.strip()]
    LLM_TIMEOUT_S = float(_get("LLM_TIMEOUT_S", _get("GEMINI_TIMEOUT_S", "20")))
    GROQ_API_KEYS = list(dict.fromkeys(
        k.strip() for k in [_get("GROQ_API_KEY"), *_get("GROQ_API_KEYS").split(",")] if k.strip()))
    GROQ_BASE_URL = _get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    GROQ_MODEL = _get("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_FALLBACK_MODELS = [m.strip() for m in _get("GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b").split(",")
                            if m.strip()]
    # Speech to text: "groq" (Whisper) or "elevenlabs" (Scribe). Falls back to the other when its key is missing.
    STT_PROVIDER = _get("STT_PROVIDER", "groq").lower()
    GROQ_STT_MODEL = _get("GROQ_STT_MODEL", "whisper-large-v3-turbo")

    GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODELS = [m.strip() for m in _get(
        "GEMINI_FALLBACK_MODELS", "gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash-lite"
    ).split(",") if m.strip()]

    ELEVENLABS_API_KEY = _get("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = _get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    ELEVENLABS_TTS_MODEL = _get("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")
    ELEVENLABS_STT_MODEL = _get("ELEVENLABS_STT_MODEL", "scribe_v1")

    PUBLIC_BASE_URL = _get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    MEMORY_TTL_DAYS = int(_get("MEMORY_TTL_DAYS", "365"))
    # /ask relevance cutoff on $vectorSearch scores ((1 + cosine) / 2): keep a memory when its score is at least
    # RELEVANCE_MIN and within RELEVANCE_MARGIN of the best match. Tuned on the voyage-3.5 demo seed.
    RELEVANCE_MIN = float(_get("RELEVANCE_MIN", "0.725"))
    RELEVANCE_MARGIN = float(_get("RELEVANCE_MARGIN", "0.10"))
    # Cache Gemini and ElevenLabs results for identical inputs (see cache.py).
    RESPONSE_CACHE = _get("RESPONSE_CACHE", "true").lower() not in ("0", "false", "no")
    CACHE_TTL_HOURS = int(_get("CACHE_TTL_HOURS", "24"))
    CORS_ORIGINS = [o.strip() for o in _get("CORS_ORIGINS", "*").split(",") if o.strip()]

    # Auth: HMAC secret for tokens, and "u_expert:code,u_successor:code,..." passcodes for /login.
    AUTH_SECRET = _get("AUTH_SECRET")
    TOKEN_TTL_SECONDS = int(_get("TOKEN_TTL_SECONDS", str(12 * 3600)))
    DEMO_PASSCODES = dict(
        pair.split(":", 1) for pair in _get("DEMO_PASSCODES").split(",") if ":" in pair
    )
    MAX_AUDIO_BYTES = int(_get("MAX_AUDIO_BYTES", str(25 * 1024 * 1024)))


settings = Settings()

# Tracing without a key only produces 401 noise; switch it off until LANGSMITH_API_KEY is set.
if not (_get("LANGSMITH_API_KEY") or _get("LANGCHAIN_API_KEY")):
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
