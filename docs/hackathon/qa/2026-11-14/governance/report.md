# Governance and senior interview QA — 2026-11-14

Executed against real localhost frontend/backend with isolated Senior, Junior, and Intern Playwright contexts. Installed Chrome repeatedly stalled or failed to dispatch input state updates; bundled Chromium headless shell 1248 resolved this. Those Chrome harness failures are not confirmed product defects. No app source edited.

## Passed
- Real Senior Record composer submitted synthetic banker training knowledge; POST /sessions and /answer succeeded. Extracted one procedure and one QA disclaimer memory. Screenshot: 01-interview.png.
- For both synthetic records, scope changes via the UI enforced the expected API visibility: successor = senior/junior; team = all three; never_transfer = senior only. Restoring team restored visibility. Screenshot: 02-scope-team.png.
- Procedure extraction produced runbook step r_d2d2823a linked to m_1e9b5802.
- Empty correction disabled Save. Correcting via UI made v2 m_7ba36284, superseding v1; dependent runbook references moved to v2 and status became needs_review. Screenshot: 03-corrected.png.
- Intern attempting to change scope of the QA record received HTTP 403.
- Canceling Forget preserved the memory.
- Confirming Forget via UI tombstoned both versions and removed the dependent runbook step; audit a_a643935e returned.
- The second QA disclaimer record was forgotten through the authorized API as cleanup. No active QA records remain.
- Original gap records were identical before/after this run: g_1 asked and g_2 open.

## Coverage limitations and harness findings
- Interview setup intercepted only the outgoing real /sessions request to add memory:false. No responses were mocked. This deliberately avoided selecting/answering the existing demo contradiction. Normal memory-on contradiction resolution was not executed on original data.
- Scope visibility was confirmed with real authenticated API reads from each isolated role context after the UI writes; question-answer retrieval is covered by the recipient agent, not this script.
- Live correction without refresh is INCONCLUSIVE: the receiving page had not been explicitly awaited to its connected-and-loaded baseline before correction, and the immediate assertion saw no rows. This is not sufficient evidence of a product bug.
- The automated live-forget assertion incorrectly searched the shared QA marker and matched the separate surviving disclaimer record. Screenshot 04-junior-after-forget.png confirms the corrected procedure is absent while the disclaimer was still present before its subsequent cleanup. Therefore that raw false assertion is a harness defect, not a product failure; robust before/after live runbook proof remains unverified.
- An initial correction locator depended on the scope select, which disappears in edit mode; resumption used stable memory-ID text. An initial runbook assertion selected the disclaimer (system memory) rather than the procedure; resumed run correctly verified the procedure dependency.
- Additional direct session API probe command was rejected by automatic approval review with generic 'blocked by policy'; it was not retried. Allowed UI test path completed instead.

## Remaining artifacts/state
QA memory tombstones: m_1e9b5802, m_67e31663, m_7ba36284. Runbook r_d2d2823a is removed. Session s_7f0ff08d and normal audit/checkpoint history remain; no sessions/audit deletion endpoint was used. Original demo memories were not edited, forgotten, or reseeded. Raw final run assertions and sanitized network path/status log are in results.json; interpret the two live assertions using the limitations above. Scripts contain no credentials or tokens.

## Relevant source references
- frontend/components/Chat.tsx: startInterview and answer; frontend/lib/api.ts: startSession defaults to memory-on.
- backend/interview.py: ask selects original open gap; detect marks current_gap_id answered for any nonempty transcript. This is a code-inspection risk: unrelated typed knowledge can mark the selected contradiction answered, because the lead question is hidden by Chat.startInterview(lead). Not mutated/reproduced against original gap.
- frontend/components/MemoryList.tsx: edit/scope/forget controls.
- backend/governance.py: correct_memory, set_scope, forget_memory.

## Final focused live retry
A final focused live retry used bundled headless shell and added explicit receiving-page WS/record baseline waits, but it stopped before any mutation because the filled composer again remained disabled. live-results.json confirms created=[] and no session/answer calls. Thus the input symptom also occurred with headless shell under this concurrently changing dev environment; its cause is unresolved (do not describe Chrome selection as a definitive fix). No further retries or test data were created. Live no-refresh correction/runbook removal remains inconclusive; server-side correction and forget cascades passed. All created QA records from the completed mutation run remain forgotten, and no active QA records were left by this agent.
