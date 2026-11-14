# Handover demo

**Pitch in one line:** Handover decides who inherits which knowledge. In a bank, the wrong person knowing the
wrong thing is a compliance problem.

Two versions of the same story: a **3-minute live demo** for round one, and a **1-minute video** for the
submission. Same beats and same data, so we only rehearse one thing.

## Cast

| Person | Level | What they get |
|---|---|---|
| **Dana** | Senior, retiring | Everything she said in her exit interviews. She controls who inherits each memory. |
| **Sam** | Junior, taking over Dana's role | 🟠 Successor and 🟢 Team memories |
| **Jordan** | Intern, new on the team | 🟢 Team memories only |

## Use case: payments operations at Northgate Bank (fictional)

Access in a bank isn't "everyone sees everything". It runs on need-to-know and segregation of duties, which
regulators require. Documents and systems already have access controls. What has none today is what's in the
expert's head. Once that goes into an AI, anyone who can talk to the AI knows what the expert knew, unless the AI
knows who it's talking to.

| Level | What it protects | Dana's memories at this level |
|---|---|---|
| 🔒 **Senior only** (never_transfer) | Client-confidential arrangements. Privacy and bank confidentiality rules say nobody else gets them, not even the successor. | Halvorsen Freight's Friday wire arrangement (m_4) |
| 🟠 **Successor** (Sam and Dana) | Authority and override knowledge: the power to move money around controls. Only the person accountable for the role gets it. An intern knowing how to get around a control is a fraud risk. | Re-keying a payment held by sanctions screening, the backup-screen zeros (m_2, m_3, m_9). Stalled batch: clear locks, restart the queue (m_1, m_7). |
| 🟢 **Team** (everyone, Jordan included) | General know-how. Safe, and it helps the intern learn. | Who to call when LedgerOne is down (m_8). The LedgerOne report is wrong on the 1st, so rerun it (m_6). PAY-08 is being retired, so never reuse flag R7 (m_5). |

**If a judge asks about engineering:** everyone has the codebase, but not production credentials, customer data
or security incident details. It's the same engine.

**Voices:** Dana is fictional, so her clips use a stock voice, not a clone of anyone. In production, the
successor hears the expert's actual recording, and the agent only ever synthesizes its own interviewer voice.

**Roles on stage:** one **Speaker** who talks the whole time, and one **Driver** who only clicks. Don't combine
them.

---

## Version 1: live demo (3:00)

| Time | Screen (Driver) | Speaker says |
|---|---|---|
| **0:00 to 0:20 Hook** | App home | "Right now about ten thousand of Canada's most experienced public servants have applied to retire, and banks are in the same spot. When an expert leaves, we want an AI to keep what they know. But once it's in the AI, who gets to know it?" |
| **0:20 to 0:35 Where memory comes from** | As Dana: her memory list, each with a 🔒 🟠 🟢 level. Play 3 seconds of one clip. | "Dana is retiring. Handover interviewed her by voice. Every memory is stored in MongoDB Atlas with an owner, a level and an expiry. Dana decides who inherits each one." |
| **0:35 to 1:15 Same question, different people** | As **Jordan**, ask: "A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?" It's withheld, and the "Why this answer" card shows: allowed 🟢 only, withheld 🟠. Switch to **Sam** and ask the same thing: Dana's warning about the backup-screen zeros, her clip plays, and the card shows allowed 🟠 🟢, used m_2 and m_9. | "Jordan is an intern. Knowing how to push money past a sanctions hold isn't an intern's job, so the agent won't say. Sam is taking over Dana's role, so Sam inherits it, in Dana's own voice. Look at the card under each answer: same question, different access, different memories used. Last year Citigroup credited a client eighty-one trillion dollars instead of two hundred and eighty because of exactly this kind of backup-screen quirk." |
| **1:15 to 1:35 What everyone gets** | As Jordan, ask: "Who do I call if LedgerOne is down?" Jordan gets the answer. | "It's not just blocking. Jordan gets the general know-how every new person on the team should have." |
| **1:35 to 1:55 What nobody gets** | As Sam, ask: "Is there anything special about Halvorsen Freight's Friday wires?" Withheld. Show the audit log: the red, denied row. | "Even Sam doesn't get Dana's client-confidential arrangements. Every read is audited, allowed or denied. The filter runs inside the Atlas Vector Search query, so withheld memories never reach the model at all." |
| **1:55 to 2:20 Dana stays in control** | As Dana, click Forget on one memory. Switch to Sam: it's gone, and the runbook step built from it disappears live. | "Dana can correct or forget anything, and everything built from it goes too. Memories about systems being retired expire on their own." |
| **2:20 to 2:45 Under the hood** | Under the hood page, or the LangSmith trace | "It's all MongoDB Atlas. Vector Search with the access level as a pre-filter, hybrid search, a graph lookup that finds everything built from a memory and removes it in one transaction, change streams for live updates, and a TTL index for expiry. LangSmith shows exactly which memories each answer used." |
| **2:45 to 3:00 Close** | Title | "AI can read the code. It can't read the person. Handover captures what experts know and decides who inherits it. Built today on MongoDB Atlas." |

