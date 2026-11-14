"""MongoDB Atlas connection, collection handles, schema + index setup, transactions, GridFS."""
import logging
import time
from typing import Callable, TypeVar

import gridfs
from pymongo import MongoClient
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import OperationFailure
from pymongo.operations import SearchIndexModel
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

import schemas
from config import settings
from errors import HandoverError

log = logging.getLogger("handover.db")


class DatabaseUnavailable(HandoverError):
    status_code = 503

PEOPLE = "people"
CLIPS = "clips"
MEMORIES = "memories"
RUNBOOK = "runbook_steps"
GAPS = "gaps"
AUDIT = "audit_log"
SESSIONS = "sessions"
VECTOR_INDEX = schemas.VECTOR_INDEX
TEXT_INDEX = schemas.TEXT_INDEX

T = TypeVar("T")
_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.MONGODB_URI:
            raise DatabaseUnavailable("MONGODB_URI is not set. Copy .env.example to .env and add the Atlas connection string.")
        _client = MongoClient(
            settings.MONGODB_URI,
            appname="handover-backend",
            tz_aware=True,
            retryWrites=True,
            serverSelectionTimeoutMS=15000,
        )
    return _client


def get_db() -> Database:
    return get_client()[settings.MONGODB_DB]


def col(name: str) -> Collection:
    return get_db()[name]


def ping() -> bool:
    get_client().admin.command("ping")
    return True


def audio_bucket() -> gridfs.GridFSBucket:
    return gridfs.GridFSBucket(get_db(), bucket_name="clip_audio")


def run_in_transaction(fn: Callable[[ClientSession], T]) -> T:
    """Run fn(session) in one multi-document transaction (retries transient errors)."""
    with get_client().start_session() as session:
        return session.with_transaction(
            fn,
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority"),
        )


def _ensure_collection(name: str, validator: dict) -> None:
    database = get_db()
    schema = {"$jsonSchema": validator}
    info = next(database.list_collections(filter={"name": name}), None)
    if info is None:
        database.create_collection(name, validator=schema, validationLevel="strict", validationAction="error")
        return
    if info.get("options", {}).get("validator") == schema:
        return
    try:
        database.command("collMod", name, validator=schema, validationLevel="strict", validationAction="error")
    except OperationFailure as exc:
        # collMod needs dbAdmin; a readWrite user keeps the validator set when the collection was created.
        log.warning("could not update validator on %s (%s); drop the collection or use a dbAdmin user",
                    name, exc.details.get("codeName") if exc.details else exc)


def _ensure_search_index(name: str, definition: dict, index_type: str) -> None:
    coll = col(MEMORIES)
    existing = {ix["name"]: ix for ix in coll.list_search_indexes()}
    if name not in existing:
        coll.create_search_index(SearchIndexModel(definition=definition, name=name, type=index_type))
        log.info("created %s index %s", index_type, name)
    elif existing[name].get("latestDefinition") != definition:
        coll.update_search_index(name, definition)
        log.info("updated %s index %s", index_type, name)


def search_indexes_ready() -> bool:
    try:
        states = {ix["name"]: ix.get("queryable", False) for ix in col(MEMORIES).list_search_indexes()}
    except OperationFailure:
        return False
    return bool(states.get(VECTOR_INDEX)) and bool(states.get(TEXT_INDEX))


def wait_for_search_indexes(timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if search_indexes_ready():
            return True
        time.sleep(3)
    return False


def ensure_schema(wait_for_search: bool = False) -> None:
    """Idempotent: validators, regular + TTL indexes, change stream pre-images, Search + Vector Search indexes."""
    for name, validator in schemas.VALIDATORS.items():
        _ensure_collection(name, validator)
    for name, models in schemas.INDEXES.items():
        col(name).create_indexes(models)
    try:
        # Lets the change stream hand us the document that a TTL delete just removed.
        get_db().command("collMod", MEMORIES, changeStreamPreAndPostImages={"enabled": True})
    except OperationFailure as exc:
        log.warning("change stream pre-images not enabled on memories (%s); TTL deletes arrive without the old doc",
                    exc.details.get("codeName") if exc.details else exc)
    try:
        _ensure_search_index(VECTOR_INDEX, schemas.VECTOR_INDEX_DEFINITION, "vectorSearch")
        _ensure_search_index(TEXT_INDEX, schemas.TEXT_INDEX_DEFINITION, "search")
    except OperationFailure as exc:
        log.error("could not create search indexes: %s", exc)
        return
    if wait_for_search and not wait_for_search_indexes():
        log.warning("search indexes are still building")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ping()
    ensure_schema(wait_for_search=True)
    print("schema ok, search indexes ready:", search_indexes_ready())
