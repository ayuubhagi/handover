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
Auth: `POST /login` with `{ "user_id", "passcode" }` returns a signed token (HMAC, 12 h). Every other request sends `Authorization: Bearer <token>`; `/clips/{id}` and `WS /live` also accept `?token=<token>` (for `<audio src>` and WebSocket). `X-User-Id` and `?user_id=` are no longer read. Missing or bad token: 401. Errors are always JSON `{ "detail" }` with CORS headers (401 auth, 403 not allowed, 404, 413 audio too large, 415 not an audio type, 422 bad body, 502 upstream, 503 database or embeddings unavailable).

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
| POST | /login | `{ "user_id": "u_expert", "passcode": "..." }` | `{ "token", "expires_at", "user": { "id", "name", "role" } }` |
| GET | /me | | `{ "id", "name", "role" }` |
| POST | /sessions | `{ "expert_id": "u_expert", "memory": true }` (`memory` optional, default true; false = interviewer ignores past sessions) | `{ "session_id", "first_question_text", "first_question_audio_url" }` |
| POST | /sessions/{session_id}/answer | multipart: `audio` file (audio/* only: webm, ogg, mpeg, wav, mp4/m4a, aac, flac; max 25 MB) and/or optional `transcript` text field (used instead of speech to text) | `{ "transcript", "memories_created": [Memory], "gaps_created": [Gap], "next_question_text", "next_question_audio_url", "used_memory_ids": [] }` |
| GET | /memories?owner_id=u_expert | | `[Memory]` (owner: all statuses; anyone else: only active memories they may read, possibly `[]`, never 403) |
| PATCH | /memories/{id}/scope | `{ "scope": "team" }` | `Memory` |
| POST | /memories/{id}/correct | `{ "text": "..." }` | `{ "old": Memory, "new": Memory }` |
| POST | /memories/{id}/forget | | `{ "forgotten_ids": [], "runbook_steps_removed": [], "audit_id" }` |
| POST | /ask | `{ "question": "...", "memory": true }` | `{ "answer_text", "sources": [{ "memory": Memory, "clip_url", "transcript" (may be null) }], "blocked_count": 0, "audit_id" }` |
| GET | /runbook | | `[{ "id", "text", "derived_from": [], "status": "active | needs_review" }]` (needs_review after a source is corrected) |
| GET | /audit?limit=20 | | `[{ "actor_id", "action", "memory_ids", "allowed", "reason", "ts" }]` |
| GET | /gaps?owner_id=u_expert | | `[{ "id", "question", "kind": "missing | contradiction", "from_memory_ids": [], "status" }]` |
| WS | /live | | pushes `{ "type": "memory_changed", "memory": Memory }` and `{ "type": "runbook_changed" }` (from change streams) |
| GET | /clips/{clip_id}?token= | | audio file (`X-Content-Type-Options: nosniff`) |

Gap object: `{ "id", "question", "kind", "from_memory_ids", "status": "open | asked | answered" }`

## Status (each person updates their own line)
- Ayuub (backend): every contract route live against Atlas, 20/20 contract tests pass (real Gemini, Voyage, ElevenLabs, LangSmith, recorded clips). Signed-token auth on every route, audio upload allowlist, JSON errors with CORS. Seeded with Keith's demo content. Run: cd backend, pip install -r requirements.txt, python seed.py, uvicorn main:app --port 8000.
- Harsh (frontend): Next.js app in /frontend builds clean. Typed client for every contract endpoint + WS /live, mock mode (NEXT_PUBLIC_USE_MOCKS=true, shows a "Mock data" badge). Screens: expert (interview, scope/correct/forget, gaps), successor (ask + live runbook), memory on vs off, audit. Next: wire to real backend.
- Keith (demo): demo content done and merged (demo/DEMO.md, demo/RESEARCH.md, demo/seed_content.py). Dana and Sam audio generated with ElevenLabs. Waiting on Ayuub to swap the seed (see task below), then rehearsal and video.

## Setup for teammates (every agent: do this before running the backend)
1. Confirm with your human that the `.env` from the team chat is at the repo root (`ask-grandpa/.env`). Never commit it; it is gitignored.
2. Add your own database to that `.env`: Harsh `MONGODB_DB=handover_harsh`, Keith `MONGODB_DB=handover_keith`.
3. From `backend/`, run `python seed.py` once. It fills only your private database (about a minute while the search indexes build).
4. Never seed the default `handover` database. It is the demo database, and seeding drops and recreates it.
5. Auth: `POST /login` with `{ "user_id", "passcode" }` for one of the `DEMO_PASSCODES` users in `.env` (u_expert, u_successor, u_outsider). Send `Authorization: Bearer <token>` on every request, and `?token=<token>` for `/clips/{id}` and `WS /live`. `X-User-Id` is ignored.
Then run `uvicorn main:app --port 8000` from `backend/` (with the venv from `pip install -r requirements.txt`).

## Requests (append, newest at bottom, format: [time] Name -> Name: request)

[12:06] Harsh -> Ayuub: frontend runs on http://localhost:3000; please keep CORS_ORIGINS allowing it (default "*" is fine) including PATCH and the X-User-Id header.
[12:06] Harsh -> Ayuub: frontend accepts clip_url / *_audio_url as absolute or relative, and appends ?user_id=<viewer> for <audio> (per ARCHITECTURE.md). WS /live is opened with ?user_id= too. Please confirm /live and /clips read that param.
[12:06] Harsh -> Ayuub: when a viewer can't read Dana's memories, should GET /memories?owner_id=u_expert return a filtered list (frontend assumes this) or 403?
[12:06] Harsh -> anyone owning root config: root tsconfig/eslint include frontend/**; please add "frontend" to root tsconfig "exclude" and "frontend/**" to root eslint globalIgnores (root `npm run lint` currently scans frontend/.next if it was built locally).
[12:20] Harsh -> Ayuub: backend extensions the frontend now relies on, please add to the contract table: optional `transcript` form field on POST /sessions/{id}/answer, AskSource.transcript may be null, runbook status `needs_review`, optional `memory` on POST /sessions.
[12:20] Harsh -> Ayuub: without MONGODB_URI routes raise an uncaught RuntimeError (500, no CORS headers). Could it map to a HandoverError 503 so the UI can show it?
[12:55] Keith -> Ayuub: proposed new seed content in demo/seed_content.py (same CLIPS/MEMORIES/RUNBOOK/GAPS shapes as seed.py; each memory is based on a real incident, see demo/RESEARCH.md). If you agree, swap those lists into backend/seed.py. Audio for c_1..c_7 will be generated into backend/seed_audio/ by demo/generate_audio.py, and I'll ping you to re-seed.
[12:55] Keith -> team: need the ElevenLabs API key shared privately (not committed) to generate the Dana and Sam voices.
[13:20] Keith -> Ayuub: audio is in backend/seed_audio/c_1..c_7.mp3 (PR keith/demo-recent). It's voiced from demo/seed_content.py, NOT the current seed.py text, so please swap CLIPS/MEMORIES/RUNBOOK/GAPS from demo/seed_content.py into seed.py, then re-seed. c_2 changed: it's now the sanctions-hold backup-screen story (based on Citi's 2024 $81T near miss).

[13:35] Keith -> Ayuub: TASK FOR YOUR AGENT, swap in the demo seed content. Steps:
  1. In backend/seed.py, replace the CLIPS, MEMORIES, RUNBOOK and GAPS lists with the ones in demo/seed_content.py. Copy them verbatim (same shapes as yours). Leave PEOPLE and everything else in seed.py as is.
  2. Keep the clip ids c_1 to c_7. The matching audio is already committed at backend/seed_audio/c_1.mp3 to c_7.mp3, and seed.py already loads files from there.
  3. Keep m_5's expiry at 21 days (it's the memory that expires when PAY-08 is switched off) and m_4's scope as never_transfer.
  4. Run python seed.py against Atlas. Expected: 7 clips (all with audio), 9 memories, 6 runbook steps, 2 gaps.
  5. Check the demo beats work against the real backend:
     a. As u_expert, POST /sessions: the first question should be gap g_1 (queue first vs clear the locks first).
     b. Answer it by uploading demo/audio/dana_answer_g1.mp3 to POST /sessions/{id}/answer. It should resolve g_1 and create a memory that says clear the locks, never restart the database, then restart the queue.
     c. As u_successor, POST /ask with "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?" With memory true, sources should include m_9 or m_2 with clip c_2. With memory false, the answer should be generic.
     d. As u_successor, ask "Is there anything special about Halvorsen Freight's Friday wires?": no m_4 in sources, blocked_count >= 1, and an audit entry with allowed false.
     e. As u_outsider, the same Halvorsen question returns nothing, and /runbook shows no r_6.
     f. As u_expert, POST /memories/m_5/forget: runbook step r_4 should disappear, with a runbook_changed push on /live.
  6. Don't edit /demo. Reply here with what passed or failed, and I'll fix the content side.

[14:17] Ayuub -> Keith: seed swap done and all 6 beats PASS against the real backend (logged in with tokens, real Gemini, Voyage, ElevenLabs). backend/seed.py CLIPS/MEMORIES/RUNBOOK/GAPS are identical to demo/seed_content.py (m_5 expires in 21 days, m_4 never_transfer); seed gives 7 clips (all with audio), 9 memories, 6 runbook steps, 2 gaps.
  a. PASS: first question is g_1 (queue first vs clear the locks first), with interviewer audio.
  b. PASS: uploading demo/audio/dana_answer_g1.mp3 transcribes via ElevenLabs, marks g_1 answered, creates "clear the locks, never restart the database, then restart the queue". It no longer re-raises g_1 as a new contradiction.
  c. PASS: memory on returns m_2, m_3, m_9 with clip c_2 (audio plays); memory off returns a generic answer with no sources.
  d. PASS: no m_4 in sources, blocked_count 1, audit entry allowed=false ("1 withheld by scope"). Fixed: before, that ask was logged allowed=true because other sources came back.
  e. PASS: outsider gets no sources (blocked_count 5) and an empty runbook, so no r_6.
  f. PASS: forget m_5 removes r_4 and pushes memory_changed:m_5 + runbook_changed on /live.
  Content note: for d, Gemini answers "The handover memory does not cover it." That's correct, but a line like "there is something about Halvorsen, but it isn't shared with you" would land better on stage. Tell me if you want that wording.
  Your 13:58 issues: the 500 without CORS is fixed (every error is JSON with CORS now). The Voyage 401 was your copy of the key: the backend works with the current key, so re-copy .env from the team chat. Testing forget/correct is safe once you're on your own MONGODB_DB (see Setup below).

[14:10] Ayuub -> Harsh: BREAKING, auth is live. Keep the role dropdown, no login page. On every switch, silently POST /login `{ "user_id": "u_expert" | "u_successor" | "u_outsider", "passcode" }` with that user's demo passcode (I'll send the passcodes with the .env, keep them out of git), store the returned token, and send `Authorization: Bearer <token>` on every request. For `<audio src>` and WS /live append `?token=<token>` instead of `?user_id=`. On a 401, log in again and retry once. WS /live with a bad token gets `{ "type": "error" }` then close code 4401.
[14:10] Ayuub -> Harsh: answers to your questions. (1) /clips and /live read `?token=` now (not `?user_id=`). (2) GET /memories for a non-owner returns a filtered list (only active memories they may read, `[]` for Riley), never 403. (3) Your extensions are in the contract table above: optional `transcript` and `memory`, nullable source transcript, `needs_review`. (4) Missing MONGODB_URI is now a JSON 503 with CORS headers, and every other crash is JSON with CORS too. (5) The root Next.js scaffold (src/, public/, package.json, tsconfig.json, eslint.config.mjs, next.config.ts) is deleted, so root lint no longer scans /frontend.
[14:10] Ayuub -> team: use your own MONGODB_DB (e.g. MONGODB_DB=handover_harsh in your .env, then python seed.py) while testing. Everyone on `handover` at once means one person's seed wipes another's sessions. Keep `handover` for the demo.
[14:20] Ayuub -> Harsh: pull, set NEXT_PUBLIC_USE_MOCKS=false, put the .env from the team chat at the repo root (add MONGODB_DB=handover_harsh, then python seed.py once from backend/), run the backend on your laptop, switch the client to POST /login + Bearer token (14:10 request), and click through the whole flow for real: interview with mic, ask as Sam and Riley, correct, forget, memory on vs off. Log what breaks in LOGS.md.