**If we're running long,** cut in this order: the "what everyone gets" beat, then half of "under the hood".

**Before each judge group:**
- Reseed the demo database (or click reset).
- Open these tabs: the app, the LangSmith trace pair (memory on vs off), and Atlas Data Explorer.
- Check that audio plays through the speakers.

---

## Version 2: 1-minute submission video

About 90 words of voiceover, with the visuals doing the work. Every shot comes from the real app: jump cuts
are fine, faked screens are not. Show code and Atlas at the end, because the rules require showing what we
built today.

| Time | Shot | Voiceover |
|---|---|---|
| 0:00 to 0:08 | Dana's memory list with 🔒 🟠 🟢 levels | "When an expert retires, Handover keeps what they know, and decides who inherits it." |
| 0:08 to 0:24 | Jordan asks about the held payment: withheld, the card shows 🟢 only. Sam asks the same thing: Dana's clip plays, the card shows 🟠 🟢 and the memories used. | "The intern doesn't get how to push money past a sanctions hold. The junior taking over does, in the expert's own voice." |
| 0:24 to 0:34 | Sam asks about Halvorsen: withheld, the audit row turns red | "Client-confidential memories go to nobody. Every read is audited." |
| 0:34 to 0:46 | Dana forgets a memory, Sam's runbook updates live | "The expert can correct or forget anything, and it disappears everywhere." |
| 0:46 to 1:00 | Repo code, Atlas collections, the LangSmith trace, the title card | "Access is enforced inside Atlas Vector Search. Built today on MongoDB Atlas, ElevenLabs, Gemini and LangGraph. Handover." |

**Recording plan:**
1. Record each beat separately at 1080p (Win+Alt+R or OBS), several takes each.
2. Record the voiceover in one take.
3. Edit in Clipchamp or CapCut, and play it back once with sound before submitting.

---

## Questions judges will grill us on

**"Prove memory changed behavior."**
Click "Open trace in LangSmith" on the card under any answer: it shows who asked, their allowed levels, and the exact memory ids used. For the strongest proof, open the trace pair. It's the same question from the same person, with memory on and off. With memory
on, the answer uses m_2 and m_9 (the backup-screen warning). With memory off, it's a generic answer with no
memories. Sam and Jordan getting different answers to the same question is proof too.

**"How do you know nothing leaks?"**
The access level is a pre-filter inside the `$vectorSearch` stage, so memories you can't see are never even
candidates and never reach the prompt. Withheld hits are counted without returning their text, and every read
goes to the audit log.

**"Why not just give everyone everything?"**
Banks run on need-to-know and segregation of duties, which regulators require. An intern who knows how to get a
payment past a sanctions hold is a fraud risk. A successor who knows a client's private arrangement is a
confidentiality breach.

**"What about engineering teams?"**
Everyone has the codebase, but not production credentials, customer data or security incident details. It's the
same engine with different levels.

**"Why not just have AI read the code and docs?"**
The backup-screen zeros, the R7 flag and the Halvorsen arrangement weren't in any code or doc. They were in
Dana's head. Klarna and Commonwealth Bank both cut staff for AI in the last two years and then reversed it.

**"Is that Dana's real voice?"**
Dana is fictional, so her clips use a stock voice, not a clone of anyone. In production, the successor hears the
expert's actual recording, and the agent only ever synthesizes its own interviewer voice.

**"What happens when a memory is wrong?"**
Correct makes a new version linked to the old one, and anything built from it is flagged for review. Forget
removes it and everything derived from it in one transaction, with an audit entry.
