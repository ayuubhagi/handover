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
- [ ] Switching the "Viewing as" dropdown between Senior / Junior / Intern causes **no 401 errors** (if it does: passcodes missing in `frontend/.env.local`, or AUTH_SECRET differs between machines)

## 3. Demo beats (the exact stage flow)

UI map (localhost:3000):
- **Top right dropdown:** who you are. **Senior** = Dana (retiring, owns every memory), **Junior** = Sam (taking over: successor + team memories), **Intern** = Jordan (same team: team memories only). Never-transfer memories stay with Dana. Until the frontend renames them, the dropdown shows Handing over / Taking over / Other team.
- **Bottom box "Tell it what you know":** the composer. The menu on its left switches **Record** (interview, saves memories) and **Ask** (questions to the handover).
- **Phone icon:** voice call mode (agent talks, you answer by mic). **Arrow:** send typed text.
- **Sidebar:** New chat, past conversations, **Handed over** (the memory list, scope, fix, forget), **Under the hood** (memories, gaps, runbook, audit, memory on vs off, live feed).

### Beat A: The agent hunts for a contradiction
- [ ] Top right: **Senior**. Sidebar: **New chat**. Composer menu: **Record**.
- [ ] Click the **phone icon** (or type "ready" and press the arrow).
- [ ] **Expected:** the first question is about the contradiction: restart the queue first vs clear the locks first. With the phone icon it is spoken out loud.

### Beat B: Answering resolves the gap
- [ ] Answer by voice on the call, or type: *Clear the locks first, never restart the database, then restart the queue.* and press the arrow.
- [ ] **Expected:** a **Saved:** chip shows a new memory with that rule.
- [ ] Sidebar > **Under the hood** > Gaps: the queue vs locks gap shows **answered**.

### Beat C: The junior inherits the right knowledge
- [ ] Top right: **Junior**. **New chat**. Composer menu: **Ask**.
- [ ] Type: *A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?* and press the arrow.
- [ ] **Expected:** answer says re-key it on the LoanDesk backup screen and delete the pre-filled zeros, cites Dana's memory, and **Hear Dana say it** plays her clip.

### Beat D: Client-confidential memory never transfers
- [ ] Still **Junior**, Ask mode. Type: *Is there anything special about Halvorsen Freight's Friday wires?*
- [ ] **Expected:** "The handover doesn't cover this for you", no sources, 1 related memory withheld.
- [ ] **Under the hood** > Audit: newest entry is an ask with **allowed false**.

### Beat E: The intern sees team knowledge only
- [ ] Top right: **Intern**. New chat, Ask mode. Same Halvorsen question.
- [ ] **Expected:** nothing shared ("The handover doesn't cover this for you").
- [ ] Ask the sanctions question from Beat C: **no sources** (that procedure is for the junior only), and a line saying related memories are not shared.
- [ ] Ask *Who do I call if LedgerOne is down?*: answers from Dana's **team** memory (duty manager, then the LedgerOne vendor hotline after 30 minutes).
- [ ] **Under the hood** > Runbook shows only the 3 team steps (LedgerOne report rerun, R7 routing flag, outage escalation), no Halvorsen step.

### Beat F: Forget cascades live
- [ ] Open a **second Chrome tab** at localhost:3000 as **Junior** > **Under the hood** > Runbook. Keep it visible.
- [ ] First tab: **Senior** > sidebar **Handed over**. Find the **PAY-08** memory and click **Forget**.
- [ ] **Expected:** the PAY-08 runbook step disappears in the second tab **without refreshing**. Audit shows a **forget** entry.

### Beat G: Memory on vs off (the proof)
- [ ] **Under the hood** > Memory on vs off. Ask the sanctions question from Beat C.
- [ ] **Expected:** ON says re-key on the backup screen and cites Dana; OFF gives a generic "get compliance sign-off, process through your exception queue with dual authorization", no sources.
- [ ] smith.langchain.com, newest trace: shows the memory ids used. Keep the tab open for Q&A.

### Beat H: Correct a memory
- [ ] **Senior** > **Handed over**. Click **Fix** on a memory, edit the text, save.
- [ ] **Expected:** a new version replaces it; the runbook step built from it shows **needs review**.

### Beat I: Scope change
- [ ] **Senior** > **Handed over**. Change a memory's "who can see this" from successor to never transfer.
- [ ] **Expected:** as **Junior** it no longer comes back; set it back and it returns.

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
- [ ] Tabs ready: app as Senior, app as Junior, Under the hood, LangSmith trace.
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
