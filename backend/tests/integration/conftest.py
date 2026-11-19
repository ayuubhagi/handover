"""Integration tests: the real FastAPI app on a real MongoDB with Atlas Search and Vector Search.

    docker compose up -d mongodb          # mongodb/mongodb-atlas-local, from the repo root
    cd backend && pytest tests/integration

No API keys are needed. Embeddings use the hashed dev fallback and the LLM is replaced by a spy that records
every prompt, so the tests can prove what reached the model, not just what came back. The relevance cutoff is
switched off so that retrieval returns every memory the access filter allows: the filter is what is under test.
"""
import os
import time

import pytest

os.environ.update(
    MONGODB_URI=os.environ.get("TEST_MONGODB_URI", "mongodb://localhost:27017/?directConnection=true"),
    MONGODB_DB="handover_it",
    GOOGLE_API_KEY="", GOOGLE_API_KEYS="", GROQ_API_KEY="", GROQ_API_KEYS="", VOYAGE_API_KEY="",
    ELEVENLABS_API_KEY="", LANGSMITH_API_KEY="", LANGCHAIN_API_KEY="", LANGSMITH_TRACING="false",
    DEMO_PASSCODES="u_expert:dana-pass,u_successor:sam-pass,u_outsider:jordan-pass",
    AUTH_SECRET="integration-secret", RESPONSE_CACHE="false",
    RELEVANCE_MIN="0", RELEVANCE_MARGIN="2", RATE_LIMIT_PER_MINUTE="100000", DEMO_RESET_ENABLED="false",
)

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *a, **k: False

from seed_facts import PASSCODES  # noqa: E402,F401  (re-exported for tests)



def _mongo_reachable() -> bool:
    from pymongo import MongoClient

    try:
        MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=3000).admin.command("ping")
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    if not _mongo_reachable():
        skip = pytest.mark.skip(reason="no MongoDB at TEST_MONGODB_URI (run: docker compose up -d mongodb)")
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip)


class LLMSpy:
    """Stands in for the LLM. Records every prompt so a test can check restricted text never reached it."""

    def __init__(self):
        self.prompts: list[str] = []

    def generate_text(self, prompt, *, system=None, temperature=0.2):
        self.prompts.append(f"{system or ''}\n{prompt}")
        return "Answer drafted from the memories provided."

    def generate_json(self, prompt, schema, *, system=None, temperature=0.1):
        self.prompts.append(f"{system or ''}\n{prompt}")
        return schema.model_validate({name: [] for name in schema.model_fields})


@pytest.fixture()
def llm_spy(monkeypatch):
    import llm

    spy = LLMSpy()
    monkeypatch.setattr(llm, "llm_available", lambda: True)
    monkeypatch.setattr(llm, "generate_text", spy.generate_text)
    monkeypatch.setattr(llm, "generate_json", spy.generate_json)
    return spy


def _seed():
    import retrieval
    import seed

    result = seed.seed()
    assert result["search_indexes_ready"], "Atlas Search / Vector Search indexes never became queryable"
    retrieval._failed_until.clear()
    retrieval._indexes_ready = False
    retrieval._indexes_checked_at = 0.0
    time.sleep(1)  # let mongot catch up with the freshly inserted documents
    return result


@pytest.fixture(scope="session")
def _seeded_once():
    return _seed()


@pytest.fixture()
def seeded(_seeded_once):
    """Seeded data shared by read-only tests. Tests that change data use `fresh` instead."""
    return _seeded_once


@pytest.fixture()
def fresh(_seeded_once):
    """Reseed after the test so the next one starts clean."""
    yield
    _seed()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def login(client):
    def _login(user_id: str) -> dict:
        resp = client.post("/login", json={"user_id": user_id, "passcode": PASSCODES[user_id]})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['token']}"}

    return _login
