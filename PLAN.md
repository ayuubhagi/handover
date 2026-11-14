# Ask Grandpa: Governed Memory Engine

Track 2: Memory You Can Govern. Ask Grandpa is the demo. The real product is a governed memory engine: the person a memory is about controls who sees it, how long it lives, and how it gets corrected or forgotten. Swap grandpa for a client, a patient, or a customer and the engine is the same.

## Pitch
Agents remember everything, but nobody governs it. Every memory here has an owner, a scope, and a lifespan, and we prove it changes what the agent does next.

## Judge questions
1. No leaking: Vector Search filters by the asker's identity inside the query.
2. Fix or forget: correct keeps history; forget cascades to embeddings, summaries, and gaps. TTL for expiry.
3. Proof: same session with memory on vs off asks different questions. LangSmith traces show which memory drove each decision.

## Stack
Atlas Sandbox, Vector Search, schema validation, TTL index, change streams, LangGraph + LangSmith, ElevenLabs (speech-to-text and voice), Gemini.

## Collections
- people: id, name, role, relationship
- memories: id, owner_id, type, text, embedding, audience, source_clip_id, session_id, created_at, expires_at, status, derived_from
- clips: id, owner_id, audio_url, transcript, session_id
- gaps: id, owner_id, question, from_memory_ids, status
- audit_log: id, actor_id, action, memory_id, allowed, reason, timestamp

## Team
- Ayuub: backend, Atlas, Vector Search, agent loop, governance
- Teammate 2: frontend, elder view and family view
- Teammate 3: demo data, sample sessions, pitch, 1 minute video, README

## Must haves (by 1:00 end to end)
1. Session 2 asks a follow-up from session 1
2. Family ask plays the real clip
3. Hide and forget work live

## Rules
Public repo. All code written during the event. Never commit .env.

## Full split (3 people)

### Person 1: Ayuub (backend + memory engine)
- 10:30-11:30: FastAPI app, Atlas connection, collections with schema validation, Vector Search index (filters: owner_id, audience, status), TTL index on expires_at
- 11:30-12:30: Endpoints: POST /session/{id}/answer (audio in, transcribe with ElevenLabs, extract stories with Gemini, embed, save), GET /family/ask?asker=&q= (permission-filtered vector search, returns clips)
- 12:30-1:30: Agent loop in LangGraph: load open gaps, pick next question, detect contradictions, create gaps; LangSmith tracing on
- 1:30-3:00: Governance: PATCH /memory/{id}/audience, POST /memory/{id}/correct, POST /memory/{id}/forget (cascade), audit_log, change stream to push updates
- 3:00-4:00: Memory on vs off comparison endpoint, bug fixes, help connect frontend

### Person 2: Frontend
- 10:30-12:00: React (Vite) app with mock API. Elder view: record button, agent reply text + audio. Family view: choose asker (grandkid or cousin), question box, results with audio + transcript
- 12:00-1:30: Story list for elder: Family/Private toggle, Correct, Forget buttons. Audit log panel
- 1:30-3:00: Swap mocks for real endpoints, live updates when a story is hidden or forgotten
- 3:00-4:00: Memory on vs off side-by-side screen, polish, make demo flow smooth

### Person 3: Demo + data
- 10:30-11:30: Write and record 3 fake grandpa sessions (~1 min each). Session 1: brother moved away in 1979, no reason given. Session 2: a year that contradicts session 1. Session 3: one private story cousins shouldn't hear. Type exact transcripts
- 11:30-1:00: Draft 3-minute pitch: hook, memory demo, governance demo, "grandpa is the demo, the product is a governed memory engine"
- 1:00-3:00: README (what it is, architecture, how to run, sponsor tools used), test the app as a user and report bugs
- 3:00-4:30: Record 1-minute submission video, run the pitch 3+ times with the team, prep 5 likely judge Q&A answers

### Checkpoints
- 12:30: backend endpoints return real data
- 1:30: one full flow works end to end
- 3:00: governance working live
- 4:00: code freeze, then demo practice and submission
