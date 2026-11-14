# 1-minute video: recording script

Record about 2 minutes raw, in one continuous screen recording at 1080p with mic audio. Claude cuts it to under
60s and adds captions. Speak each line, then **pause 1 second** before the next click. The pauses are where the
cuts go.

**Before recording:** reseed the demo DB, close other tabs, turn the volume up (clip audio has to be in the
recording), and start on Dana, Record mode.

| # | Who | Do | Say (you, the narrator) | Keeps in final cut |
|---|---|---|---|---|
| 1 | Dana · Senior | Home screen, Record mode | "Dana runs payments at a bank and she's retiring. Handover interviews her so her knowledge stays." | ~5s |
| 2 | Dana | Click **Call**. The interviewer asks open gap g_1 (queue vs locks). | (let it ask) | ~6s |
| 3 | Dana | Answer out loud: *"Clear the database locks first. Never restart the database. Then restart the queue."* | (your answer is the line) | ~7s |
| 4 | Dana | It asks gap g_2 (catching a wrong amount on the backup screen). Answer: *"Check the amount against the original wire before you release it, every time."* End the call. | "It found the contradictions and gaps in what she'd said, and asked about them." | ~7s |
| 5 | Dana | Open **Desk ledger**. Hover one 🔒, one 🟠, one 🟢 badge. | "Every memory goes in the desk ledger with an access level. Dana decides who inherits what." | ~7s |
| 6 | Jordan · Intern | Switch role. Ask: *"A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?"* | "Jordan's an intern. Pushing money past a sanctions hold isn't an intern's call, so it's withheld." | ~7s |
| 7 | Jordan | Ask: *"Who do I call if LedgerOne is down?"* | "But Jordan still gets the team know-how." | ~4s |
| 8 | Sam · Junior | Switch role. Click **Call** and ask the sanctions question out loud. Let the answer play, then Dana's clip. | "Sam is taking over, so Sam inherits it, in Dana's own voice." | ~9s |
| 9 | Sam | Type: *"Is there anything special about Halvorsen Freight's Friday wires?"* It's withheld. | "Client secrets stay with Dana. Even Sam doesn't get them." | ~5s |
| 10 | Dana | Switch back, open the Desk ledger: she sees all of it, including 🔒 Halvorsen. | "Only Dana sees everything. Built on MongoDB Atlas. Handover." | ~5s |

Total ≈ 58s. Who sees what (the point of the video):

| | 🔒 Senior only | 🟠 Successor | 🟢 Team |
|---|---|---|---|
| Dana | ✅ | ✅ | ✅ |
| Sam | ❌ | ✅ | ✅ |
| Jordan | ❌ | ❌ | ✅ |

**If a beat flops** (slow answer, wrong source), just say "again" and redo that beat right away. I'll cut the bad take.

## Editing (Claude does this when you send the raw file)

1. Cut silences and loading spinners, and speed up model waits 2–3x (ffmpeg).
2. Keep the best take of each beat, in the order above. Hard cuts only, no faked screens.
3. Burn in captions from a speech-to-text transcript (ElevenLabs, key already in `.env`), white text with a dark box at
   the bottom. Add a small role label per beat ("Dana · Senior", and so on).
4. Export 1080p MP4 under 60s, loudness normalized. Check it once with sound before submitting.
