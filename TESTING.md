# TESTING.md: full end-to-end retest of Handover

Use this before every rehearsal and once more right before judging. Run it top to bottom. Tick each box. If a step fails, write the step number and what you saw in LOGS.md with the tag ISSUE.

---

## 0. Setup (once per laptop)

- [ ] `.env` at repo root (from team chat, never committed). Teammates add `MONGODB_DB=handover_<name>`. The demo laptop uses the default database.
- [ ] `frontend/.env.local`:
  ```
  NEXT_PUBLIC_USE_MOCKS=false
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_DEMO_PASSCODES=<from team chat>
  ```
- [ ] Terminal 1 (backend):
  ```
  cd backend
  .venv\Scripts\python -m uvicorn main:app --port 8000
  ```
  If you see `WinError 10048`, a backend is already running on 8000. That's fine; use it.
- [ ] Terminal 2 (frontend): `cd frontend` then `npm run dev`
- [ ] Browser: **Chrome** (mic + dictation), open http://localhost:3000
- [ ] Mic permission allowed for localhost (lock icon in the address bar)

## 1. Reset to a clean demo state

Do this before each full run, **only when nobody else is using that database**.

- [ ] Stop the backend (Ctrl+C in Terminal 1)
- [ ] `cd backend` then `.venv\Scripts\python seed.py`
- [ ] Expected output: **7 clips (all with audio), 9 memories, 6 runbook steps, 2 gaps**
- [ ] Start the backend again (Terminal 1 command above)
- [ ] Hard refresh the browser (Ctrl+Shift+R) and start a **new conversation** in the sidebar (old conversations point at old sessions)

## 2. Health checks (30 seconds)

- [ ] http://localhost:8000/health returns `{"ok": true, "mongo": true}`
- [ ] The UI shows **no "Mock data" badge**
- [ ] Switching the "Viewing as" dropdown between Handing over / Taking over / Other team causes **no 401 errors** (if it does: passcodes missing in `frontend/.env.local`, or AUTH_SECRET differs between machines)

## 3. Demo beats (the exact stage flow)

### Beat A: The agent hunts for a contradiction
- [ ] Viewing as **Handing over** (Dana). Interview mode. Start a new interview.
- [ ] **Expected:** the first question is about the contradiction: restart the queue first vs clear the locks first (gap g_1).
- [ ] The question plays out loud in the interviewer voice (ElevenLabs). If silent: check the ElevenLabs key has text-to-speech permission.

### Beat B: Answering resolves the gap
- [ ] Answer by **mic** (or upload `demo/audio/dana_answer_g1.mp3`): "Clear the locks first, never restart the database, then restart the queue."
- [ ] **Expected:** transcript appears, a "Saved:" chip shows a new memory saying clear the locks, never restart the database, then restart the queue.
- [ ] Under the hood > Gaps: **g_1 shows answered**.
- [ ] If the composer stays disabled after a failed answer, refresh and start a new conversation (known issue, Harsh is fixing).

### Beat C: The successor inherits the right knowledge
- [ ] Switch to **Taking over** (Sam). Ask mode.
- [ ] Ask: *"A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?"*
- [ ] **Expected:** an answer warning not to push it through, with sources that include **m_9 or m_2**, and **"Hear Dana say it"** plays clip **c_2** (the sanctions-hold backup-screen story).

### Beat D: Client-confidential memory never transfers
- [ ] Still **Taking over**. Ask: *"Is there anything special about Halvorsen Freight's Friday wires?"*
- [ ] **Expected:** no m_4 in sources, a gentle "not shared with you" / "the handover doesn't cover it" line, **blocked_count ≥ 1**.
- [ ] Under the hood > Audit: newest entry is an **ask with allowed = false**.

### Beat E: Another team sees nothing
- [ ] Switch to **Other team** (Riley). Ask the same Halvorsen question.
- [ ] **Expected:** nothing returned.
- [ ] Runbook view: **no r_6**.

### Beat F: Forget cascades live
- [ ] Switch to **Handing over**. Open "What … knows" (the memory list).
- [ ] Forget **m_5** (the PAY-08 memory that is about to expire).
- [ ] **Expected:** runbook step **r_4 disappears without a refresh** (live update from the change stream). Audit shows a **forget** entry.
- [ ] Open a second browser tab as **Taking over** before you click Forget: r_4 should vanish there too, live. This is the strongest visual.

### Beat G: Memory on vs off (the proof)
- [ ] Under the hood > **Memory on vs off**. Ask the sanctions question from Beat C.
- [ ] **Expected:** memory ON cites Dana's memory and clip; memory OFF gives a generic best-guess answer with **no sources**. The difference must be obvious on screen.
- [ ] Open https://smith.langchain.com, newest trace: it should show the memory ids used. Keep this tab open for Q&A.

### Beat H: Correct a memory
- [ ] As **Handing over**, correct any memory (edit its text).
- [ ] **Expected:** a new version replaces the old one; the runbook step built from it shows **needs review**.

### Beat I: Scope change
- [ ] As **Handing over**, change a memory's scope from successor to never_transfer.
- [ ] **Expected:** switch to Taking over and that memory no longer comes back; switch it back and it returns.

## 4. Stress and failure checks

- [ ] Ask a question with nothing relevant (*"What's the wifi password?"*): answer says the handover doesn't cover it, no random sources.
- [ ] Refresh the page mid-flow: the app reloads without errors.
- [ ] Stop the backend for 5 seconds: the UI shows a clear "backend is down" message, not a blank screen. Start it again and it recovers.
- [ ] Turn off wifi for 10 seconds, turn it back on: the next request works (Atlas reconnects).
- [ ] Ask the same question 3 times quickly: no rate-limit errors (Voyage Tier 1, query cache).

## 5. Before judging (5:00 PM)

- [ ] Reset to clean demo state (section 1), then **do not seed again**.
- [ ] Laptop plugged in, notifications off (Focus mode), volume up, other apps closed.
- [ ] Browser zoom so the back row can read it (Ctrl + plus).
- [ ] Tabs ready: app as Handing over, app as Taking over, Under the hood, LangSmith trace.
- [ ] Backup screen recording of a full successful run saved on the desktop.
- [ ] One person drives, one person talks. Rehearse the 3 minutes at least 3 times.

## Known gotchas

| Symptom | Fix |
|---|---|
| 401 on everything | `NEXT_PUBLIC_DEMO_PASSCODES` missing or wrong, or AUTH_SECRET differs from the backend's .env |
| `WinError 10048` | Backend already running on 8000; use it or close the other one |
| Audio 404 | Run seed.py so clips load from backend/seed_audio/ |
| Interviewer silent | ElevenLabs key missing text-to-speech permission |
| Gaps vanished after a reseed | Another backend on the same database was running during the reseed; everyone uses their own MONGODB_DB |
| Gemini 429 | Free-tier limit; add billing in Google AI Studio with a budget alert |
| Voyage 401 | Wrong key in .env; copy it again from the team chat |
