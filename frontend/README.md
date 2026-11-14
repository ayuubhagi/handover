# Handover frontend

Next.js (App Router) + Tailwind v4. Talks to the FastAPI backend through the API contract in `../TEAM.md`.

## Run

```bash
cd frontend
cp .env.example .env.local   # edit as needed, never commit it
npm install
npm run dev                  # http://localhost:3000
```

- `NEXT_PUBLIC_API_URL` backend base URL (default `http://localhost:8000`).
- `NEXT_PUBLIC_USE_MOCKS=true` uses fictional in-browser data (`lib/mock.ts`) and shows a "Mock data" badge in the header. Set it to `false` to use the real backend. Never present mock mode as the live system.

Restart `npm run dev` after changing env vars.

## Layout

- `lib/types.ts` contract types (Memory, Gap, ...)
- `lib/api.ts` real client for every contract endpoint, plus WS `/live` with auto-reconnect
- `lib/mock.ts` same interface, fictional data, scope filtering, forget cascade, versioned correct, audit, gaps
- `app/expert` interview + memory governance + gaps
- `app/successor` ask + live runbook
- `app/compare` memory on vs off
- `app/audit` audit log

The viewer (Dana · Senior, Sam · Junior, Jordan · Intern) is picked in the header; switching silently calls `POST /login` and every request sends `Authorization: Bearer <token>`. Audio and the WebSocket send `?token=` because browsers can't set headers there.

## Checks

```bash
npm run lint
npm run build
```
