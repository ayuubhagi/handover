from datetime import datetime, timedelta, timezone

import retrieval


class _GapCollection:
    def find(self, query):
        assert query == {"owner_id": "u_expert", "status": {"$in": ["open", "asked"]}}
        return [
            {
                "_id": "g_visible",
                "owner_id": "u_expert",
                "question": "Do I clear the locks or restart the queue first?",
                "kind": "contradiction",
                "from_memory_ids": ["m_1"],
                "status": "open",
            },
            {
                "_id": "g_hidden",
                "owner_id": "u_expert",
                "question": "What is the private client exception?",
                "kind": "missing",
                "from_memory_ids": ["m_private"],
                "status": "open",
            },
        ]


def test_ask_surfaces_only_open_gaps_backed_by_retrieved_memories(monkeypatch):
    now = datetime.now(timezone.utc)
    memory = {
        "_id": "m_1",
        "owner_id": "u_expert",
        "kind": "procedure",
        "text": "Restart the payments queue before touching the ledger database.",
        "scope": "successor",
        "status": "active",
        "version": 1,
        "supersedes": None,
        "derived_from": [],
        "source_clip_id": "c_1",
        "session_id": "s_1",
        "created_at": now,
        "expires_at": now + timedelta(days=30),
        "_score": 1.0,
    }

    monkeypatch.setattr(retrieval.access, "default_expert_id", lambda: "u_expert")
    monkeypatch.setattr(retrieval.access, "allowed_scopes", lambda viewer, owner: ["successor", "team"])
    monkeypatch.setattr(retrieval.access, "get_person", lambda owner: {"name": "Dana"})
    monkeypatch.setattr(retrieval, "_query_vector", lambda question, embedding: None)
    monkeypatch.setattr(retrieval, "_search", lambda *args, **kwargs: ([memory], "keyword"))
    monkeypatch.setattr(retrieval, "_count_blocked", lambda *args, **kwargs: set())
    monkeypatch.setattr(retrieval.db, "col", lambda name: _GapCollection())
    monkeypatch.setattr(retrieval.llm, "llm_available", lambda: False)
    monkeypatch.setattr(retrieval.audit, "write_audit", lambda *args, **kwargs: "a_1")
    monkeypatch.setattr(retrieval, "_annotate_trace", lambda **kwargs: None)
    monkeypatch.setattr(retrieval, "_trace_url", lambda: None)

    answer = retrieval.ask({"_id": "u_successor", "name": "Sam"}, "What comes first?")["answer_text"]

    assert "Open question: Do I clear the locks or restart the queue first?" in answer
    assert "private client exception" not in answer
