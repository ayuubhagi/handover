# LOGS.md: shared work log

Every person and every AI assistant or subagent appends here: what got done, commits and PR links, issues, and conflicts.
Append only, newest at the bottom. Format: `[HH:MM] Name (agent/human): entry`. Use the tags **DONE / ISSUE / CONFLICT / PR / BLOCKED**.

## Open issues and conflicts (edit this list, keep it short)
- CONFLICT: TEAM.md says React (Vite) for /frontend, but a Next.js app is scaffolded at the root (src/). The frontend was built as Next.js in /frontend. Is the root src/ dead code? (Harsh)
- ISSUE: there's no `.env` locally, so the backend can't reach Atlas, Gemini, Voyage or ElevenLabs on Harsh's machine. Keys need to be shared privately, never committed. (Harsh)
- ISSUE: root tsconfig and eslint scan /frontend. See TEAM.md Requests. (Harsh)
- ISSUE (security scan, backend/routes.py, Ayuub): X-User-Id / ?user_id= is self-asserted, so anyone can impersonate u_expert; uploaded audio content_type isn't allowlisted, which is an XSS risk. Fix: allowlist audio MIME types + nosniff.
- ISSUE: backend needs MONGODB_URI to serve anything but /health; unhandled RuntimeError returns a 500 without CORS headers, which the browser reports as a network error. (Harsh)

## Log
[12:06] Harsh (subagent): DONE: Next.js frontend in /frontend. Typed client for every TEAM.md endpoint, mock mode (NEXT_PUBLIC_USE_MOCKS), WS /live reconnect, and the /expert, /successor, /compare and /audit screens. Build and lint clean. Commits 641b1cd, 9426a9b, 4466720, c5ee005.
[12:06] Harsh (subagent): ISSUE: verified in mock mode only. Forget, correct, recording and compare were never clicked through.
[backend] Ayuub: DONE (from git): routes, retrieval, governance, interview agent, voice, live hub, contract test. Commits 652bb35, a8df07e, 21f3607, 23ceecd, beb0938.
[2026-11-14 12:20] Harsh (subagent): DONE: diffed frontend client against backend routes/models. Paths, methods, X-User-Id, ?owner_id, ?limit, multipart `audio`, WS /live?user_id= message shapes, clip URLs (absolute PUBLIC_BASE_URL/clips/{id}, frontend appends ?user_id=) and CORS ("*", PATCH, X-User-Id allowed) all match. Fixed: AskSource.transcript nullable, runbook `needs_review` status shown, optional `transcript` form field supported (typed answer when no STT key). Commits 148cd3b, 6462103.
[2026-11-14 12:20] Harsh (subagent): DONE: mock click-through of correct, forget, compare, interview (typed). Fixed mock forget not deleting gaps of forgotten memories, gaps not refreshing after memory edits, unlabeled inputs. Commit a0f9059 (also commits frontend/AGENTS.md, auto-written by next dev). Clearer backend-down error, ee69318. Build, lint and tsc clean.
[2026-11-14 12:20] Harsh (subagent): ISSUE: backend in backend/.venv (gitignored) installs and starts; /health returns {"ok":true,"mongo":false}. Every other route 500s: "RuntimeError: MONGODB_URI is not set. Copy .env.example to .env and add the Atlas connection string." pytest: 15 failed (same cause). Live needs MONGODB_URI (+ python seed.py), VOYAGE_API_KEY, GOOGLE_API_KEY, ELEVENLABS_API_KEY; frontend NEXT_PUBLIC_API_URL, NEXT_PUBLIC_USE_MOCKS=false.
[2026-11-14 12:20] Harsh (subagent): ISSUE: real mic recording not verified (headless browser has no mic). UI click-through stopped on scope change: app/ and components/ are being redesigned by another agent.
