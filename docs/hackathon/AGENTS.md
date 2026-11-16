<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

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
