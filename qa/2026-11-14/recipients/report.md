# Recipient flows QA — 2026-11-14

Scope: isolated Playwright browser against real localhost:3000 frontend and localhost:8000 backend. No mocked answers, no database seeding, no application source changes. Synthetic demo-bank questions only.

## Completed initial run

| Flow | Result | Evidence |
|---|---|---|
| Junior sanctions exception question | PASS: LoanDesk backup screen and remove pre-filled zeros; m_2 successor source | evidence.json, Sam-sanctions.png |
| Junior confidential Halvorsen Friday wires | PASS: explicitly withheld, no sources, blocked_count 1 | evidence.json, Sam-confidential.png |
| Junior LedgerOne outage | PASS: duty manager first, vendor hotline after 30 minutes | evidence.json, Sam-outage.png |
| Junior irrelevant Wi-Fi password | PASS: handover does not cover this, no sources | evidence.json |
| New chat between questions | PASS: separate conversation created for each question | test.cjs |
| Reload | Page reloads and composer usable. Active conversation resets by design (store.ts:42), so the prior answer is not immediately visible. Reopening history is tested separately. | evidence.json |
| Original recording | Clip c_2 HTTP 200. Audible playback NOT established: immediate Stop-button count was zero; human listening was not performed. | evidence.json |

Initial desktop screenshot capture later stalled; owned browser test tree stopped and reduced follow-up run used. Browser startup/hydration also required retries; this is a coverage limitation, not asserted as an application defect without reproduction.

## Source inspection requiring browser follow-up

Same-browser role switching does not clear active chat or filter stored conversations: RoleMenu.tsx:26 only changes user; Chat.tsx:32 selects conversation by ID without owner validation; Chat.tsx:190 renders stored messages; store.ts:49 stores all roles together. A successor answer may remain readable after switching to intern. Current browser proof tracked in followup.json if completed.

## Environment changed during run

Parent independently found old database identities (outsider in another team), then externally migrated identities appeared during QA. Initial identity/audit mismatch must not be described as a current defect; follow-up browser run uses fresh sessions after migration.

## Current-data browser follow-up

The final keyboard-driven isolated Chromium run reached Jordan after database identities were migrated. `followup.json` records:

- PASS: LedgerOne outage answer gives duty manager then hotline after 30 minutes; all returned sources have team scope.
- PASS: Halvorsen question withholds one related memory, returns no sources.
- PASS: sanctions question withholds two related memories, returns no sources.
- FAIL: unrelated Wi-Fi question returns "The handover memory does not cover it [1]" but attaches an unrelated synthetic QA training source (`m_67e31663`). This violates TESTING.md's "no random sources" expectation. That temporary governance QA record existed during the query and was subsequently cleaned up by the governance agent. The observation establishes a retrieval/citation false positive under added team knowledge, not a leaked restricted memory.
- BLOCKED in this browser run: Under-the-hood and comparison navigation, because the test used an exact accessible link name that omitted decorative icon text. Parent separately verifies the comparison through the actual API; do not report browser coverage for it.

Fresh cross-role browser script runs separately and writes cross-role.json; final status below.

## Confirmed P1: cached successor knowledge remains visible to intern

Actual browser reproduction completed with current identities and real API responses (`cross-role.json`, `cross-role-final.png`):

1. Fresh browser, switch Dana → Sam with Viewing as.
2. Ask: "How do I re-key a sanctions-held payment after compliance approval?"
3. Receive successor-only source m_2 with LoanDesk backup-screen instructions and original transcript.
4. Switch Sam → Jordan. Role label changes to Jordan, but full successor answer and transcript stay visible.
5. Reload. Reopen "Re-keying a compliance payment" from sidebar. As Jordan, the same successor-only answer/transcript is still readable.

This is a same-browser role-switch/cache isolation failure; a fresh intern API query correctly withholds the source. The demo intentionally allows choosing roles, but its displayed current-role boundary is not respected for historical content. For a real shared workstation/account transition, cached information survives the authorization change.

Relevant locations: frontend/components/RoleMenu.tsx:26, frontend/components/Chat.tsx:32 and :190, frontend/components/store.ts:49 and :77. Fix by scoping histories to current identity, clearing active conversation when identity changes, and ensuring cached answers are not rendered under a different identity. Consider revalidation when scopes change or memories are forgotten.

## Final coverage limits

No human listening or real microphone evaluation in this track. Source clip HTTP 200 is transport evidence only. Under-hood comparison browser step was blocked by test selector; parent API supplement covers semantic on/off behavior. Cross-role screenshot and stored answer evidence are complete. Application source remained unchanged.
