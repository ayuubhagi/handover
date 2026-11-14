"""Handover API. Run from backend/:  uvicorn main:app --reload"""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ConfigurationError, ConnectionFailure

import db
from config import settings
from errors import HandoverError
from live import hub
from routes import router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("handover")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(db.ensure_schema)
    except Exception as exc:
        log.warning("could not prepare the database (is MONGODB_URI set?): %s", exc)
    hub.start(asyncio.get_running_loop())
    yield
    hub.stop()


def _error_status(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, HandoverError):
        return exc.status_code, exc.detail
    if isinstance(exc, (ConnectionFailure, ConfigurationError)):
        return 503, "Database unavailable; check MONGODB_URI and Atlas network access"
    if isinstance(exc, httpx.HTTPError):
        return 502, f"Upstream service error: {exc.__class__.__name__}"
    return 500, f"Internal server error ({exc.__class__.__name__})"


class JSONErrors:
    """Turns any unhandled exception into a JSON error. It sits inside CORSMiddleware, so the browser
    sees the real message and status instead of a CORS-blocked 'network error'."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception as exc:
            status, detail = _error_status(exc)
            log.exception("%s %s failed", scope.get("method"), scope.get("path"))
            if started:
                raise
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)


app = FastAPI(title="Handover API", lifespan=lifespan)
app.add_middleware(JSONErrors)  # added first = runs inside CORS

_all = settings.CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _all else settings.CORS_ORIGINS,
    allow_credentials=not _all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HandoverError)
async def handover_error(_: Request, exc: HandoverError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/health")
def health():
    try:
        mongo = db.ping()
    except Exception:
        mongo = False
    return {"ok": True, "mongo": mongo}


app.include_router(router)
