# Handover banker-flow QA — November 14, 2026

## Readiness

Local app is running at http://localhost:3000, with a healthy backend/MongoDB at http://localhost:8000/health. This is a functional audit of the working checkout, not a release certification. Three parallel agents used independent Playwright browser instances for recipient access, governance, and mobile/voice/resilience. Browser contexts separated the Senior, Junior, and Intern audiences. No application fixes, commits, deployment, reseeding, or changes to existing demo memories were performed by this QA team.

**Not ready to certify audience isolation or muted calls.** Two privacy issues were reproduced: cached chat content crosses the selected audience boundary, and call mute can leave the microphone enabled. The tested call End button did release the microphone.

## Confirmed outstanding errors

### P1 — Switching to Intern exposes a Junior's cached restricted answer

1. As Sam/Junior, ask how to re-key a sanctions-held payment after compliance approval.
2. Receive the successor-only LoanDesk answer and original transcript from memory m_2.
3. Switch the role menu to Jordan/Intern.
4. The same restricted answer and transcript remain visible. Reload and reopen the conversation from history: they remain visible as Jordan.

Fresh requests as Jordan correctly withhold this knowledge. The failure is local cached-conversation isolation, not an authenticated backend retrieval bypass. Clear the active conversation on identity change, partition/filter stored history by viewer, and enforce ownership when reopening conversations. Also account for revoked/forgotten sources in persisted answers.

Evidence: [cross-role.json](recipients/cross-role.json), [screenshot](recipients/cross-role-final.png), [reproduction](recipients/cross-role.cjs). Source: `frontend/components/RoleMenu.tsx:26`, `frontend/components/Chat.tsx:32`, `frontend/components/store.ts:49`, `frontend/components/Sidebar.tsx:90`.

### 1. P1 — Call says Muted while the microphone is enabled

1. Select Ask and start a Call.
2. Press Mute during the greeting.
3. Press Interrupt.

The screen says Muted, but a newly created audio track is enabled and live. Speech recognition also produced a caption while muted. This was reproduced with a synthetic Chrome microphone; no human recording was needed. End call stopped the track.

Fix direction: persist desired mute state across new recorder streams, apply it before recording, and stop/suppress the separate speech-recognition consumer while muted. See `frontend/components/CallScreen.tsx:85`, `:110`, `:193` and `frontend/components/useRecorder.ts:38`, `:114`.

Evidence: [voice-results.json](resilience/voice-results.json), [muted-active-mic.png](resilience/muted-active-mic.png), [reproduction script](resilience/voice.cjs).

### 2. P2 — Hidden mobile navigation takes keyboard focus

At 390px width, leave the sidebar closed, focus Open menu and press Tab. Focus moves to the offscreen Handover link (x=-240, right=-130). The sidebar is only translated out of view, so its controls remain focusable. Make the closed mobile sidebar inert/hidden to keyboard navigation while preserving desktop navigation.

Evidence: [supplement-results.json](resilience/supplement-results.json), [screenshot](resilience/hidden-sidebar-keyboard.png). Source: `frontend/components/Sidebar.tsx:58`.

### 3. P2 — Escape does not dismiss the mobile menu

Open the sidebar at phone width and press Escape: the sidebar and backdrop remain open. The Close menu button works. Add Escape dismissal and return focus to the menu opener.

Evidence: [screenshot](resilience/sidebar-after-escape.png), [results](resilience/results.json). Source: `frontend/components/Sidebar.tsx:54`.

### P2 — Unrelated memory cited for an unanswered question

As Intern, asking “What's the wifi password?” returned “The handover memory does not cover it [1]” but attached a synthetic QA training disclaimer as a source. That memory contains no Wi-Fi information. The synthetic record was temporarily shared with the team during the parallel governance test and has since been forgotten. This is an observed relevance false positive under added knowledge, not a missing seed password. Fix retrieval/answer source validation so an abstaining answer does not cite unrelated material.

Evidence: the last `JordanAsk` entry in [followup.json](recipients/followup.json), memory m_67e31663. Source investigation: `backend/retrieval.py` relevance selection and answer/source construction. LLM/retrieval behavior may vary on repeated runs.

## Verified checks

