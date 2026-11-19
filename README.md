# Handover

**Governed memory for AI agents, so a senior employee's knowledge outlives their last day.**

[![CI](https://github.com/ayuubhagi/handover/actions/workflows/ci.yml/badge.svg)](https://github.com/ayuubhagi/handover/actions/workflows/ci.yml)

Built in six hours at **Agents in Context Toronto**, a MongoDB hackathon organized by Cerebral Valley (November 14, 2026), for the **Memory You Can Govern** problem statement.

[![Handover demo video: when senior employees leave, their knowledge shouldn't](docs/media/handover.png)](docs/media/handover_demo.mp4)

**[Watch the 70-second demo](docs/media/handover_demo.mp4)** (click the image or this link).

---

## The problem

When senior employees leave, the process knowledge they built up over years usually leaves with them, because most of it was never written down: which deadline thousands of paycheques depend on, which screen quietly adds extra zeros to a payment, which client only approves transfers by phone.

An AI agent can capture that knowledge. But then the agent knows things not everyone should hear, and someone has to decide who gets to see what. Most enterprise AI tools control access to documents that already exist. The memories an agent creates from a conversation have no file and no permissions of their own.

**Handover governs what the agent learns.**

## How it works

1. **Exit interview.** A voice agent interviews the person who is leaving. Whisper transcribes, an LLM extracts procedures, systems, clients and workarounds, and the agent follows up when two answers contradict each other.
2. **Every memory is born with governance metadata.** Each one is stored in MongoDB Atlas with an owner, an access scope, an expiry and a link to the recording it came from. `$jsonSchema` validation rejects any memory missing them.
3. **Access is enforced in the database, not the prompt.** When someone asks a question, their role becomes a pre-filter inside the `$vectorSearch` query. Memories they can't read are never retrieved, so they never reach the model and no prompt can pull them out.
4. **The same rule holds everywhere the knowledge shows up**, from checklists built on top of memories to live updates and expiry (details below).
5. **Every answer is traceable.** LangSmith records who asked, which scopes they were allowed, and which memory ids the agent used.

### Who sees what

The demo is a bank's payments team. All names and data are fictional.

| Person | Can read | Example: "I'm taking over the Halvorsen Freight account. What should I know?" |
|---|---|---|
| **Intern** | `team` memories | Nothing. Two memories exist but are withheld, and the withheld read is logged. |
| **Junior, taking over** | `successor` + `team` | The fraud warning: Halvorsen only approves transfers by phone, so an email asking to change their bank details is a scam. |
| **Senior, leaving** | everything, including `never_transfer` | The fraud warning, plus the confidential fact that Halvorsen is quietly moving to another bank. |

The model suggests a scope when it extracts a memory (client confidential → `never_transfer`, procedures → `successor`, general facts → `team`). The senior can re-scope, correct or forget any memory, and every change is audited.

## Engineering details

- **Derived knowledge inherits the strictest source.** A checklist step built from several memories only appears if the viewer can read all of them, so anything built from restricted knowledge stays restricted.
- **Forget means forget.** `$graphLookup` walks the memory's lineage, and the memory plus everything derived from it is removed in one multi-document transaction, with an audit entry.
- **Corrections are versioned.** A correction creates a new version that supersedes the old one, and steps derived from it are flagged for review.
- **Memories expire.** A TTL index removes memories about retired systems automatically, and expiry cascades like a forget.
- **Live views.** Change streams push every scope change, correction and forget to other users' screens over a WebSocket, redacted per viewer.
- **Hybrid retrieval.** `$rankFusion` combines `$vectorSearch` (Voyage AI embeddings) and Atlas Search, with the same scope filter on both.
- **Resumable interviews.** The interview agent is a LangGraph graph whose state is checkpointed in Atlas with `MongoDBSaver`, so an interview survives a crash.
- **Voice rule.** Only the interviewer's voice is synthesized. Answers link back to the expert's original recording.
- **No stale reads.** Atlas Search indexes update asynchronously, so for a moment after a forget the index can still call a memory active. Every pipeline re-checks the same access filter against the stored document after the search stage, so a forgotten or re-scoped memory is never served from a stale index.
- **Provider-agnostic LLM layer.** OpenAI gpt-oss-120b on Groq by default, falling back automatically to Gemini when a model hits its quota, overloads or returns output that fails the schema. Structured output uses strict JSON schemas.

Full design, collections, indexes and pipelines: [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md).

## Tested, not just demoed

Every push runs [CI](.github/workflows/ci.yml) against `mongodb/mongodb-atlas-local`, a real MongoDB with Atlas Search and Vector Search, so the access pre-filters are tested in the same `$rankFusion` pipelines production runs.

- **Red-team leak eval: 0 leaks in 100 attacks.** [50 adversarial prompts](backend/tests/integration/attacks.py) (role impersonation, "ignore previous instructions", scope probing, indirect questions, exfiltration through translation or base64, mixed topics) are each sent as the intern and as the junior. A leak is a restricted memory showing up as a source, in the answer, or **anywhere in the prompt sent to the model**. The LLM is replaced by a spy that records every prompt, so the test proves restricted text never leaves the database. The eval also checks that each role still gets what it *is* allowed to see, so it cannot pass by returning nothing.
- **61 tests:** 33 unit tests (access rules, signed tokens, the LLM provider chain, rate limits) and 28 integration tests (per-role visibility on every route, forget cascades, versioned corrections, re-scoping, expiry, the demo reset, rate limiting).
- **About 21 ms median** for `/ask` retrieval with the access filter (CI runner, local MongoDB, LLM excluded).
- The integration tests caught the stale-index window described above. It is now covered by a regression test.

## Stack

MongoDB Atlas (Vector Search, Atlas Search, `$rankFusion`, `$jsonSchema`, TTL indexes, change streams, `$graphLookup`, transactions) · LangGraph with the MongoDB checkpointer · LangSmith · Voyage AI · OpenAI gpt-oss-120b and Whisper on Groq, Gemini fallback · ElevenLabs · FastAPI (Python) · Next.js · GitHub Actions

## Run it locally

You need Python 3.11 to 3.13 and Node 20+. For MongoDB, either use an Atlas cluster (the free M0 tier works) or run one locally with Atlas Search included: `docker compose up -d mongodb`. Keys: Groq (free) or Gemini for the LLM, Voyage AI for embeddings, and optionally ElevenLabs (interviewer voice) and LangSmith (traces).

1. Copy `.env.example` to `.env` at the repo root and fill it in. Use a database name of your own in `MONGODB_DB`; `seed.py` drops and recreates the collections in it.
2. Start the backend:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python seed.py                   # loads the fictional demo data
   uvicorn main:app --port 8000
   ```
   Check it at `http://localhost:8000/health`, which should return `{"ok": true, "mongo": true}`.
3. Start the frontend in another terminal:
   ```bash
   cd frontend
   cp .env.example .env.local       # set NEXT_PUBLIC_USE_MOCKS=false and the same DEMO_PASSCODES
   npm install
   npm run dev
   ```
   Open `http://localhost:3000` and switch between the senior, junior and intern with the role menu in the top right.

### Run the tests

```bash
cd backend
pytest tests/unit                          # no database or keys needed
docker compose up -d mongodb               # from the repo root, first time only
pytest tests/integration -s                # integration tests + leak eval, no keys needed
```

## Deploy

The backend ships as a Docker image with a [Render blueprint](render.yaml) (`DEMO_MODE=true`): visitors pick a role without a passcode, tokens are short-lived, expensive routes are rate limited per IP, a daily LLM budget falls back to extractive answers instead of exhausting the free tier, and anyone can restore the fictional data from Under the hood. Point the Vercel frontend at it with `NEXT_PUBLIC_USE_MOCKS=false`, `NEXT_PUBLIC_DEMO_MODE=true` and `NEXT_PUBLIC_API_URL`.

## What's next

- Replace the demo logins with SSO, mapping identity-provider groups to scopes.
- Keep new memories private until the senior approves them. Today they become visible as soon as they're extracted, and the senior reviews afterward.
- Inference attacks. The leak eval proves restricted memories never reach the model; inferring a secret by combining facts a viewer *is* allowed to see is a harder, open problem.
- Retrieval quality evals per role, alongside the leak eval.

## Team

Ayuub Hagi · Harsh Seetha · Keith Singh

The core was built during the hackathon; tests, CI, the leak eval, the provider-agnostic LLM layer and the public-demo hardening were added afterwards. All demo data is fictional. Hackathon planning notes, the API contract and QA reports are in [docs/hackathon](docs/hackathon).
