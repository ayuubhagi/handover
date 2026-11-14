"""Every route in the TEAM.md API contract."""
from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

import access
import audit
import auth
import clips
import db
import governance
import interview
import retrieval
import voice
from config import settings
from errors import BadRequest, Forbidden, NotFound, PayloadTooLarge, Unauthorized, UnsupportedMedia
from live import hub
from models import AskBody, CorrectBody, ScopeBody, SessionCreate

router = APIRouter()

# Uploads are served back to browsers later, so only real audio types are stored.
AUDIO_TYPES = {
    "audio/webm", "audio/ogg", "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mp4", "audio/x-m4a", "audio/m4a", "audio/aac", "audio/flac", "audio/x-flac",
}


def viewer(authorization: str | None = Header(default=None)) -> dict:
    return auth.person_from_token(auth.bearer(authorization))


def viewer_or_query(authorization: str | None = Header(default=None), token: str | None = Query(default=None)) -> dict:
    # <audio src> cannot send headers, so the clip route also takes ?token=
    return auth.person_from_token(auth.bearer(authorization) or token)


class LoginBody(BaseModel):
    user_id: str
    passcode: str | None = None


@router.post("/login")
def login(body: LoginBody):
    return auth.login(body.user_id, body.passcode)


@router.get("/me")
def me_route(me: dict = Depends(viewer)):
    return {"id": me["_id"], "name": me["name"], "role": me["role"]}


def _audio_type(upload: UploadFile) -> str:
    ctype = (upload.content_type or "").split(";")[0].strip().lower()
    if ctype not in AUDIO_TYPES:
        raise UnsupportedMedia(f"Unsupported audio type '{ctype or 'unknown'}'")
    return ctype


# interview --------------------------------------------------------------------
@router.post("/sessions")
def create_session(body: SessionCreate, me: dict = Depends(viewer)):
    if me["_id"] != body.expert_id:
        raise Forbidden("Only the expert can start their own interview")
    started = interview.start_session(body.expert_id, memory_on=body.memory)
    return {
        "session_id": started["session_id"],
        "first_question_text": started["first_question_text"],
        "first_question_audio_url": voice.speak(started["first_question_text"], started["session_id"]),
    }


@router.post("/sessions/{session_id}/answer")
def answer(session_id: str, audio: UploadFile | None = File(default=None),
           transcript: str | None = Form(default=None), me: dict = Depends(viewer)):
    session = db.col(db.SESSIONS).find_one({"_id": session_id})
    if session is None:
        raise NotFound("Session not found")
    if session["expert_id"] != me["_id"]:
        raise Forbidden("Only the expert can answer in their interview")

    data = audio.file.read(settings.MAX_AUDIO_BYTES + 1) if audio is not None else b""
    if len(data) > settings.MAX_AUDIO_BYTES:
        raise PayloadTooLarge("Audio is larger than the upload limit")
    content_type = _audio_type(audio) if data else "audio/webm"
    if not data and not (transcript or "").strip():
        raise BadRequest("Send an audio file (or a transcript form field)")

    clip = clips.save_clip(owner_id=me["_id"], session_id=session_id, transcript=transcript or "",
                           audio=data or None, content_type=content_type, speaker="expert")
    if not (transcript or "").strip():
        transcript = voice.transcribe(data, audio.filename or "answer.webm", content_type)
        clips.set_transcript(clip["_id"], transcript)

    result = interview.submit_answer(session_id, transcript, clip["_id"])
    return {
        "transcript": transcript,
        "memories_created": result["memories_created"],
        "gaps_created": result["gaps_created"],
        "next_question_text": result["next_question_text"],
        "next_question_audio_url": voice.speak(result["next_question_text"], session_id),
        "used_memory_ids": result["used_memory_ids"],
    }


# memories and governance ----------------------------------------------------
@router.get("/memories")
def memories(owner_id: str | None = None, me: dict = Depends(viewer)):
    return governance.list_memories(me, owner_id or access.default_expert_id())


@router.patch("/memories/{memory_id}/scope")
def set_scope(memory_id: str, body: ScopeBody, me: dict = Depends(viewer)):
    return governance.set_scope(me, memory_id, body.scope)


@router.post("/memories/{memory_id}/correct")
def correct(memory_id: str, body: CorrectBody, me: dict = Depends(viewer)):
    return governance.correct_memory(me, memory_id, body.text)


@router.post("/memories/{memory_id}/forget")
def forget(memory_id: str, me: dict = Depends(viewer)):
    return governance.forget_memory(me, memory_id)


@router.post("/ask")
def ask(body: AskBody, me: dict = Depends(viewer)):
    return retrieval.ask(me, body.question, body.memory)


@router.get("/runbook")
def runbook(me: dict = Depends(viewer)):
    return governance.list_runbook(me)


@router.get("/audit")
def audit_log(limit: int = 20, me: dict = Depends(viewer)):
    return governance.list_audit(me, limit)


@router.get("/gaps")
def gaps(owner_id: str | None = None, me: dict = Depends(viewer)):
    return governance.list_gaps(me, owner_id or access.default_expert_id())


# clips ------------------------------------------------------------------------
@router.get("/clips/{clip_id}")
def get_clip(clip_id: str, me: dict = Depends(viewer_or_query)):
    clip = clips.get_clip(clip_id)
    if clip is None:
        raise NotFound("Clip not found")
    if clip["speaker"] == "expert" and me["_id"] != clip["owner_id"]:
        readable = {**access.readable_filter(me, clip["owner_id"]), "source_clip_id": clip_id}
        if db.col(db.MEMORIES).count_documents(readable, limit=1) == 0:
            audit.write_audit(me["_id"], "read_clip", [], False, f"no readable memory comes from clip {clip_id}")
            raise Forbidden("This recording is not shared with you")
    stored = clips.read_audio(clip)
    if stored is None:
        raise NotFound("No audio stored for this clip")
    data, content_type = stored
    if content_type not in AUDIO_TYPES:
        content_type = "application/octet-stream"
    # nosniff: the browser must treat the bytes as the declared audio type, never as HTML or script.
    return Response(content=data, media_type=content_type, headers={
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "private, max-age=300",
    })


# live -------------------------------------------------------------------------
@router.websocket("/live")
async def live(ws: WebSocket):
    await ws.accept()
    token = auth.bearer(ws.headers.get("authorization")) or ws.query_params.get("token")
    try:
        person = await run_in_threadpool(auth.person_from_token, token)
    except Unauthorized as exc:
        await ws.send_json({"type": "error", "detail": exc.detail})
        await ws.close(code=4401, reason="unauthorized")
        return
    except Exception:
        await ws.close(code=1011, reason="server error")
        return
    await hub.connect(ws, person)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
