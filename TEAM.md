# TEAM.md: the single source of truth between us

Every person's AI assistant reads this file first and writes here when it needs something from someone else.
Read PLAN.md for the idea, judging, and checklist.

## Ownership (only edit your own folder)

| Folder | Owner | Job |
|---|---|---|
| /backend | Ayuub | FastAPI, MongoDB Atlas, memory engine, agent loop, ElevenLabs/Voyage/Gemini calls |
| /frontend | Harsh | React (Vite) UI: Expert, Successor, Memory On vs Off |
| /demo | Keith | Scripts, recordings, pitch, video plan, judge Q&A, project description, deploy |

Root files (PLAN.md, README.md, TEAM.md, .gitignore, .env.example): anyone can append to TEAM.md; ask in the team chat before editing the others.

## Rules for every AI assistant working in this repo
1. Only create or edit files inside your owner's folder. Never touch another folder.
2. If you need something from another folder (a new endpoint, a field, a file), add a line under "Requests" below with your name. Do not build it yourself.
3. The API contract below is the only way frontend and backend talk. Backend implements it exactly; frontend mocks it exactly. Changing it means updating this file first and posting in the team chat.
4. Never commit .env, keys, or real personal data. All demo data is fictional.
5. Pull before you push. Small commits. Commit messages say what changed, no AI references, no co-author lines.

## API contract (base URL: http://localhost:8000)

People (seeded): expert `u_expert` (Dana, retiring ops lead), successor `u_successor` (Sam), outsider `u_outsider` (Riley, another team).
Every request sends header `X-User-Id` with one of those ids.

Memory object:
```json
{
  "id": "m_123",
  "owner_id": "u_expert",
  "kind": "procedure | system | client | workaround",
  "text": "Restart the payments queue before touching the database.",
  "scope": "successor | team | never_transfer",
  "status": "active | corrected | forgotten",
  "version": 1,
  "supersedes": null,
  "derived_from": [],
  "source_clip_id": "c_1",
  "session_id": "s_1",
  "created_at": "2026-11-14T12:00:00Z",
  "expires_at": "2027-01-31T00:00:00Z"
}
```

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | /sessions | `{ "expert_id": "u_expert" }` | `{ "session_id", "first_question_text", "first_question_audio_url" }` |
| POST | /sessions/{session_id}/answer | multipart: `audio` file | `{ "transcript", "memories_created": [Memory], "gaps_created": [Gap], "next_question_text", "next_question_audio_url", "used_memory_ids": [] }` |
| GET | /memories?owner_id=u_expert | | `[Memory]` |
| PATCH | /memories/{id}/scope | `{ "scope": "team" }` | `Memory` |
| POST | /memories/{id}/correct | `{ "text": "..." }` | `{ "old": Memory, "new": Memory }` |
| POST | /memories/{id}/forget | | `{ "forgotten_ids": [], "runbook_steps_removed": [], "audit_id" }` |
| POST | /ask | `{ "question": "...", "memory": true }` | `{ "answer_text", "sources": [{ "memory": Memory, "clip_url", "transcript" }], "blocked_count": 0, "audit_id" }` |
| GET | /runbook | | `[{ "id", "text", "derived_from": [], "status" }]` |
| GET | /audit?limit=20 | | `[{ "actor_id", "action", "memory_ids", "allowed", "reason", "ts" }]` |
| GET | /gaps?owner_id=u_expert | | `[{ "id", "question", "kind": "missing | contradiction", "from_memory_ids": [], "status" }]` |
| WS | /live | | pushes `{ "type": "memory_changed", "memory": Memory }` and `{ "type": "runbook_changed" }` (from change streams) |
| GET | /clips/{clip_id} | | audio file |

Gap object: `{ "id", "question", "kind", "from_memory_ids", "status": "open | asked | answered" }`

## Status (each person updates their own line)
- Ayuub (backend):
- Harsh (frontend):
- Keith (demo):

## Requests (append, newest at bottom, format: [time] Name -> Name: request)

