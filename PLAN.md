# Handover: Governed Memory Engine

Track 2: Memory You Can Govern.

Handover is a voice agent that runs exit interviews with a senior employee across their last few weeks and remembers what they know. The expert controls that memory: who inherits each piece, how long it lives, and whether it gets corrected or forgotten. Their successor asks questions and hears the expert's real recorded answers.

Demo: a retiring bank operations lead. Product: a governed memory engine for any knowledge that would otherwise leave with someone.

## What makes it different (say this to judges)
1. The agent hunts for what's missing: it finds gaps and contradictions across sessions and asks about them.
2. Memory is inherited: ownership moves from expert to successor, with scopes (successor, team, never_transfer).
3. Forget cascades: removing a memory updates the runbook steps built from it, live.
4. Only the interviewer voice is synthesized. The expert's voice is always a real recording.

## MongoDB features (use all of these, deliberately)
- Atlas Sandbox cluster (required for finalists)
- $jsonSchema validation: every memory needs owner, scope, expires_at, source_clip_id
- Atlas Vector Search with pre-filter on scope, owner, status (leak prevention happens in the query)
- Voyage AI embeddings (MongoDB owned), voyage-3 family
- Hybrid search: Atlas Search (keyword, for system names like "SWIFT queue") + Vector Search, combined with $rankFusion
- TTL index on expires_at (memories about retired systems expire)
- Change streams: push hide/forget/correct to the successor UI live, and drive the cascade worker
- $graphLookup over derived_from: find everything built from a memory, for cascade forget and for "why does the agent know this"
- Multi-document transaction: forget + cascade + audit entry commit together
- LangGraph MongoDBSaver checkpointer: interview state survives restarts
- audit_log collection: every read and governance action, who and why
- Dev: MongoDB MCP Server + MongoDB Agent Skills in Claude Code

## Collections
- people: name, role (expert, successor, outsider)
- clips: owner_id, audio_url, transcript, session_id
- memories: owner_id, kind (procedure, system, client, workaround), text, embedding, scope, status (active, corrected, forgotten), version, supersedes, derived_from, source_clip_id, session_id, created_at, expires_at
- runbook_steps: text, derived_from (memory ids), status
- gaps: owner_id, question, from_memory_ids, kind (missing, contradiction), status
- audit_log: actor_id, action, memory_ids, allowed, reason, ts

## Team
- Ayuub: backend, Atlas, memory engine, agent loop
- Teammate 2: frontend (expert view, successor view, live updates, memory on vs off)
- Teammate 3: demo script, recorded expert sessions, pitch, 1 minute video, README

## Must haves
1. Session 2 asks a contradiction/gap follow-up from session 1
2. Successor asks, gets scope-filtered answer + real clip; outsider gets blocked
3. Expert forgets a memory: runbook step disappears live, audit entry shows
4. Memory on vs off side by side

## Times
Code freeze 4:00. Submissions due 5:00 PM. Judging 5:15. Top 6 at 7:00.

## Compliance checklist (from the official resource guide + participant guide)

### Problem Statement 2: Memory You Can Govern
- [ ] Atlas + Vector Search persist and retrieve memory
- [ ] Memory changes what the agent does on the next run (session 2 asks about session 1 gaps; memory on vs off demo)
- [ ] Rules for who can read each memory (scope pre-filter: successor / team / never_transfer)
- [ ] Rules for how long it lives (expires_at + TTL index)
- [ ] Rules for how it gets corrected (versioned correct, supersedes link) or forgotten (cascade via $graphLookup, in a transaction)
- [ ] Q1 leakage: outsider and successor see different results for the same question, enforced in the query, logged in audit_log
- [ ] Q2 wrong/expired: show a correction and an expiry live
- [ ] Q3 proof: memory on vs off side by side + LangSmith trace naming the memory ids that drove the decision
- [ ] Atlas is the data, memory AND state layer (LangGraph MongoDBSaver checkpointer for interview state)

### Hackathon requirements
- [ ] Project + cluster created through the Atlas Sandbox invite (Agents in Context Toronto org). Not a personal cluster.
- [ ] All work original, written today (commit history starts today)
- [ ] Repo public (done) and demo link accessible
- [ ] Team of 4 or fewer
- [ ] Live, in-person demo works on our laptop with venue wifi (have a recorded backup)

### Submission (Cerebral Valley platform, due 5:00 PM)
- [ ] Public GitHub repo link
- [ ] 1-minute demo video showing code AND functionality built today, with audio checked
- [ ] Concise project description
- [ ] All teammates added to the submission

### Rules / disqualification risks
- [ ] Demo only shows what we built today
- [ ] No code, data or assets we don't have rights to. Use fake bank data only. Record teammates (with consent) as the expert. Never clone a real person's voice.
- [ ] Not on the anti-project list: not basic RAG (lead with governance + agent loop), no Streamlit (we use React), dashboard is not the main feature, no medical advice

### Judging (Round 1: Demo 35, Difficulty 30, Creativity 15, Impact 20. ~3 min demo + 1-2 min Q&A)
- [ ] Demo 35: one clean live flow, rehearsed 3+ times, backup video ready
- [ ] Difficulty 30: show the hard parts on screen (pre-filtered vector search, hybrid $rankFusion, $graphLookup cascade, transaction, change stream, checkpointer)
- [ ] Creativity 15: agent hunts gaps and contradictions; memory is inherited, not just stored
- [ ] Impact 20: knowledge loss when senior staff leave; works for banks, on-call, plant operators
- [ ] Round 2 (top 6, 7:00 PM): same criteria, equal weight, 3 min + 2 min Q&A

### Bonus prizes
- [ ] ElevenLabs: speech to text + interviewer voice (Best Project Built with ElevenLabs)
- [ ] LangSmith traces visible in demo

### Recommended setup from the guide
- [ ] MongoDB Agent Skills installed in Claude Code
- [ ] MongoDB MCP Server connected
- [ ] Voyage AI key (200M free tokens) or Automated Embeddings
