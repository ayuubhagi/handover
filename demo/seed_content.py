"""Demo content for Handover: what Dana says, what Sam asks, and the seed rows built from it.

Each of Dana's memories is a fictional version of a real failure mode, so we can defend it when judges
grill us. Real incidents and sources are in demo/RESEARCH.md. The bank (Northgate), its systems
(LoanDesk, LedgerOne, PAY-08) and its clients are made up.

For Ayuub: CLIPS, MEMORIES, RUNBOOK and GAPS use the same shapes as backend/seed.py, so they can be
pasted in to replace the current lists. The audio in backend/seed_audio/c_N.mp3 is generated from CLIPS.
"""

# Dana's recorded answers (session 1). These exact strings are what the ElevenLabs Dana voice reads.
CLIPS = {
    "c_1": "When the overnight payments batch stalls, restart the payments queue before you touch the ledger "
           "database. If you restart the database first, the batch reloads and every payment in it posts twice. "
           "Then you spend the whole morning reversing them.",
    "c_2": "Interest-only payments on the syndicated loans are where people get hurt. In LoanDesk, setting the "
           "principal to the wash account is not enough. You also have to set the front and fund fields to the "
           "wash account, or the system pays the principal out of our own cash. Three people approve that "
           "screen, and none of them will catch it, because they're all looking at the same screen.",
    "c_3": "Halvorsen Freight is our touchiest client. Their treasurer, Ingrid, has a standing verbal agreement "
           "that we release their Friday wires up to two million without the second approver. "
           "That is not written down anywhere.",
    "c_4": "Never reuse routing flag R7 for anything new. It used to switch on the old auto-release router. "
           "That code is dead everywhere except PAY-08, which nobody has switched off yet. If R7 gets turned on "
           "and PAY-08 picks up the job, it starts releasing payments on its own. PAY-08 is supposed to be "
           "decommissioned at the end of the month.",
    "c_5": "The reconciliation report from LedgerOne is always wrong on the first business day of the month, "
           "because of a timezone bug. Rerun it after ten a.m. Eastern and it comes out right.",
    "c_6": "For a stalled batch, actually, the first thing I do is check the ledger database locks, clear them, "
           "and only then worry about the queue.",
    "c_7": "On-call escalation goes to the payments ops duty manager first, then to the LedgerOne vendor hotline "
           "if it's still down after thirty minutes. The hotline is useless before then.",
}

# id, clip, kind, scope, text, expires in days (None = default), derived_from
MEMORIES = [
    ("m_1", "c_1", "procedure", "successor",
     "When the overnight payments batch stalls, restart the payments queue before touching the ledger database. "
     "Restarting the database first reloads the batch and every payment posts twice.", None, []),
    ("m_2", "c_2", "procedure", "successor",
     "Interest-only payments on syndicated loans in LoanDesk: set the principal, front and fund fields all to the "
     "wash account. If only principal is set, LoanDesk pays the principal out of the bank's own cash.", None, []),
    ("m_3", "c_2", "workaround", "team",
     "The three-person approval on the LoanDesk payment screen does not catch wash account mistakes, because every "
     "approver sees the same screen. Do not rely on the approvers to catch it.", None, []),
    ("m_4", "c_3", "client", "never_transfer",
     "Halvorsen Freight has a verbal agreement with treasurer Ingrid: Friday wires up to 2 million are released "
     "without the second approver. It is not documented anywhere.", None, []),
    ("m_5", "c_4", "system", "successor",
     "Never reuse routing flag R7. It used to enable the old auto-release router, and that code still runs on "
     "PAY-08. If R7 is turned on and PAY-08 picks up the job, it releases payments on its own. "
     "PAY-08 is decommissioned at the end of the month.", 21, []),
    ("m_6", "c_5", "workaround", "successor",
     "The LedgerOne reconciliation report is wrong on the first business day of each month because of a timezone bug. "
     "Rerun it after 10 a.m. Eastern.", None, []),
    ("m_7", "c_6", "procedure", "successor",
     "For a stalled payments batch, first check and clear the ledger database locks, then deal with the queue.",
     None, []),
    ("m_8", "c_7", "procedure", "team",
     "On-call escalation: payments ops duty manager first, then the LedgerOne vendor hotline if the outage "
     "lasts more than 30 minutes.", None, []),
    ("m_9", "c_2", "procedure", "successor",
     "Interest-only loan payment checklist: set principal, front and fund to the wash account, and check the fields "
     "yourself. The three-person approval will not catch a mistake here.", None, ["m_2", "m_3"]),
]

RUNBOOK = [
    ("r_1", "Stalled overnight batch: restart the payments queue before touching the ledger database.", ["m_1"]),
    ("r_2", "Interest-only loan payment: set principal, front and fund to the wash account, then check the fields "
            "yourself before approval.", ["m_9"]),
    ("r_3", "First business day of the month: rerun the LedgerOne reconciliation report after 10 a.m. Eastern.", ["m_6"]),
    ("r_4", "Routing flags: never reuse R7 while PAY-08 is still running.", ["m_5"]),
    ("r_5", "Outage over 30 minutes: escalate to the duty manager, then the LedgerOne vendor hotline.", ["m_8"]),
    ("r_6", "Friday wires for Halvorsen Freight: follow the release arrangement agreed with their treasurer.", ["m_4"]),
]

GAPS = [
    ("g_1", "contradiction",
     "You told me to restart the payments queue before touching the ledger database, but you also said you clear "
     "the database locks first. Which one comes first when the batch stalls?", ["m_1", "m_7"]),
    ("g_2", "missing",
     "You said to set the front and fund fields to the wash account. Is there any way to check those before the "
     "payment actually goes out?", ["m_2"]),
]

# Dana's answer to the contradiction (g_1), used live in session 2. Upload it as the answer audio if the mic or
# wifi fails on stage.
DANA_LIVE_ANSWERS = {
    "dana_answer_g1": "Good catch. Clear the database locks first, but never restart the database. Clearing locks is "
                      "safe. Restarting the database is what reloads the batch and causes the duplicates. "
                      "So: clear the locks, then restart the queue.",
}

# What Sam asks in the demo, in Sam's voice. Each one is chosen to land a specific point.
SAM_QUESTIONS = {
    "sam_q1_batch": "The overnight batch just stalled. What do I do first?",
    "sam_q2_interest": "I'm sending the interest-only payment on a syndicated loan tonight. Anything I need to watch for?",
    "sam_q3_flag": "Can I reuse routing flag R7 for the new instant payments feature?",
    "sam_q4_halvorsen": "Is there anything special about Halvorsen Freight's Friday wires?",
}
