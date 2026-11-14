"""Change streams -> websocket hub, plus the TTL cascade worker.

One thread watches memories and runbook_steps. Every hide, correct or forget reaches the successor's
screen live, and a TTL delete of an expired memory triggers the same runbook cascade a forget does.
"""
import asyncio
import logging
import threading
import time

from fastapi import WebSocket
from pymongo.errors import OperationFailure, PyMongoError

import access
import db
from models import hidden_memory, iso, memory_out

log = logging.getLogger("handover.live")
PIPELINE = [{"$match": {"ns.coll": {"$in": [db.MEMORIES, db.RUNBOOK]}}}]
RUNBOOK_CHANGED = {"type": "runbook_changed"}


class LiveHub:
    def __init__(self):
        self._clients: dict[WebSocket, dict | None] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._resume_token = None
        self._pre_images = True

    # websocket side ---------------------------------------------------------
    async def connect(self, ws: WebSocket, viewer: dict | None) -> None:
        with self._lock:
            self._clients[ws] = viewer

    def disconnect(self, ws: WebSocket) -> None:
        with self._lock:
            self._clients.pop(ws, None)

    async def _send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            self.disconnect(ws)

    def _broadcast(self, build) -> None:
        """build(viewer) -> payload or None, evaluated per connection (redaction differs per viewer)."""
        if self._loop is None:
            return
        with self._lock:
            clients = list(self._clients.items())
        for ws, viewer in clients:
            try:
                payload = build(viewer)
            except Exception:
                log.exception("building live payload failed")
                continue
            if payload is not None:
                asyncio.run_coroutine_threadsafe(self._send(ws, payload), self._loop)

    # change stream side -----------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="change-stream", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _open(self):
        kwargs = {"full_document": "updateLookup"}
        if self._pre_images:
            kwargs["full_document_before_change"] = "whenAvailable"
        if self._resume_token:
            kwargs["resume_after"] = self._resume_token
        return db.get_db().watch(PIPELINE, **kwargs)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                with self._open() as stream:
                    log.info("change stream open")
                    while not self._stop.is_set() and stream.alive:
                        change = stream.try_next()
                        if change is None:
                            time.sleep(0.2)
                            continue
                        self._resume_token = stream.resume_token
                        self._handle(change)
            except OperationFailure as exc:
                if self._pre_images and "fullDocumentBeforeChange" in str(exc):
                    log.warning("pre-images unsupported, watching without them")
                    self._pre_images = False
                elif self._resume_token is not None:
                    log.warning("resume failed, starting a fresh change stream: %s", exc)
                    self._resume_token = None
                else:
                    log.warning("change stream error: %s", exc)
                time.sleep(2)
            except (PyMongoError, RuntimeError) as exc:
                log.warning("change stream unavailable, retrying: %s", exc)
                time.sleep(2)
            except Exception:
                log.exception("change stream crashed, restarting")
                time.sleep(2)

    def _handle(self, change: dict) -> None:
        coll = change["ns"]["coll"]
        op = change["operationType"]
        if coll == db.RUNBOOK:
            self._broadcast(lambda _v: RUNBOOK_CHANGED)
            return
        if op in ("insert", "update", "replace"):
            doc = change.get("fullDocument")
            if doc:
                mem = memory_out(doc)
                self._broadcast(lambda v: {"type": "memory_changed",
                                           "memory": mem if access.can_read(v, doc) else hidden_memory(mem)})
            fields = set((change.get("updateDescription") or {}).get("updatedFields") or {})
            if op != "update" or fields & {"scope", "status"}:
                self._broadcast(lambda _v: RUNBOOK_CHANGED)
        elif op == "delete":
            memory_id = change["documentKey"]["_id"]
            pre = change.get("fullDocumentBeforeChange")
            try:
                import governance

                governance.cascade_expired(memory_id, pre)
            except Exception:
                log.exception("expiry cascade failed for %s", memory_id)
            if pre:
                mem = {**hidden_memory(memory_out(pre)), "status": "forgotten"}
                self._broadcast(lambda _v: {"type": "memory_changed", "memory": mem})
            self._broadcast(lambda _v: RUNBOOK_CHANGED)


hub = LiveHub()
