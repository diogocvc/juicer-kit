---
name: context-management
description: Use this skill to optimize token usage, manage context efficiently, and hand off work between agents using artifact references.
---

# Skill: Context Management

Use this skill to keep context small, accurate and portable. It covers
pruning, summarization, selective loading and — following Section 16 of the
Structural Document — **handoffs by artifact reference**, not by replaying
conversations.

## Context Tiers

Load in this order; stop as soon as the question is answered:

1. **Task contract** — id, description, acceptance criteria, `scope.paths`,
   `task.checks`, gates. This is always in scope.
2. **Artifacts** — maps, diagnoses, designs, plans, review/security evidence.
   Reference by path and commit/tree; do not paste them.
3. **Repository slice** — only the files named by the map or needed to verify a
   claim.
4. **Full repository** — almost never; use `@finder` first.

## Strategies

### 1. Context pruning

- Remove files unrelated to the current activity.
- Keep the task contract, active decisions and evidence references.
- Drop completed sub-task transcripts once their artifact exists.

### 2. Summarization

- When a session grows long, compact it (see `/compact` below).
- Keep decisions, open questions, action items and evidence links.
- Discard intermediate reasoning and repeated explanations.

### 3. Selective loading

- Use `@finder` for a location map before reading files.
- Read specific sections (line ranges) for large files.
- Grep for the symbol or error string instead of loading a whole tree.

### 4. Reference, do not repeat

- Point to artifacts: `docs/...`, `backlog/...`, `.juicer/evidence/...`,
  `path:line`, commit/tree.
- Do not restate a plan or decision that already has a canonical artifact.
- If an artifact is stale, say so and name the newer commit/tree.

### 5. Avoid bloat

- Do not paste whole conversations into a handoff.
- Do not include secrets, tokens or personal data.
- Do not carry speculation as context; convert it to an Open Question.

## Handoffs (Structural Document, Section 16)

A handoff transfers **state**, not conversation. The receiving activity must be
able to continue from the handoff alone, without the sender's history.

### Principles

- **Artifact-first** — link to files, commits, evidence and task ids.
- **Bounded** — one screen: objective, decisions, evidence, open questions,
  next action.
- **Scoped** — state `scope.paths` and what was explicitly not touched.
- **Fresh** — include the commit/tree; flag anything older.
- **Honest** — separate facts, claims and unknowns; `UNKNOWN` is allowed.
- **Safe** — no secrets, credentials, PII or raw logs with sensitive data.
- **Idempotent** — the receiver can re-read the artifacts and reach the same
  state.

### Handoff packet

```json
{
  "handoff_id": "HANDOFF-TASK-001-002",
  "from_activity": "diagnosis",
  "to_activity": "bugfix",
  "task_id": "TASK-001",
  "commit": "abc1234",
  "tree_hash": "def5678",
  "objective": "Remove the confirmed null-dereference in the invoice parser.",
  "scope": {"paths": ["src/billing/"], "constraints": ["no API changes"]},
  "artifacts": [
    {"kind": "diagnosis", "path": ".juicer/evidence/diagnosis-TASK-001.json", "commit": "abc1234"},
    {"kind": "failing_test", "path": "tests/billing/test_invoice.py::test_null_customer", "commit": "abc1234"}
  ],
  "decisions": [
    {"decision": "Fix at the parser boundary", "reason": "All callers pass raw input"}
  ],
  "evidence": [
    {"claim": "Null customer reaches line 42", "source": "trace + test output"}
  ],
  "open_questions": [
    {"question": "Should a missing customer be rejected or defaulted?", "owner": "human"}
  ],
  "next_action": "Add the regression test, then apply the minimal fix.",
  "do_not_redo": ["root-cause investigation", "reproduction"],
  "blockers": []
}
```

### Handoff rules

- The receiver **consumes** the handoff; it does not repeat completed work
  listed in `do_not_redo` unless it finds a concrete contradiction.
- If the commit/tree differs from the current workspace, treat the handoff as
  stale and report it before acting.
- If an artifact is missing or unreadable, report `BLOCKED`; do not reconstruct
  it from memory.
- Keep the handoff in the repository (or `.juicer/evidence/`) when it must
  survive the session; chat-only handoffs are not durable.

### What not to hand off

- The full conversation or intermediate reasoning.
- Secrets, tokens, `.env` contents or PII.
- Unverified claims presented as facts.
- A scope broader than the task contract.

## `/compact` Summary Template

```
## Session Summary

### Objective
[One sentence]

### Decisions
- [Decision, reason, artifact/commit]

### Evidence
- [Artifact path, commit/tree, what it proves]

### Scope Touched
- [paths]

### Open Questions
- [Question, owner, why it matters]

### Next Action
- [Single next step]
```

## Rules

- Prune before the context becomes unmanageable; summarize proactively.
- Never lose a decision, an open question or an evidence link.
- Never paste a transcript when an artifact reference will do.
- Never include secrets or PII in context or handoffs.
- Mark assumptions explicitly; `UNKNOWN` is better than a confident guess.
- The core state in `.juicer/` is canonical; do not recreate it in prose.