| Area | Observed result |
|---|---|
| Local startup | Frontend responds; backend reports `ok: true, mongo: true` |
| TypeScript | `npx tsc --noEmit --incremental false` passed |
| ESLint | `npm run lint` passed |
| Backend contracts | Latest safe subset: **9 passed, 12 deselected** |
| Junior banker questions | Sanctions procedure returns LoanDesk/zero-removal guidance and source; confidential Halvorsen knowledge withheld; outage escalation correct; unknown Wi-Fi question has no sources |
| Intern banker questions | Actual browser questions: team outage guidance succeeds; confidential and successor-only knowledge withheld. Unknown Wi-Fi case exposed the unrelated-source issue above |
| Memory on/off | Real API comparison: ON returns LoanDesk/zeros and m_2/m_9; OFF returns generic guidance with no sources. Comparison-panel UI not certified |
| Senior capture/governance | Typed interview creates synthetic memories and a dependent runbook step; all scope visibility combinations pass; correction creates v2 and flags the step for review; forget cancellation and version/runbook cascade pass |
| Current role data | Dana/senior, Sam/junior, Jordan/intern; Intern sees only team memories and three team runbook steps |
| Backend authorization | Missing/forged credentials rejected; confidential clips blocked; team clip allowed for Intern; only owners can govern; invalid inputs rejected |
| Resilience | Browser-scoped backend outage and offline failure show errors; requests recover after reconnect |
| Submission/history | Three rapid Enter presses produce one request; refresh and reopening history preserve messages |
| Responsive routes | Home, Desk ledger, Under the hood exercised at 390x844 and 1440x1000; no observed document horizontal overflow |
| Calls | Ask and Record start/end; real Record opening asks queue-versus-locks contradiction; denied mic handled; End releases tested track |

Backend evidence: [current contract results](backend/contracts-current.xml), [current readiness snapshot](backend/readiness.json), [read-only probe](backend/probe.py).

Real retrieval comparison evidence: [questions.json](backend/questions.json). Governance mutations used only marked QA records; both versions and the extra disclaimer were forgotten afterward. Session, audit, and tombstone history remain by design. Original gaps stayed unchanged by the governance test. The normal Record call checked its first contradiction question without answering it.

The backend subset includes identity/token enforcement, passcode enforcement, JSON/CORS errors, scoped memory lists, runbook visibility, gaps visibility, owner-only governance, clip access, and websocket authentication. The twelve excluded tests are not implied to pass: some mutate seed data, others overlap browser coverage.

## Environment changes during testing

The starting database had older identities: Dana/expert, Sam/successor, and Riley/outsider in retail-marketing. This caused five initial contract failures and exposed all actors' audit rows to the old outsider role. During testing, the backend/database changed outside this QA team's actions. Fresh logins confirmed the current identities and scoped audit behavior, and all nine selected contracts passed on rerun. These initial problems are **resolved in the final observed state**, not outstanding findings. Historical evidence is retained in `backend/contracts.xml` and `backend/readiness-initial.json`.

Application source files also changed outside this team's work during the run. Browser hydration/stalls required retries and an alternate Chromium binary. Those initial automation failures are not classified as product defects. Results apply to the observed local session, not a frozen Git revision.

## Coverage limits

Human speech recognition quality, audible speaker/source-clip quality, long multi-turn calls, real handset hardware, expiry/TTL timing, and live LangSmith trace inspection were not certified. Clip HTTP availability is not a human playback test. Network faults were scoped to the test browser; shared servers and machine networking were not stopped. No lintapple pass is claimed: no UI changes were made, and the audit used browser functional/responsive checks. Production build/deployment was not tested.

Live correction/forget without refreshing the receiving view remains inconclusive: the initial checks had baseline/selector defects, not reliable evidence of a product failure. Normal memory-on contradiction resolution was deliberately not performed on original demo data. Source inspection also found that any nonempty answer marks the selected gap answered (`backend/interview.py:170`), while a typed opening can hide that question (`Chat.startInterview(lead)`); unrelated typed knowledge may therefore resolve a gap incorrectly. This is an unverified code-path concern to test on disposable gap data, separate from the reproduced findings above.

Detailed agent reports and scripts:

- [Recipient flows](recipients/report.md)
- [Governance flows](governance/report.md)
- [Mobile, voice, and resilience](resilience/report.md)

Playwright was installed outside the app under `%TEMP%/ask-grandpa-qa-tools`; reproduction scripts use that location and require the local servers. Read script notes before rerunning mutation tests. QA artifacts are under this directory; application files were left for you to fix.
