"""The LLM provider chain: Groq first, Gemini as fallback, quota errors bench a model and move on."""
import json

import pytest
from pydantic import BaseModel

import detection
import extraction
import llm
from config import settings


class Answer(BaseModel):
    value: str


@pytest.fixture()
def chain(monkeypatch):
    """Two Groq models and one Gemini model, with every call recorded."""
    monkeypatch.setattr(settings, "LLM_PROVIDERS", ["groq", "gemini"])
    monkeypatch.setattr(settings, "GROQ_API_KEYS", ["gk"])
    monkeypatch.setattr(settings, "GROQ_MODEL", "big")
    monkeypatch.setattr(settings, "GROQ_FALLBACK_MODELS", ["small"])
    monkeypatch.setattr(settings, "GOOGLE_API_KEYS", ["ggk"])
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gem")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", [])
    monkeypatch.setattr(llm, "_benched", {})
    calls: list[str] = []
    replies: dict[str, object] = {}

    def fake(provider):
        def call(key, model, prompt, system, temperature, schema):
            calls.append(model)
            reply = replies.get(model, "ok")
            if isinstance(reply, Exception):
                raise reply
            return reply
        return call

    monkeypatch.setattr(llm, "_CALLERS", {"groq": fake("groq"), "gemini": fake("gemini")})
    return calls, replies


def test_uses_groq_first(chain):
    calls, _ = chain
    assert llm.generate_text("hi") == "ok"
    assert calls == ["big"]


def test_quota_error_benches_model_and_falls_back(chain):
    calls, replies = chain
    replies["big"] = llm._Retryable(429, "quota")
    assert llm.generate_text("hi") == "ok"
    assert calls == ["big", "small"]
    calls.clear()
    llm.generate_text("hi again")  # the benched model is skipped on the next call
    assert calls == ["small"]


def test_falls_through_to_gemini(chain):
    calls, replies = chain
    replies["big"] = llm._Retryable(429)
    replies["small"] = llm._Retryable(503)
    assert llm.generate_text("hi") == "ok"
    assert calls == ["big", "small", "gem"]


def test_every_provider_down_raises(chain):
    _, replies = chain
    for model in ("big", "small", "gem"):
        replies[model] = llm._Retryable(429)
    with pytest.raises(RuntimeError):
        llm.generate_text("hi")


def test_malformed_json_tries_next_model(chain):
    calls, replies = chain
    replies["big"] = "not json"
    replies["small"] = json.dumps({"value": "fine"})
    assert llm.generate_json("hi", Answer).value == "fine"
    assert calls == ["big", "small"]


def test_no_keys_means_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEYS", [])
    monkeypatch.setattr(settings, "GOOGLE_API_KEYS", [])
    assert not llm.llm_available()
    with pytest.raises(RuntimeError):
        llm.generate_text("hi")


@pytest.mark.parametrize("model", [extraction._Result, detection._Result])
def test_strict_schema_meets_structured_output_rules(model):
    schema = llm.strict_schema(model.model_json_schema())
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text

    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(schema)
