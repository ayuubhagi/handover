"""Clip documents; audio bytes live in GridFS (bucket clip_audio)."""
import db
from models import clip_url, new_id, utcnow


def save_clip(*, owner_id: str, session_id: str, transcript: str, audio: bytes | None,
              content_type: str = "audio/mpeg", speaker: str = "expert", clip_id: str | None = None) -> dict:
    clip_id = clip_id or new_id("c")
    file_id = None
    if audio:
        file_id = db.audio_bucket().upload_from_stream(
            clip_id, audio, metadata={"content_type": content_type, "clip_id": clip_id}
        )
    doc = {
        "_id": clip_id,
        "owner_id": owner_id,
        "speaker": speaker,
        "audio_url": clip_url(clip_id),
        "transcript": transcript,
        "session_id": session_id,
        "audio_file_id": file_id,
        "content_type": content_type,
        "created_at": utcnow(),
    }
    db.col(db.CLIPS).insert_one(doc)
    return doc


def set_transcript(clip_id: str, transcript: str) -> None:
    db.col(db.CLIPS).update_one({"_id": clip_id}, {"$set": {"transcript": transcript}})


def get_clip(clip_id: str) -> dict | None:
    return db.col(db.CLIPS).find_one({"_id": clip_id})


def read_audio(clip: dict) -> tuple[bytes, str] | None:
    """(bytes, content_type), or None when the clip has no stored audio."""
    file_id = clip.get("audio_file_id")
    if not file_id:
        return None
    try:
        data = db.audio_bucket().open_download_stream(file_id).read()
    except Exception:
        return None
    return data, clip.get("content_type") or "audio/mpeg"


def delete_audio(clip: dict) -> None:
    file_id = clip.get("audio_file_id")
    if not file_id:
        return
    try:
        db.audio_bucket().delete(file_id)
    except Exception:
        pass
    db.col(db.CLIPS).update_one({"_id": clip["_id"]}, {"$set": {"audio_file_id": None}})
