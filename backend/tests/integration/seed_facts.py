"""What the seeded demo data (backend/seed.py) lets each role read. Shared by the integration tests."""

PASSCODES = {"u_expert": "dana-pass", "u_successor": "sam-pass", "u_outsider": "jordan-pass"}
ALL_MEMORIES = {f"m_{i}" for i in range(1, 10)}
SCOPE = {"m_1": "successor", "m_2": "successor", "m_3": "successor", "m_4": "never_transfer", "m_5": "team",
         "m_6": "team", "m_7": "successor", "m_8": "team", "m_9": "successor"}
READABLE = {
    "u_expert": ALL_MEMORIES,
    "u_successor": {m for m, s in SCOPE.items() if s in ("successor", "team")},
    "u_outsider": {m for m, s in SCOPE.items() if s == "team"},
}
