# Juicer Kit v2.4.0

**A harness-agnostic operating system for AI-native software development.**

Juicer is built around a portable core plus thin harness adapters. Adding a new AI development tool should require an adapter, not a rewrite of the workflow.

Juicer Kit provides a portable workflow for planning, executing, reviewing, testing and shipping software with AI agents while keeping the human in control.

The kit is deliberately independent from a specific:

- CLI
- IDE
- agent harness
- model/provider
- MCP configuration
- session or chat history

The repository is the source of truth. Agent sessions are replaceable workers.

## Core principles

1. **Human control is the default**
   - Plans require approval before execution.
   - High-impact actions require explicit approval.
   - The user can stop, redirect, skip or delegate any unit of work.
   - "Approval" means a **Recorded Plan Approval** or **Recorded Ship
     Approval**: a record written by `juicer approve` /
     `juicer ship-approve`. It records *who* and *when*; it does not
     authenticate the person behind the keyboard, and it is not a
     barrier — it is evidence a later step reads. See
     [Safety gates](#safety-gates) and
     [Security and trust boundary](#security-and-trust-boundary).

2. **State lives in the repository**
   - Mission state, plan, decisions, handoffs and learnings are persisted under `.juicer/`.
   - A new session can resume without reconstructing the whole conversation.

3. **Skills are portable**
   - Canonical skills live in `.agents/skills/`.
   - Only Claude Code mirrors them into `.claude/skills/`; OpenCode, Cursor and Zed read `.agents/skills/` natively.

4. **Agents are workers, not the operating system**
   - Role definitions describe capabilities and responsibilities.
   - The workflow does not depend on one orchestrator being able to spawn another agent.

5. **Direct workers are first-class**
   - Workers such as finder, analyst, coder, reviewer, tester, security and devops can be invoked independently (full list in Roles).
   - Native harness delegation is optional.

6. **Every execution unit is checkable**
   - Inputs
   - objective
   - acceptance criteria
   - files/scope
   - verification
   - result
   - next action

## Architecture

```text
                         HUMAN
                           │
                    Mission / Decision
                           │
                           ▼
                    ┌──────────────┐
                    │  .juicer/    │
                    │ source state │
                    └──────┬───────┘
                           │
                 ┌─────────┴─────────┐
                 │                   │
           Portable skills       Worker roles
           .agents/skills/       agents/*.md
                  │                   │
                  └─────────┬─────────┘
                            │
        ┌──────────┬────────┼────────┬──────────┐
        ▼          ▼        ▼        ▼          ▼
    OpenCode    Claude    Cursor    Codex      Zed
      adapter   adapter   adapter  adapter    adapter
        │          │        │        │          │
        └──────────┴────────┴────────┴──────────┘
                            │
                            ▼
                        MODEL(S)
```

## Install

Copy the repository into a project, or use the included installer:

```bash
./bin/juicer init
```

Then:

```bash
./bin/juicer status
./bin/juicer mission "Build feature X"
```

The installer creates the runtime state and mirrors workers and portable
skills into supported harness locations. It refuses to run in a
subdirectory of an existing Juicer workspace unless you pass `--nested`,
which creates a separate workspace root there on purpose. The
`.gitignore` block it writes lists the exact paths Juicer generates, not
whole harness directories, so your own harness configuration stays
tracked. In a git repository it also installs a `pre-commit` guard
against direct commits on `main`/`master` (escapes: `--no-verify`,
`JUICER_NO_GIT_GUARD=1`, `juicer init --no-git-guard`); existing hook
content is preserved and `core.hooksPath` is never set.

Adapters are executable Python. By default only the adapters bundled
with the kit are loaded; to load adapters from the project's
`adapters/` directory, pass `--trust-project-adapters` or set
`JUICER_TRUST_PROJECT_ADAPTERS=1`. See the `Trust` section of
`docs/adapter-contract.md`.

## Primary workflow

```text
MISSION
  ↓
DISCOVER
  ↓
PLAN
  ↓
RECORDED PLAN APPROVAL
  ↓
EXECUTE ONE UNIT
  ↓
VERIFY
  ↓
CHECKPOINT
  ↓
NEXT UNIT
  ↓
REVIEW
  ↓
TEST
  ↓
RECORDED SHIP APPROVAL
```

The orchestrator is intentionally **not required** for this flow.

## Roles

| Role | Responsibility |
|---|---|
| finder | Fast repository reconnaissance |
| analyst | Deep technical analysis |
| researcher | External technical research |
| architect | Solution architecture |
| planner | Atomic implementation plan |
| coder | New implementation |
| editor | Safe modification of existing code |
| fixer | Minimal bug correction |
| refactorer | Structural improvement without behavior change |
| reviewer | Code quality and regression review |
| tester | Test design and execution |
| debugger | Unknown-cause investigation |
| security | Security review |
| documenter | Documentation |
| devops | CI/CD, infrastructure and release |
| optimizer | Performance investigation |

## Direct subagent usage

The kit does not assume a universal delegation API.

Where the harness supports native subagents, use its native mechanism. Where it does not, run the worker directly with the same role definition and attach the current `.juicer/` state.

Examples:

```text
OpenCode: @finder ...
Claude Code: invoke the finder agent
Cursor: /create-subagent or run the corresponding skill/mode
Zed: use a native or external agent path and provide the worker prompt
```

The important invariant is not the invocation syntax. The invariant is the **role contract + repository state + acceptance criteria**.

## Safety gates

The kit defines four gates. What actually stops you differs per gate, and
the difference matters:

- **Mechanically enforced** — `bin/juicer` refuses the command and exits
  1. Only the shell boundary, file permissions and the harness can be
  bypassed on top of that.
- **Workflow convention** — nothing in the CLI stops you. Compliance
  depends on the agent (or human) following the contract. Treat these as
  process rules, not barriers.
- **Harness-dependent** — Juicer writes configuration a harness *may*
  honour. Juicer cannot verify that it does; see
  [`docs/security.md`](docs/security.md) §6 for what each harness
  actually enforces.
- **Recorded evidence** — Juicer persists a record that a later command
  or a human reads. A record is evidence, never a barrier: nothing in
  Juicer stops a process that ignores it.

| Gate | Kind | What actually stops you |
|---|---|---|
| 1 — Plan (Recorded Plan Approval) | mechanical | `juicer start` and `juicer ship-approve` refuse without a valid, unmodified plan approval record |
| 2 — Change | convention | nothing — `juicer start UNIT` records only the unit id; scope and acceptance criteria live as prose in `.juicer/plan.md` |
| 3 — Verify | convention | nothing — `juicer checkpoint done` and `juicer finish` transition on state alone; the CLI never checks that tests ran |
| 4 — Ship (Recorded Ship Approval) | mechanical gate + recorded evidence | `juicer ship-approve` writes `ship_approved` and a record bound to the approved target; the CLI itself runs nothing, so release skills and workflows must read the flag via `juicer status` — that last step is a rule, not a barrier |

### Gate 1 — Plan (Recorded Plan Approval)
No `juicer start` before the current mission plan is approved. The
record stores the plan and mission digests plus `mission_id`; editing
either file after approval invalidates it until `juicer approve` runs
again, and `juicer status` reports the reason. The record is evidence
that a process naming itself as `by` approved that exact content — it is
not proof that a specific person was at the keyboard.

### Gate 2 — Change
Every implementation unit records its scope and acceptance criteria.
This is a rule for humans and agents. The CLI stores the unit id
(`juicer start UNIT-001`) and nothing else — it does not parse or verify
scope.

### Gate 3 — Verify
Implementation is not considered complete until the relevant verification
has been executed or an explicit exception is recorded. This is a rule
for humans and agents. The CLI has no verification field and does not
confirm that any test ran.

### Gate 4 — Ship (Recorded Ship Approval)
Production-impacting changes require a recorded approval, stored as
`ship_approved: true` plus a `ship_approval` object in
`.juicer/state.json` by `./bin/juicer ship-approve`. The record binds the
plan, mission and active unit, plus — in a git repository — the commit
and working tree (`code_binding: "sha"`). Outside git, or when git fails,
`code_binding` is `"none"` / `"failed"` and `juicer status` warns: that
approval does **not** cover source changes. The CLI runs no production
command itself; release skills and workflows must verify the flag via
`./bin/juicer status` and stop while it is `false`. That final step is a
rule the harness and the human must uphold — the CLI cannot force a
process to stop.

### Identity, not authentication
Both approval commands require an identity: the OS user when stdin is a
TTY, otherwise an explicit `--by=<id>`. The record stores `by`, `at`,
`via`, `revision` and the approved target digest. It proves that a
process identifying itself as `by` wrote the record; it does **not**
prove who was at the keyboard. The harness may add its own confirmation
in front of these commands — Juicer does not provide that and does not
verify it.

## Security and trust boundary

What `juicer` itself guarantees, what it delegates to the harness, and
what it cannot guarantee at all, is documented in
[`docs/security.md`](docs/security.md).

```text
Human / External Authority
          ↓
Harness / Environment
          ↓
Juicer Core
          ↓
      Project
```

In short:

- **Human / External Authority** owns the decision to approve. Juicer
  records an identity; it does not authenticate a person.
- **Harness / Environment** is where isolation, shell permission, the OS
  filesystem boundary and command confirmation come from. Juicer neither
  provides nor verifies any of them.
- **Juicer Core** confines every write to the project root, keeps
  `state.json` atomic and revision-fenced, refuses illegal gate
  transitions, and binds approvals to the content they approved.
- **Project** is untrusted input: `agents/*.md`, `.agents/skills/**`,
  `.juicer/*.md` and `adapters/*/adapter.py` are all repository content
  that a compromised repository controls.

`.juicer/state.json` is an ordinary file in the working tree. Any process
running with your privileges can rewrite it. The file's integrity is only
as good as the OS permissions on the repository.

## Context economy

Workers should not read the entire repository or entire chat history by default.

They should:

1. Read `.juicer/mission.md`.
2. Read the active plan unit.
3. Read only the relevant project instructions.
4. Inspect the smallest useful code scope.
5. Write a concise checkpoint.
6. Leave reusable learning in `.juicer/learnings.md`.

This makes long-running work resumable and reduces token waste.

## Compatibility

Current adapters:

- Codex
- OpenCode
- Claude Code
- Cursor
- Zed

These are examples, not architectural dependencies. A future Gemini CLI, Aider, Windsurf, Kiro or custom harness should be added as an adapter under `adapters/<name>/` without changing `.juicer/`, `agents/`, `.agents/skills/` or the workflows.

OpenCode currently supports project skills under `.opencode/skills` as well as Claude-compatible and `.agents/skills` locations. Claude Code supports filesystem skills under `.claude/skills`. Cursor supports the Agent Skills standard and `.agents/skills`. Zed supports native skills/instructions and external ACP agents. The kit therefore treats the portable filesystem contract as primary and native harness configuration as an adapter. 

## Versioning

Juicer Kit v2 intentionally replaces the v1 architecture instead of incrementally extending it.

Recommended project update (from a checkout of the kit):

```bash
./juicer-kit/bin/juicer init
./juicer-kit/bin/juicer sync all
```

`init` is idempotent: it fills in the files your project does not have
yet and never overwrites your edits. `sync all` regenerates the harness
mirrors; those mirrors are listed in `.gitignore` and must not be
committed. To pick up kit changes in files you already have, diff them
against the kit checkout.

## License

MIT.


## Documentation

Source: https://github.com/diogocvc/juicer-kit

- English: `docs/GUIDE.md`
- Português: `docs/GUIDE.pt-BR.md`
- Architecture: `docs/architecture.md`
- Adapter Contract: `docs/adapter-contract.md`
- Security model: `docs/security.md`
- Installation: `docs/installation.md`
- Worker Protocol: `docs/worker-protocol.md`
- Migration from v1: `docs/migration-v1.md`
- Changelog: `CHANGELOG.md`
