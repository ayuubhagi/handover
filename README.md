# Handover

**A governed memory engine for knowledge that would otherwise walk out the door.** Built at Agents in Context Toronto, a MongoDB hackathon (Nov 14, 2026), for Problem Statement 2: Memory You Can Govern.

Handover is a voice agent that runs exit interviews with a senior employee across their last few weeks and remembers what they know. The expert controls that memory: who inherits each piece, how long it lives, and whether it gets corrected or forgotten. Their successor asks questions and hears the expert's real recorded answers.

The demo is a retiring bank operations lead. The product is the engine underneath, for any knowledge that leaves with someone: a departing advisor, an on-call engineer, a plant operator.

## How it works

1. **Interview:** the expert talks. ElevenLabs transcribes, and the model extracts procedures, systems, clients, and workarounds. Each memory is saved to MongoDB Atlas with an owner, a scope (`successor`, `team`, or `never_transfer`), an expiry, and its source clip. Schema validation rejects any memory missing those fields.
2. **The agent hunts for gaps:** before each session it loads open gaps and contradictions ("Monday you said restart the queue first, today you said the database") and asks about them out loud with an ElevenLabs voice.
3. **Scoped inheritance:** when the successor asks a question, Vector Search pre-filters by scope, so only memories they are allowed to inherit come back, and the expert's real clip plays. Client-confidential memories never surface.
4. **Governance:** the expert can hide, correct, or forget a memory. Corrections are versioned. A forget cascades through everything built from that memory (summaries, runbook steps) in one transaction, with an audit entry, and change streams update the successor's view live. TTL expires memories about retired systems.
5. **Proof:** the same session with memory on vs off asks different questions and gives the successor different answers. LangSmith traces show which memories caused each decision.

**Voice rule:** only the interviewer's voice is synthesized. The expert's voice is always a real recording, never cloned.

## How we answer the track questions

| Question | Answer |
|---|---|
| How do you keep one person's memory from leaking into another's? | Scope is enforced inside the `$vectorSearch` pre-filter, not in the prompt. Every read is written to `audit_log`. |
| How does the agent fix or drop a memory that is wrong or expired? | `correct` writes a new version that supersedes the old one. `forget` walks `derived_from` with `$graphLookup` and removes the memory, its embedding, and derived runbook steps in a transaction. A TTL index expires memories automatically. |
| How do you prove a memory changed behavior? | Memory on vs off, side by side, plus LangSmith traces naming the memory ids behind each decision. |

## MongoDB features used

Atlas (hackathon sandbox) · Vector Search with pre-filters · Atlas Search + `$rankFusion` hybrid retrieval · `$jsonSchema` validation · TTL indexes · change streams · `$graphLookup` · multi-document transactions · LangGraph `MongoDBSaver` checkpointer for interview state · Voyage AI embeddings

## Stack

FastAPI (Python), React (Vite), LangGraph, LangSmith, ElevenLabs, Gemini, Voyage AI, MongoDB Atlas.

## Run it locally

Terminal 1 (backend):
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py   (first time only, and only into your own MONGODB_DB)
uvicorn main:app --port 8000
```

Terminal 2 (frontend):
```
cd frontend
npm install
npm run dev
```
Then open http://localhost:3000 in Chrome.

Required:
- `.env` at the repo root, copied from the team chat. It holds MONGODB_URI, GOOGLE_API_KEY, VOYAGE_API_KEY, ELEVENLABS_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING, AUTH_SECRET and DEMO_PASSCODES. Never commit it.
- Your own database in that `.env`: `MONGODB_DB=handover_harsh`, `MONGODB_DB=handover_keith`, and so on. Never run `seed.py` against the default `handover` database, which is demo-only.
- `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_USE_MOCKS=false` (copy `frontend/.env.example`).
- Python 3.11 to 3.13 and Node 20+. On macOS/Linux or Git Bash, activate with `source .venv/bin/activate` or `source .venv/Scripts/activate`.
- Check the backend: `http://localhost:8000/health` → `{"ok": true, "mongo": true}`. Every other route needs a token from `POST /login` (`{"user_id", "passcode"}` from DEMO_PASSCODES), sent as `Authorization: Bearer <token>`.

## Git workflow (we are 3+ people pushing at once)

- **Pull before you start and after every commit:** `git pull --rebase origin main`, then push.
- Fix any conflicts right away, then make sure the app still runs before moving on.
- Keep commits small and push often so nobody drifts far from `main`.

## Team

Ayuub Hagi, Harsh (GreenKeewi), Keith V Singh (KVS-ALT)

All code in this repository was written during the hackathon. All demo data is fictional.
