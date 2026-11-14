"""Handover API. Run from backend/:  uvicorn main:app --reload"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


app = FastAPI(title="Handover API", lifespan=lifespan)

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
