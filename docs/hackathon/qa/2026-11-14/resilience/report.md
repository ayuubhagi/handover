# Mobile, voice and resilience audit — 2026-11-14

Tested real localhost:3000 frontend and localhost:8000 backend in separate Chrome Playwright processes. Phone viewport 390×844; desktop 1440×1000. No application edits, reseeding, existing-memory mutations or shared-service restarts. One Record call creates a session and asks the initial question; no recorded answer was submitted. Ask tests create ordinary audit events.

## Confirmed findings

### P1 — Muted call opens an enabled microphone and still transcribes

Reproduce: Fresh page → Mode Ask → Call → Mute while greeting is speaking → Interrupt. The screen says **Muted**, but the newly opened audio track has `enabled: true`, `readyState: live`. The speech-recognition caption also displayed “yeah” while muted. This was tested using Chrome's fake media device, not a person's microphone. The synthetic-device track state is direct browser evidence, not a mocked application response.

Evidence: `voice-results.json`, `muted-active-mic.png`, reproducible `voice.cjs`.
Source: `frontend/components/CallScreen.tsx:85` starts recognition and a new recorder in `listen()`; `:110` never reapplies muted state. `:193` only toggles the recorder that already exists. `frontend/components/useRecorder.ts:41` acquires a fresh enabled stream; `:114` changes only the current track. Recognition is a separate microphone consumer and is never stopped by mute.
Suggested fix: persist desired mute state into every newly acquired stream; pause/abort speech recognition while muted and suppress turn submission until unmuted. Test mute-before-listen and mute across subsequent turns. End call DID stop the tested media track.

### P2 — Closed mobile sidebar remains keyboard-focusable

Reproduce: At 390px width with sidebar closed, focus Open menu and press Tab. Focus moves to hidden Handover home link at x=-240, right=-130, entirely outside viewport. Keyboard users lose visible focus and tab through unavailable navigation.

Evidence: `supplement-results.json`, `hidden-sidebar-keyboard.png`. Source: `frontend/components/Sidebar.tsx:58` hides only with CSS transform; no inert/hidden handling for closed mobile navigation.
The initial suite's keyboard result was sampled during the closing animation and incorrectly marked PASS; the stable fresh-page supplement supersedes it.

### P2 — Escape does not close mobile sidebar

Reproduce: Open menu on mobile, wait for animation, press Escape. Sidebar/backdrop stay open. Close menu button does work.
Evidence: `sidebar-after-escape.png`, `results.json`. Source: `frontend/components/Sidebar.tsx:54` onward has click handlers only; no Escape/focus-management behavior.

## Passed real flows

- Phone navigation to Desk ledger and Under the hood, then New chat; both routes render without document horizontal overflow.
- Light-theme toggle and desktop route rendering at 1440×1000.
- Role menu arrow-key/Enter selection from Dana to Sam; junior Record restriction and Ask instead transition.
- Browser-scoped `/ask` connection refusal shows clear backend error; question remains in conversation.
- Removing network fault recovers: real LedgerOne answer says duty manager first, vendor hotline after 30 minutes and renders sources.
- Three rapid Enter presses yield exactly one `/ask` request.
- Reload then reopen from sidebar preserves conversation history.
- Browser-context offline failure is visible; reconnect and another question works. Unknown wifi question returns “The handover doesn't cover this.”
- Ask call with denied microphone displays actionable microphone unavailable text; End call returns to composer.
- Record call starts real session and asks queue-vs-locks contradiction; Interrupt opens mic, denied permission displays error, End call returns to composer.
- Fake-microphone Ask call End stops the acquired track (`readyState: ended`).
- No pageerror events captured by completed main suite.

## Limits and artifacts

Human speech transcription quality, actual speaker sound, source clip playback quality, long multi-turn voice sessions, silence detection accuracy, and permission-dialog dismissal while a request is pending are not certified. No handset hardware test. Lintapple was read but not installed/run: this was a read-only audit, no UI built/changed. Screenshots and functional checks are not a lintapple pass.

Initial attempts failed because hydration needed extra time and exact accessible-name selectors did not match names including decorative icon content. Those harness failures were corrected before the completed suite; they are not product errors. Parent observed unrelated concurrent source/backend changes; results apply to this observed session, not an immutable release.

Scripts: `suite.cjs`, `voice.cjs`, `supplement.cjs`. Raw observations: `results.json`, `voice-results.json`, `supplement-results.json`. The scripts use temporary installed Playwright and Chrome; no application dependency added. `probe.cjs` and `debug.cjs` are read-only diagnostic helpers.
