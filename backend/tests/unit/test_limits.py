"""Rate limiter and the daily LLM budget that keep a public demo inside its free tiers."""
import pytest

import llm
import ratelimit
from config import settings


def test_sliding_window_per_client():
    ratelimit.reset()
    for _ in range(3):
        ratelimit.check("1.2.3.4", "ask", 3)
    with pytest.raises(ratelimit.TooManyRequests):
        ratelimit.check("1.2.3.4", "ask", 3)
    ratelimit.check("5.6.7.8", "ask", 3)   # other clients are unaffected
    ratelimit.check("1.2.3.4", "login", 3)  # and so are other buckets
    ratelimit.reset()


def test_zero_disables_the_limit():
    for _ in range(100):
        ratelimit.check("1.2.3.4", "ask", 0)


def test_daily_budget_switches_to_the_fallback_path(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEYS", ["k"])
    monkeypatch.setattr(settings, "LLM_PROVIDERS", ["groq"])
    monkeypatch.setattr(settings, "LLM_DAILY_BUDGET", 2)
    monkeypatch.setattr(llm, "_budget", {"day": "", "used": 0})
    monkeypatch.setattr(llm, "_CALLERS", {"groq": lambda *a: "ok"})
    assert llm.generate_text("one") == "ok"
    assert llm.generate_text("two") == "ok"
    assert not llm.llm_available()
    with pytest.raises(RuntimeError):
        llm.generate_text("three")
