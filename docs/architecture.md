# Architecture

## 1. Portable core

The portable core is:

- `.juicer/` — state
- `agents/` — role contracts
- `.agents/skills/` — portable skills
- `bin/juicer` — deterministic state controller

None of these requires an AI provider.

## 2. Harness adapters

Adapters translate native capabilities into the same role contracts.

A harness may provide:

- native subagents
- skills
- slash commands
- modes
- ACP
- MCP
- approval controls

These are accelerators, not dependencies.

## 3. State machine

`bin/juicer` enforces every gate command against this table before writing
state. An illegal transition exits 1 with `Cannot <command> from status=<state>`.

```text
idle
  ↓ mission
planning
  ↓ approve
ready
  ↓ start
executing ── checkpoint blocked ──→ blocked
    │ ↑                              │
    │ └────── checkpoint executing ←─┘
    │ (repeat while units remain)
    ├─ checkpoint ready → ready ──┐
    └─ checkpoint done → ready    │  (current_unit cleared on ready/done)
                                  ↓
                    finish → done → ship-approve
```

Transition table (source states accepted per command):

| Command | From | To |
|---|---|---|
| `mission` | idle, planning, ready, blocked, done | planning |
| `approve` | planning, blocked, ready, done | ready from planning/blocked; otherwise unchanged |
| `start` | ready, blocked (requires `approved`) | executing |
| `checkpoint executing` | executing, blocked | executing |
| `checkpoint blocked` | executing, blocked | blocked |
| `checkpoint ready` | executing, blocked, ready | ready |
| `checkpoint done` | ready | done |
| `finish` | ready, done | done |
| `ship-approve` | ready, done | — (sets `ship_approved`) |

Rules:

- `start` checks the approval gate first, so an unapproved attempt always
  fails with `Blocked: the plan has not been approved; run juicer approve
  first.` The message then names the specific failure: a missing/invalid
  record, or a plan/mission that changed after approval.
- An approval covers the **content** of `.juicer/plan.md`,
  `.juicer/mission.md` and `mission_id` at the moment it was recorded.
  Editing either file afterwards invalidates it until `approve` runs
  again; `done` is an accepted source state precisely so a plan edited
  after `finish` can be re-approved before shipping.
- Only one unit is active at a time: `start` is rejected while `executing`.
- `mission` is rejected while `executing`; a new mission resets
  `approved`, `ship_approved` and `current_unit`.
- `current_unit` is cleared by `checkpoint ready`/`checkpoint done` and
  kept by `checkpoint blocked`.
- `status` prints the commands available in the current state.

## 4. Why this fixes the v1 problem

The previous design made the OpenCode agent layer too central. A failure or behavioral change in the orchestrator could therefore affect the entire workflow.

v2 separates:

- workflow state
- role definitions
- skills
- native delegation
- model selection
- user approval

A broken native orchestrator no longer destroys the underlying workflow.

## 5. Direct worker execution

Every worker is independently addressable.

The worker receives the same state whether it is:

- delegated by another agent
- invoked directly by the user
- started from an IDE mode
- run in an external ACP agent
- run in a CLI session

## 6. Locking and state integrity

- Every read-modify-write (`update_state`, `write_state`) runs under an
  exclusive `flock` on `.juicer/state.lock`. The lock is reentrant
  within one process.
- Writes are atomic: temp file in `.juicer/`, `fsync`, then `rename`.
- `_fenced_write` requires `revision == disk revision + 1`, so a stale
  writer fails instead of restoring old state.
- On a platform without `fcntl` the lock degrades to a no-op and the CLI
  says so once on stderr; the revision fence still applies.

## 7. Root discovery and confinement

- Commands walk up from the working directory to the nearest directory
  containing `.juicer/state.json`. With no workspace they fail cleanly
  and never create one as a side effect.
- `juicer init` targets the current directory. Creating a workspace
  underneath an existing one requires `--nested`; the two roots stay
  separate, and a test asserts that.
- Every CLI write resolves strictly inside the root. Adapter output
  additionally refuses `.juicer/`, `.git/` and `.gitignore`, and must
  fall inside the paths the adapter declares (`agents_dir`,
  `skills_dir`, marker file).
- Only manifest-recorded, adapter-owned paths are ever deleted.

## 8. Trust boundary

```text
Human / External Authority
          ↓
Harness / Environment
          ↓
Juicer Core
          ↓
      Project
```

The human decides; the harness/OS enforces shell and filesystem
permissions; Juicer records state, gates and approvals; project content
is untrusted input. `adapters/*/adapter.py` is executable Python and is
not imported unless `--trust-project-adapters` or
`JUICER_TRUST_PROJECT_ADAPTERS=1` is given.

The full threat model, what is mechanical versus conventional, and the
complete limitation list live in [`security.md`](security.md). Where the
two documents overlap, `security.md` is authoritative.
