"""End to end run of TESTING.md sections 3 (beats A to I) and 4 through the real UI.

    pip install -r tests/e2e/requirements.txt      (uses your installed Chrome; no browser download)
    pytest tests/e2e -v -s

conftest.py starts its own backend (:8001, MONGODB_DB=handover_e2e, seeded fresh) and frontend (:3001).
Roles are switched with the "Viewing as" dropdown. The live mic is replaced by a fake getUserMedia stream
that plays demo/audio/dana_answer_g1.mp3, so the recorder, upload and ElevenLabs speech to text are real.
One screenshot per beat lands in backend/e2e-screens/ (gitignored), plus results.json.
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from playwright.sync_api import Page, expect, sync_playwright

from conftest import REPO, RESULTS, SCREENS

ANSWER_MP3 = REPO / "demo" / "audio" / "dana_answer_g1.mp3"
SANCTIONS_Q = "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?"
HALVORSEN_Q = "Is there anything special about Halvorsen Freight's Friday wires?"
WIFI_Q = "What's the wifi password?"
REFUSALS = ("don't have access", "do not have access", "contact it", "consult your")
DANA_ANSWER = ("Good catch. Clear the database locks first, but never restart the database. Clearing locks is safe. "
               "Restarting the database is what reloads the batch and causes the duplicates. "
               "So: clear the locks, then restart the queue.")

# Replace the microphone with Dana's recorded answer, played into a MediaStream.
FAKE_MIC = """
window.__e2e = { answerDone: false, answerSeconds: 0 };
navigator.mediaDevices.getUserMedia = async () => {
  const ac = new AudioContext();
  await ac.resume();
  const data = await (await fetch('/__e2e/answer.mp3')).arrayBuffer();
  const buf = await ac.decodeAudioData(data);
  const src = ac.createBufferSource();
  src.buffer = buf;
  const dest = ac.createMediaStreamDestination();
  src.connect(dest);
  window.__e2e.answerSeconds = buf.duration;
  src.onended = () => { window.__e2e.answerDone = true; };
  src.start();
  return dest.stream;
};
"""


# ---------------------------------------------------------------- fixtures and helpers

class App:
    def __init__(self, browser, servers):
        self.browser = browser
        self.servers = servers
        self.web = servers["web"]
        self.api = servers["api"]
        self.errors: list[str] = []
        self.ctx = self.new_context()
        self.page = self.ctx.new_page()
        self.watch(self.page, "main")

    def new_context(self):
        ctx = self.browser.new_context(viewport={"width": 1440, "height": 960})
        ctx.add_init_script(FAKE_MIC)
        ctx.route("**/__e2e/answer.mp3", lambda r: r.fulfill(path=str(ANSWER_MP3), content_type="audio/mpeg"))
        return ctx

    def watch(self, page: Page, name: str):
        page.on("pageerror", lambda e: self.errors.append(f"[{name}] pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and self.errors.append(f"[{name}] console: {m.text}"))

    def token(self, user: str) -> str:
        r = httpx.post(f"{self.api}/login", json={"user_id": user, "passcode": self.servers["passcodes"][user]})
        r.raise_for_status()
        return r.json()["token"]


@pytest.fixture(scope="module")
def app(servers):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel="chrome", headless=True,
            args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"],
        )
        a = App(browser, servers)
        a.page.goto(a.web)
        expect(a.page.get_by_role("button", name=re.compile("^Viewing as:"))).to_be_visible(timeout=60_000)
        yield a
        browser.close()
    (SCREENS / "results.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")


def shot(page: Page, beat: str, name: str) -> str:
    file = f"{beat}_{name}.png"
    page.screenshot(path=str(SCREENS / file), full_page=False)
    RESULTS.setdefault(beat, {"screens": []})["screens"].append(file)
    return file


def record(beat: str, ok: bool, note: str = ""):
    entry = RESULTS.setdefault(beat, {"screens": []})
    entry["result"] = "PASS" if ok else "FAIL"
    entry["note"] = note


def audit_row(row) -> dict:
    cells = [c.strip() for c in row.locator("td").all_inner_texts()]
    return dict(zip(["time", "who", "action", "memories", "result", "reason"], cells))


def role(page: Page, name: str):
    page.get_by_role("button", name=re.compile("^Viewing as:")).click()
    page.get_by_role("option", name=name, exact=True).click()
    expect(page.get_by_role("button", name=f"Viewing as: {name}")).to_be_visible()


def mode(page: Page, label: str):
    btn = page.get_by_role("button", name=re.compile("^Mode:"))
    if btn.get_attribute("aria-label") != f"Mode: {label}":
        btn.click()
        page.get_by_role("option", name=label, exact=True).click()
    expect(page.get_by_role("button", name=f"Mode: {label}")).to_be_visible()


def go(page: Page, where: str):
    if where == "chat":
        page.get_by_role("button", name="New chat").click()
        expect(page.get_by_role("heading", level=1)).to_be_visible()
    else:
        page.get_by_role("link", name=where).click()
        expect(page.get_by_role("heading", level=1, name=where)).to_be_visible()


def ask_in_chat(page: Page, question: str) -> dict:
    box = page.get_by_role("textbox", name="Ask anything")
    box.fill(question)
    with page.expect_response(lambda r: r.url.endswith("/ask") and r.request.method == "POST", timeout=120_000) as resp:
        box.press("Enter")
    assert resp.value.ok, resp.value.text()
    body = resp.value.json()
    expect(page.get_by_text(body["answer_text"][:40], exact=False).last).to_be_visible(timeout=20_000)
    return body


def no_alerts(page: Page):
    # The app's ErrorNote; Next.js also renders an empty role=alert route announcer, which is not an error.
    expect(page.locator("div[role=alert]")).to_have_count(0)


# ---------------------------------------------------------------- section 3: demo beats

def test_a_contradiction_question(app: App):
    p = app.page
    role(p, "Handing over")
    go(p, "chat")
    mode(p, "Record")
    sessions = []
    p.on("response", lambda r: r.url.endswith("/sessions") and r.request.method == "POST" and sessions.append(r))
    p.get_by_role("button", name="Call").click()
    p.wait_for_timeout(8000)
    starts = [r.json() for r in sessions]
    assert starts, "no POST /sessions after clicking Call"
    g1 = [s for s in starts if "queue" in s["first_question_text"].lower() and "lock" in s["first_question_text"].lower()]
    assert g1, [s["first_question_text"] for s in starts]                 # the backend asked g_1
    q = g1[0]["first_question_text"]
    assert g1[0]["first_question_audio_url"], "interviewer audio missing (ElevenLabs text to speech)"
    r = httpx.get(g1[0]["first_question_audio_url"], params={"token": app.token("u_expert")})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    on_call_screen = p.get_by_text(q[:50]).is_visible() or (p.wait_for_timeout(15000) or p.get_by_text(q[:50]).is_visible())
    shot(p, "A", "call_screen")
    if not on_call_screen:
        # Where did the question go? Each session the call screen created is a conversation in the sidebar.
        p.get_by_role("button", name="End call").click()
        p.locator("aside nav li button").filter(has_not_text="New recording").first.click()
        shown_in_chat = p.get_by_text(q[:50]).first.is_visible()
        shot(p, "A", "question_in_chat")
        pytest.fail(
            f"FRONTEND: Call screen stuck on 'Connecting'; one click made {len(starts)} POST /sessions (StrictMode "
            f"double effect in next dev). Backend asked g_1 with audio; question visible in the chat transcript: "
            f"{shown_in_chat}.")
    record("A", True, f"first question: {q[:110]}")


def test_b_answer_resolves_gap(app: App):
    p = app.page
    role(p, "Handing over")
    go(p, "chat")
    mode(p, "Record")
    box = p.get_by_role("textbox", name="Tell it what you know")
    box.fill(DANA_ANSWER)
    with p.expect_response(lambda r: "/answer" in r.url and r.request.method == "POST", timeout=180_000) as resp:
        box.press("Enter")
    assert resp.value.ok, resp.value.text()
    body = resp.value.json()
    text = " ".join(m["text"] for m in body["memories_created"]).lower()
    assert "lock" in text and "queue" in text and ("never" in text or "not" in text), body["memories_created"]
    expect(p.get_by_text(body["transcript"][:30]).first).to_be_visible(timeout=20_000)    # transcript bubble
    expect(p.get_by_text(body["memories_created"][0]["text"][:40]).first).to_be_visible()  # saved chip
    expect(p.get_by_text(body["next_question_text"][:40]).first).to_be_visible()
    shot(p, "B", "transcript_and_saved")
    go(p, "Under the hood")
    gap = p.locator("li", has_text="g_1 from")
    expect(gap.get_by_text("answered", exact=True)).to_be_visible(timeout=20_000)
    gap.scroll_into_view_if_needed()
    shot(p, "B", "gap_g1_answered")
    record("B", True, f"transcript: {body['transcript'][:80]}... | saved: {[m['text'] for m in body['memories_created']]}")


def test_c_successor_inherits(app: App):
    p = app.page
    role(p, "Taking over")
    go(p, "chat")
    mode(p, "Ask")
    body = ask_in_chat(p, SANCTIONS_Q)
    ids = [(s["memory"]["id"], s["memory"]["source_clip_id"]) for s in body["sources"]]
    assert any(mid in ("m_2", "m_9") for mid, _ in ids), ids
    assert all(m["memory"]["scope"] != "never_transfer" for m in body["sources"])
    low = body["answer_text"].lower()
    assert "zero" in low or "backup screen" in low, body["answer_text"]
    idx = next(i for i, (_, clip) in enumerate(ids) if clip == "c_2")
    with p.expect_response(lambda r: "/clips/c_2" in r.url, timeout=30_000) as clip:
        p.get_by_role("button", name="Original").nth(idx).click()
    assert clip.value.status in (200, 206) and clip.value.headers["content-type"].startswith("audio/")
    shot(p, "C", "sanctions_answer_with_clip")
    record("C", True, f"sources {ids}; clip c_2 played; answer: {body['answer_text'][:120]}")


def test_d_confidential_never_transfers(app: App):
    p = app.page
    body = ask_in_chat(p, HALVORSEN_Q)
    assert "m_4" not in [s["memory"]["id"] for s in body["sources"]]
    assert body["sources"] == [] and body["blocked_count"] >= 1, body
    assert "doesn't cover" in body["answer_text"] or "not shared" in body["answer_text"], body["answer_text"]
    expect(p.get_by_text("Some notes are private.").last).to_be_visible()
    shot(p, "D", "halvorsen_withheld")
    go(p, "Under the hood")
    rows = p.locator("table tbody tr")
    expect(rows.first).to_be_visible(timeout=20_000)
    p.wait_for_timeout(1500)  # let the audit list settle after the page's own loads
    entries = [audit_row(r) for r in rows.all()]
    p.get_by_role("heading", name="Audit").scroll_into_view_if_needed()
    shot(p, "D", "audit_ask_blocked")
    newest_ask = next(e for e in entries if e["action"] == "ask")
    assert newest_ask["who"] == "Taking over" and newest_ask["result"] == "blocked", newest_ask
    assert entries[0]["action"] == "ask" and entries[0]["result"] == "blocked", (
        f"newest audit row is {entries[0]['action']}/{entries[0]['result']} by {entries[0]['who']}, not the blocked ask")
    record("D", True, f"blocked_count {body['blocked_count']}; newest audit row: {entries[0]}")


def test_e_other_team_sees_nothing(app: App):
    p = app.page
    role(p, "Other team")
    go(p, "chat")
    mode(p, "Ask")
    body = ask_in_chat(p, HALVORSEN_Q)
    assert body["sources"] == [], body
    expect(p.get_by_role("button", name="Original")).to_have_count(0)
    go(p, "Handed over")
    expect(p.get_by_text("No steps visible to you.")).to_be_visible(timeout=20_000)
    expect(p.locator("main").get_by_text("Halvorsen")).to_have_count(0)
    shot(p, "E", "other_team_nothing")
    record("E", True, f"sources [], blocked_count {body['blocked_count']}, runbook empty")


def test_f_forget_cascades_live(app: App):
    p = app.page
    role(p, "Handing over")
    go(p, "Handed over")
    # Second tab, as the successor, watching the checklist before the forget.
    ctx2 = app.new_context()
    p2 = ctx2.new_page()
    app.watch(p2, "successor-tab")
    p2.goto(f"{app.web}/knows")
    role(p2, "Taking over")
    step = "never reuse R7"
    expect(p2.get_by_text(step, exact=False)).to_be_visible(timeout=30_000)
    expect(p.get_by_text(step, exact=False)).to_be_visible(timeout=30_000)
    item = p.locator("li", has_text="Never reuse routing flag R7")
    item.get_by_role("button", name="Forget").click()
    with p.expect_response(lambda r: "/memories/m_5/forget" in r.url, timeout=60_000) as resp:
        item.get_by_role("button", name="Forget").click()
    body = resp.value.json()
    assert "r_4" in body["runbook_steps_removed"], body
    # No reload: the change stream pushes runbook_changed over WS /live to both tabs.
    expect(p2.get_by_text(step, exact=False)).to_have_count(0, timeout=20_000)
    expect(p.get_by_text(step, exact=False)).to_have_count(0, timeout=20_000)
    shot(p2, "F", "successor_tab_r4_gone_live")
    shot(p, "F", "expert_after_forget")
    go(p, "Under the hood")
    forget_row = p.locator("table tbody tr", has_text="forget").first
    expect(forget_row).to_contain_text("m_5", timeout=20_000)
    ctx2.close()
    record("F", True, f"forget {body}; r_4 vanished live in the successor tab")


def test_g_memory_on_vs_off(app: App):
    p = app.page
    role(p, "Taking over")
    go(p, "Under the hood")
    p.get_by_role("textbox", name="Question").fill(SANCTIONS_Q)
    p.get_by_role("button", name="Compare").click()
    on_panel = p.locator("section", has=p.get_by_role("heading", name="Memory on", exact=True))
    off_panel = p.locator("section", has=p.get_by_role("heading", name="Memory off", exact=True))
    expect(on_panel.get_by_text("In their own words")).to_be_visible(timeout=120_000)
    expect(on_panel.get_by_role("button", name="Play c_2").first).to_be_visible()
    expect(off_panel.locator("p.font-serif")).to_be_visible(timeout=120_000)
    expect(off_panel.get_by_text("In their own words")).to_have_count(0)
    off_text = off_panel.locator("p.font-serif").inner_text()
    assert not any(w in off_text.lower() for w in REFUSALS), off_text
    assert "zero" not in off_text.lower(), off_text
    p.get_by_role("heading", name="Memory on vs off").scroll_into_view_if_needed()
    shot(p, "G", "memory_on_vs_off")
    note = f"memory off: {off_text[:120]}"
    trace = langsmith_ask_trace()
    if trace:
        note += f" | LangSmith trace {trace}"
    record("G", True, note)


def langsmith_ask_trace() -> str | None:
    """Newest 'ask' run in LangSmith that names memory ids (traces flush asynchronously)."""
    try:
        from langsmith import Client
        client = Client()
        for _ in range(10):
            for run in client.list_runs(filter='eq(name, "ask")', limit=5, is_root=True):
                ids = (run.outputs or {}).get("used_memory_ids")
                if ids:
                    return f"{run.id} used_memory_ids={ids}"
            time.sleep(3)
    except Exception as exc:
        return f"not checked ({exc.__class__.__name__})"
    return None


def test_h_correct_memory(app: App):
    p = app.page
    role(p, "Handing over")
    go(p, "Handed over")
    item = p.locator("li", has_text="LedgerOne reconciliation report is wrong")
    item.get_by_role("button", name="Fix").click()
    new_text = ("The LedgerOne reconciliation report is wrong on the first business day of each month because of a "
                "timezone bug. Rerun it after 11 a.m. Eastern.")
    item.get_by_role("textbox", name="Fix this").fill(new_text)
    with p.expect_response(lambda r: "/correct" in r.url, timeout=60_000) as resp:
        item.get_by_role("button", name="Save").click()
    body = resp.value.json()
    assert body["old"]["status"] == "corrected" and body["new"]["version"] == 2 and body["new"]["supersedes"] == body["old"]["id"]
    expect(p.get_by_text("Rerun it after 11 a.m. Eastern.")).to_be_visible(timeout=20_000)
    step = p.locator("li", has_text="rerun the LedgerOne reconciliation report")
    expect(step.get_by_text("Needs a check")).to_be_visible(timeout=20_000)
    shot(p, "H", "corrected_needs_check")
    go(p, "Under the hood")
    tech = p.locator("li", has_text=f"from {body['new']['id']}")
    expect(tech.get_by_text("needs review")).to_be_visible(timeout=20_000)
    record("H", True, f"{body['old']['id']} v1 -> {body['new']['id']} v2; runbook step needs review")


def test_i_scope_change(app: App):
    p = app.page
    m1 = "Restarting the database first reloads the batch"
    role(p, "Handing over")
    go(p, "Handed over")
    item = p.locator("li", has_text=m1)
    with p.expect_response(lambda r: "/memories/m_1/scope" in r.url, timeout=30_000) as resp:
        item.get_by_role("radio", name="Only me").click()
    assert resp.value.json()["scope"] == "never_transfer"
    role(p, "Taking over")
    expect(p.get_by_text("Handed over", exact=True).first).to_be_visible()
    expect(p.locator("li", has_text=m1)).to_have_count(0, timeout=20_000)
    shot(p, "I", "successor_cannot_see_m1")
    role(p, "Handing over")
    with p.expect_response(lambda r: "/memories/m_1/scope" in r.url, timeout=30_000) as resp:
        p.locator("li", has_text=m1).get_by_role("radio", name="Sam").click()
    assert resp.value.json()["scope"] == "successor"
    role(p, "Taking over")
    expect(p.locator("li", has_text=m1)).to_have_count(1, timeout=20_000)
    shot(p, "I", "successor_sees_m1_again")
    record("I", True, "m_1 hidden from Taking over at never_transfer, back at successor")


# ---------------------------------------------------------------- section 4: stress and failure

def test_4a_nothing_relevant(app: App):
    p = app.page
    role(p, "Taking over")
    go(p, "chat")
    mode(p, "Ask")
    body = ask_in_chat(p, WIFI_Q)
    assert body["sources"] == [], body
    assert "doesn't cover" in body["answer_text"], body["answer_text"]
    expect(p.get_by_role("button", name="Original")).to_have_count(0)
    shot(p, "4A", "wifi_not_covered")
    record("4A", True, body["answer_text"])


def test_4b_refresh_mid_flow(app: App):
    p = app.page
    before = len(app.errors)
    p.reload()
    expect(p.get_by_role("button", name=re.compile("^Viewing as:"))).to_be_visible(timeout=30_000)
    p.wait_for_timeout(2000)
    no_alerts(p)
    new = [e for e in app.errors[before:] if "pageerror" in e]
    assert not new, new
    shot(p, "4B", "after_refresh")
    record("4B", True, "reloaded without errors")


def test_4c_backend_down_and_back(app: App):
    p = app.page
    backend = app.servers["backend"]
    go(p, "chat")
    mode(p, "Ask")
    backend.stop()
    t0 = time.time()
    try:
        box = p.get_by_role("textbox", name="Ask anything")
        box.fill(SANCTIONS_Q)
        box.press("Enter")
        alert = p.locator("div[role=alert]")
        expect(alert).to_be_visible(timeout=30_000)
        expect(alert).to_contain_text("reach the backend")
        shot(p, "4C", "backend_down_message")
    finally:
        time.sleep(max(0.0, 5 - (time.time() - t0)))
        backend.start()
    go(p, "chat")
    mode(p, "Ask")
    body = ask_in_chat(p, SANCTIONS_Q)
    assert body["sources"], body
    no_alerts(p)
    shot(p, "4C", "backend_recovered")
    record("4C", True, "clear 'can't reach the backend' message, then recovered after restart")


def test_4d_offline_and_back(app: App):
    p = app.page
    go(p, "chat")
    mode(p, "Ask")
    app.ctx.set_offline(True)
    time.sleep(10)
    app.ctx.set_offline(False)
    body = ask_in_chat(p, HALVORSEN_Q)
    assert body["answer_text"]
    no_alerts(p)
    shot(p, "4D", "after_offline")
    record("4D", True, "browser offline 10 s (simulated with Playwright, wifi untouched), next request worked")


def test_4e_same_question_three_times(app: App):
    p = app.page
    go(p, "chat")
    mode(p, "Ask")
    for _ in range(3):
        ask_in_chat(p, SANCTIONS_Q)
    no_alerts(p)
    token = app.token("u_successor")
    with ThreadPoolExecutor(3) as pool:
        codes = list(pool.map(lambda _: httpx.post(f"{app.api}/ask", json={"question": SANCTIONS_Q, "memory": True},
                                                   headers={"Authorization": f"Bearer {token}"}, timeout=120).status_code,
                              range(3)))
    assert codes == [200, 200, 200], codes
    shot(p, "4E", "three_quick_asks")
    record("4E", True, "3 asks in the UI back to back + 3 concurrent API asks, all 200, no rate-limit errors")


def test_zz_no_page_errors(app: App):
    """Report (not fail) browser console errors collected during the run."""
    RESULTS["console_errors"] = {"errors": app.errors[:50]}
