"""Shared test setup: put backend/ on the import path.

Test layout:
  tests/unit/         pure logic, no database or API keys (access rules, tokens, LLM provider chain)
  tests/integration/  the real FastAPI app on a real MongoDB with Atlas Search + Vector Search
                      (mongodb-atlas-local in CI, docker compose locally); no API keys needed
  tests/test_contract.py, tests/e2e/   against a running server with real Atlas and real API keys
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
