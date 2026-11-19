"""Unit tests never touch the network: every key is blanked before config is imported."""
import os

os.environ.update(
    MONGODB_URI="", GOOGLE_API_KEY="", GOOGLE_API_KEYS="", GROQ_API_KEY="", GROQ_API_KEYS="",
    VOYAGE_API_KEY="", ELEVENLABS_API_KEY="", LANGSMITH_API_KEY="", LANGCHAIN_API_KEY="",
    LANGSMITH_TRACING="false", AUTH_SECRET="unit-test-secret", RESPONSE_CACHE="false",
)

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *a, **k: False  # a developer's .env must not leak real keys into unit tests
