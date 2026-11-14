"""Servers for the end to end run. Nothing here touches the demo servers on 8000 and 3000.

    backend   http://localhost:8001  MONGODB_DB=handover_e2e (seeded fresh)
    frontend  http://localhost:3001  a temporary copy of /frontend (its own .next), real API, no mocks

The frontend runs from a copy because a second `next dev` in /frontend would share .next/dev with the
running demo server. The copy links node_modules back to /frontend with a junction.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
FRONTEND = REPO / "frontend"
SCREENS = BACKEND / "e2e-screens"
LOGS = SCREENS / "logs"
PYTHON = sys.executable

E2E_DB = os.getenv("E2E_DB", "handover_e2e")
API_PORT = int(os.getenv("E2E_API_PORT", "8001"))
WEB_PORT = int(os.getenv("E2E_WEB_PORT", "3001"))
API = f"http://localhost:{API_PORT}"
WEB = f"http://localhost:{WEB_PORT}"
PROTECTED_PORTS = {8000, 3000}  # the running demo servers

sys.path.insert(0, str(BACKEND))
from config import settings  # noqa: E402  (same .env as the backend: passcodes, keys)


def _port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_http(url: str, timeout: float, ok=lambda r: r.status_code < 500) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=10)
            if ok(r):
                return
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as exc:
            last = repr(exc)
        time.sleep(1)
    raise RuntimeError(f"{url} not ready after {timeout:.0f}s ({last})")


def _kill_tree(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


class Backend:
    """The e2e backend, with stop/start so the test can take it down (section 4)."""

    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.env = {**os.environ, "MONGODB_DB": E2E_DB, "PUBLIC_BASE_URL": API, "PYTHONUNBUFFERED": "1"}
        self._log = None

    def seed(self) -> str:
        out = subprocess.run([PYTHON, "-W", "ignore", "seed.py"], cwd=BACKEND, env=self.env,
                             capture_output=True, text=True, timeout=600)
        (LOGS / "seed.log").write_text(out.stdout + out.stderr, encoding="utf-8")
        if out.returncode != 0 or "gaps: 2" not in out.stdout:
            raise RuntimeError(f"seed failed:\n{out.stdout[-2000:]}\n{out.stderr[-2000:]}")
        return out.stdout

    def start(self) -> None:
        assert API_PORT not in PROTECTED_PORTS
        if _port_in_use(API_PORT):
            raise RuntimeError(f"port {API_PORT} is already in use; stop that process first")
        self._log = open(LOGS / "backend.log", "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [PYTHON, "-W", "ignore", "-m", "uvicorn", "main:app", "--port", str(API_PORT)],
            cwd=BACKEND, env=self.env, stdout=self._log, stderr=subprocess.STDOUT,
        )
        _wait_http(f"{API}/health", 90, ok=lambda r: r.status_code == 200 and r.json().get("mongo"))

    def stop(self) -> None:
        _kill_tree(self.proc)
        self.proc = None
        if self._log:
            self._log.close()
            self._log = None
        deadline = time.time() + 20
        while _port_in_use(API_PORT) and time.time() < deadline:
            time.sleep(0.5)


def _remove_copy(path: Path) -> None:
    """Delete the frontend copy. The node_modules junction is unlinked first, so the real
    /frontend/node_modules is never touched."""
    if not path.exists():
        return
    link = path / "node_modules"
    if os.path.lexists(link):
        if os.path.isjunction(link) or os.path.islink(link):
            os.unlink(link) if os.path.islink(link) else os.rmdir(link)
        else:
            raise RuntimeError(f"{link} is a real directory, refusing to delete it")
    shutil.rmtree(path)


def _make_frontend_copy() -> Path:
    dest = Path(tempfile.gettempdir()) / "handover-e2e-frontend"
    _remove_copy(dest)
    shutil.copytree(FRONTEND, dest, ignore=shutil.ignore_patterns("node_modules", ".next", ".env.local", "*.log"))
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(dest / "node_modules"), str(FRONTEND / "node_modules")],
                       check=True, capture_output=True)
    else:
        os.symlink(FRONTEND / "node_modules", dest / "node_modules")
    # Turbopack must be allowed to resolve through the junction into the real node_modules.
    cfg = dest / "next.config.ts"
    root = os.path.commonpath([str(dest), str(FRONTEND)])
    text = cfg.read_text(encoding="utf-8")
    if "root: __dirname" in text:
        cfg.write_text(text.replace("root: __dirname", f"root: {json.dumps(root)}"), encoding="utf-8")
    return dest


@pytest.fixture(scope="session")
def servers():
    SCREENS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    for port in (API_PORT, WEB_PORT):
        assert port not in PROTECTED_PORTS
        if _port_in_use(port):
            raise RuntimeError(f"port {port} is already in use; stop that process first")

    backend = Backend()
    backend.seed()
    backend.start()

    copy = _make_frontend_copy()
    passcodes = ",".join(f"{k}:{v}" for k, v in settings.DEMO_PASSCODES.items())
    web_env = {**os.environ, "NEXT_PUBLIC_API_URL": API, "NEXT_PUBLIC_USE_MOCKS": "false",
               "NEXT_PUBLIC_DEMO_PASSCODES": passcodes, "NEXT_TELEMETRY_DISABLED": "1",
               "GOOGLE_API_KEY": settings.GOOGLE_API_KEY, "PORT": str(WEB_PORT)}
    web_log = open(LOGS / "frontend.log", "w", encoding="utf-8")
    web = subprocess.Popen(["node", str(copy / "node_modules" / "next" / "dist" / "bin" / "next"), "dev",
                            "--port", str(WEB_PORT)], cwd=copy, env=web_env, stdout=web_log, stderr=subprocess.STDOUT)
    try:
        _wait_http(WEB, 240, ok=lambda r: r.status_code == 200)
        yield {"backend": backend, "api": API, "web": WEB, "passcodes": settings.DEMO_PASSCODES}
    finally:
        _kill_tree(web)
        web_log.close()
        backend.stop()
        try:
            _remove_copy(copy)
        except Exception as exc:  # leave it for the next run rather than risk the real node_modules
            print(f"could not remove {copy}: {exc}")


# ---------------------------------------------------------------- per-beat results (shared with the tests)

RESULTS: dict[str, dict] = {}


def beat_of(name: str) -> str:
    """test_a_contradiction_question -> A, test_4c_backend_down -> 4C."""
    return name.split("_")[1].upper()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return
    entry = RESULTS.setdefault(beat_of(item.name), {"screens": []})
    if rep.failed:
        entry["result"] = "FAIL"
        msg = getattr(rep, "longreprtext", "") or str(rep.longrepr)
        lines = [l for l in msg.splitlines() if l.startswith("E ")] or msg.splitlines()[-1:]
        entry["note"] = " ".join(l[1:].strip() for l in lines)[:400]
    else:
        entry.setdefault("result", "PASS")
