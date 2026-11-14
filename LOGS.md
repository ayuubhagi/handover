# LOGS.md: shared work log

Every person and every AI assistant or subagent appends here: what got done, commits and PR links, issues, and conflicts.
Append only, newest at the bottom. Format: `[HH:MM] Name (agent/human): entry`. Use the tags **DONE / ISSUE / CONFLICT / PR / BLOCKED**.

## Open issues and conflicts (edit this list, keep it short)
- CONFLICT: TEAM.md says React (Vite) for /frontend, but a Next.js app is scaffolded at the root (src/). The frontend was built as Next.js in /frontend. Is the root src/ dead code? (Harsh)
- ISSUE: there's no `.env` locally, so the backend can't reach Atlas, Gemini, Voyage or ElevenLabs on Harsh's machine. Keys need to be shared privately, never committed. (Harsh)
- ISSUE: root tsconfig and eslint scan /frontend. See TEAM.md Requests. (Harsh)

## Log
[12:06] Harsh (subagent): DONE: Next.js frontend in /frontend. Typed client for every TEAM.md endpoint, mock mode (NEXT_PUBLIC_USE_MOCKS), WS /live reconnect, and the /expert, /successor, /compare and /audit screens. Build and lint clean. Commits 641b1cd, 9426a9b, 4466720, c5ee005.
[12:06] Harsh (subagent): ISSUE: verified in mock mode only. Forget, correct, recording and compare were never clicked through.
[backend] Ayuub: DONE (from git): routes, retrieval, governance, interview agent, voice, live hub, contract test. Commits 652bb35, a8df07e, 21f3607, 23ceecd, beb0938.
