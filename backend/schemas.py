"""$jsonSchema validators and index definitions for every collection."""
from pymongo import ASCENDING, DESCENDING, IndexModel

from config import settings

KINDS = ["procedure", "system", "client", "workaround"]
SCOPES = ["successor", "team", "never_transfer"]
MEMORY_STATUSES = ["active", "corrected", "forgotten"]
RUNBOOK_STATUSES = ["active", "needs_review", "removed"]
GAP_KINDS = ["missing", "contradiction"]
GAP_STATUSES = ["open", "asked", "answered"]
ROLES = ["senior", "junior", "intern"]

_str = {"bsonType": "string"}
_nonempty = {"bsonType": "string", "minLength": 1}
_str_list = {"bsonType": "array", "items": {"bsonType": "string"}}
_date = {"bsonType": "date"}

VALIDATORS = {
    "people": {
        "bsonType": "object",
        "required": ["_id", "name", "role", "team"],
        "properties": {
            "_id": _nonempty,
            "name": _nonempty,
            "role": {"enum": ROLES},
            "team": _nonempty,
            "successor_of": {"bsonType": ["string", "null"]},
        },
    },
    "clips": {
        "bsonType": "object",
        "required": ["_id", "owner_id", "speaker", "audio_url", "transcript", "session_id", "created_at"],
        "properties": {
            "_id": _nonempty,
            "owner_id": _nonempty,
            "speaker": {"enum": ["expert", "interviewer"]},
            "audio_url": _str,
            "transcript": _str,
            "session_id": _nonempty,
            "audio_file_id": {"bsonType": ["objectId", "null"]},
            "content_type": _str,
            "created_at": _date,
        },
    },
    # Every memory must say who owns it, who may inherit it, when it dies and which recording it came from.
    "memories": {
        "bsonType": "object",
        "required": [
            "_id", "owner_id", "kind", "text", "scope", "status", "version",
            "source_clip_id", "session_id", "created_at", "expires_at",
        ],
        "properties": {
            "_id": _nonempty,
            "owner_id": _nonempty,
            "kind": {"enum": KINDS},
            "text": _nonempty,
            "embedding": {
                "bsonType": "array",
                "minItems": settings.EMBED_DIMS,
                "maxItems": settings.EMBED_DIMS,
                "items": {"bsonType": "double"},
            },
            "scope": {"enum": SCOPES},
            "status": {"enum": MEMORY_STATUSES},
            "version": {"bsonType": "int", "minimum": 1},
            "supersedes": {"bsonType": ["string", "null"]},
            "derived_from": _str_list,
            "source_clip_id": _nonempty,
            "session_id": _nonempty,
            "created_at": _date,
            "expires_at": _date,
        },
    },
    "runbook_steps": {
        "bsonType": "object",
        "required": ["_id", "text", "derived_from", "status", "order"],
        "properties": {
            "_id": _nonempty,
            "text": _nonempty,
            "derived_from": _str_list,
            "status": {"enum": RUNBOOK_STATUSES},
            "order": {"bsonType": ["int", "long", "double"]},
            "created_at": _date,
            "updated_at": _date,
        },
    },
    "gaps": {
        "bsonType": "object",
        "required": ["_id", "owner_id", "question", "kind", "from_memory_ids", "status"],
        "properties": {
            "_id": _nonempty,
            "owner_id": _nonempty,
            "question": _nonempty,
            "kind": {"enum": GAP_KINDS},
            "from_memory_ids": _str_list,
            "status": {"enum": GAP_STATUSES},
            "session_id": {"bsonType": ["string", "null"]},
            "created_at": _date,
        },
    },
    "audit_log": {
        "bsonType": "object",
        "required": ["_id", "actor_id", "action", "memory_ids", "allowed", "reason", "ts"],
        "properties": {
            "_id": _nonempty,
            "actor_id": _nonempty,
            "action": _nonempty,
            "memory_ids": _str_list,
            "allowed": {"bsonType": "bool"},
            "reason": _str,
            "ts": _date,
            "detail": {"bsonType": "object"},
        },
    },
    "sessions": {
        "bsonType": "object",
        "required": ["_id", "expert_id", "memory_on", "status", "created_at"],
        "properties": {
            "_id": _nonempty,
            "expert_id": _nonempty,
            "memory_on": {"bsonType": "bool"},
            "status": {"enum": ["active", "closed"]},
            "turn": {"bsonType": ["int", "long"]},
            "created_at": _date,
        },
    },
}

INDEXES = {
    "memories": [
        # TTL: a memory is deleted by the server once expires_at passes.
        IndexModel([("expires_at", ASCENDING)], name="expires_at_ttl", expireAfterSeconds=0),
        IndexModel([("owner_id", ASCENDING), ("status", ASCENDING), ("scope", ASCENDING)], name="owner_status_scope"),
        IndexModel([("derived_from", ASCENDING)], name="derived_from"),
        IndexModel([("supersedes", ASCENDING)], name="supersedes"),
        IndexModel([("session_id", ASCENDING)], name="session"),
    ],
    "runbook_steps": [
        IndexModel([("derived_from", ASCENDING)], name="derived_from"),
        IndexModel([("status", ASCENDING), ("order", ASCENDING)], name="status_order"),
    ],
    "gaps": [IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)], name="owner_status")],
    "audit_log": [
        IndexModel([("ts", DESCENDING)], name="ts_desc"),
        IndexModel([("actor_id", ASCENDING), ("ts", DESCENDING)], name="actor_ts"),
    ],
    "clips": [IndexModel([("session_id", ASCENDING)], name="session")],
}

VECTOR_INDEX = "memories_vector"
TEXT_INDEX = "memories_text"

# Scope, owner, status and expiry are filter fields so leak prevention happens inside $vectorSearch.
VECTOR_INDEX_DEFINITION = {
    "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": settings.EMBED_DIMS, "similarity": "cosine"},
        {"type": "filter", "path": "owner_id"},
        {"type": "filter", "path": "scope"},
        {"type": "filter", "path": "status"},
        {"type": "filter", "path": "expires_at"},
    ]
}

# Keyword side of hybrid search (system names like "SWIFT queue"); token fields carry the same filters.
TEXT_INDEX_DEFINITION = {
    "mappings": {
        "dynamic": False,
        "fields": {
            "text": {"type": "string", "analyzer": "lucene.standard"},
            "owner_id": {"type": "token"},
            "scope": {"type": "token"},
            "status": {"type": "token"},
            "kind": {"type": "token"},
            "expires_at": {"type": "date"},
        },
    }
}
