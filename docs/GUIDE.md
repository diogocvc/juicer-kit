# Juicer Kit Complete Guide

**Version 4.1.0** — activity-oriented Markdown kit (agents, commands, skills)
plus the executable orchestration core (`juicer/` + `bin/juicer`).

**Target harness**: OpenCode 2.x/V2, measured in this environment as
`opencode v2.2.7`. V1 binaries may be detected for diagnostics but are
`degraded`; compatibility with V1 is not promised. Measured capabilities and
known gaps are recorded in [`STATUS.md`](../STATUS.md).

> **What changed in 4.1.0** — Juicer Kit now uses a **capability model**: agents
> are activity-oriented capabilities selected per task, not fixed personas in a
> mandatory chain. The executable core (`juicer/` + `bin/juicer`) is the owner
> of scope, deterministic checks, evidence, gates and integration. This guide
> describes that model; if an older example conflicts with it, the capability
> model and the core win.

## Table of Contents

1. [Introduction](#introduction)
2. [What is Juicer Kit](#what-is-juicer-kit)
3. [Who This Guide Is For](#who-this-guide-is-for)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
   - [Option 1: Manual Copy](#option-1-manual-copy)
   - [Option 2: Git Submodule](#option-2-git-submodule)
   - [Option 3: Orchestration Core](#option-3-orchestration-core)
   - [Option 4: Symlink](#option-4-symlink)
6. [Kit Structure](#kit-structure)
7. [Initial Setup](#initial-setup)
8. [Getting Started](#getting-started)
   - [Starting OpenCode](#starting-opencode)
   - [Testing Agents](#testing-agents)
9. [Orchestration Core (4.1.0)](#orchestration-core-410)
   - [What the Core Does](#what-the-core-does)
   - [State and Ownership](#state-and-ownership)
   - [Quick Start](#quick-start)
   - [CLI Commands](#cli-commands)
   - [Gates and Human Approval](#gates-and-human-approval)
   - [Resume and Recovery](#resume-and-recovery)
   - [Measured Capabilities and Limitations](#measured-capabilities-and-limitations)
10. [Backlog System](#backlog-system)
    - [What is the Backlog](#what-is-the-backlog)
    - [Adding Tasks](#adding-tasks)
    - [Viewing the Backlog](#viewing-the-backlog)
    - [Starting a Task](#starting-a-task)
    - [Editing Tasks](#editing-tasks)
    - [Removing Tasks](#removing-tasks)
11. [Agents](#agents)
    - [Orchestrator](#orchestrator)
    - [Finder](#finder)
    - [Analyst](#analyst)
    - [Researcher](#researcher)
    - [Architect](#architect)
    - [Planner](#planner)
    - [Coder](#coder)
    - [Editor](#editor)
    - [Fixer](#fixer)
    - [Refactorer](#refactorer)
    - [Reviewer](#reviewer)
    - [Tester](#tester)
    - [Debugger](#debugger)
    - [Security](#security)
    - [Documenter](#documenter)
    - [Commenter](#commenter)
    - [DevOps](#devops)
    - [Optimizer](#optimizer)
12. [Skills](#skills)
    - [TDD Workflow](#tdd-workflow)
    - [Security Review](#security-review)
    - [PRD Template](#prd-template)
    - [API Design](#api-design)
    - [Code Review Checklist](#code-review-checklist)
    - [Context Management](#context-management)
13. [Commands](#commands)
    - [Backlog Commands](#backlog-commands)
    - [Development Commands](#development-commands)
    - [Quality Commands](#quality-commands)
14. [Capability Selection](#capability-selection)
    - [Simple Bug with a Known Cause](#simple-bug-with-a-known-cause)
    - [Complex Feature](#complex-feature)
    - [Risk-Triggered Security Review](#risk-triggered-security-review)
    - [With the Core (Auditable Path)](#with-the-core-auditable-path)
15. [Best Practices](#best-practices)
16. [Token Optimization](#token-optimization)
17. [Troubleshooting](#troubleshooting)
18. [Practical Examples](#practical-examples)
19. [Contribution](#contribution)

---

## Introduction

Welcome to the **Juicer Kit Complete Guide**! This guide was created to help people of **all skill levels** use agents in OpenCode efficiently, securely, and productively.

Version 4.1.0 has two layers:

- a **Markdown kit** — 18 activity-oriented agents, 6 skills and 9 slash
  commands that you can use directly in OpenCode chat;
- an **executable orchestration core** — Python modules in `juicer/` driven by
  `bin/juicer`, which runs tasks in isolated git worktrees, executes
  deterministic checks, enforces gates and records evidence.

You can use the Markdown kit standalone, adopt the core for auditable execution, or combine both. The core is the owner of mission state, scope, evidence, gates and integration.

Whether you are:
- **Beginner** in AI and agents → This guide will teach you from scratch.
- **Intermediate** → Will optimize your workflow.
- **Advanced** → Will find patterns and practices to scale.

The goal is that by the end of this guide, you will be able to:
- Set up Juicer Kit in your project.
- Select the capabilities a task actually needs.
- Manage tasks with the backlog system and, when needed, import them into a mission.
- Understand the 4.1.0 orchestration core, its gates and its `.juicer/` state.
- Apply skills and commands to accelerate work.
- Follow the canonical gate order without treating any agent chain as mandatory.
- Avoid common mistakes and optimize token usage.

Let's go!

---

## What is Juicer Kit

**Juicer Kit** is a set of **activity-oriented capabilities** (Markdown agents), **skills**, and **commands** for OpenCode, plus an **orchestration core** for auditable execution, inspired by Mission Kit and optimized for workflows with:

- **Human autonomy** → You decide when and how to use each capability.
- **Security** → Risk-triggered reviews and audits for critical features.
- **Quality** → Capabilities selected per task, with deterministic checks and review before merge.
- **Reusability** → Structure that works in VS Code, Zed, and other editors.
- **Auditability** → Isolated worktrees, deterministic check results, linked evidence and explicit merge gates.

### Two layers, one workflow

| Layer | What it is | Use it when |
| --- | --- | --- |
| **Markdown kit** | `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/` and `backlog/` | You want to drive the agents interactively in OpenCode chat. |
| **Orchestration core** | `juicer/` + `bin/juicer`, state in `.juicer/` | You want the core to run tasks, enforce gates, record evidence and integrate explicitly. |

Both layers follow the same canonical order:

**implementation → deterministic checks → review → security (when applicable) → human approval (when applicable) → merge/integrate → post-merge checks → done.**

The Markdown kit's `@orchestrator` and the core use this order. Agents may advise; they do not waive core gates.

### Capability selection, not fixed personas

Agents in Juicer Kit are **activity-oriented capabilities**, not job titles.
Each one receives a task contract from the core or from you, works inside the
declared `scope.paths` and reports results as evidence. The model is chosen per
task/session, not baked into an agent's identity.

The `@orchestrator` (or the core `juicer`) reads the task and invokes **only the
capabilities it needs**:

- a simple, well-understood bug with a known cause may need only `@fixer`,
  followed by deterministic checks;
- a complex feature may need `@finder` to locate code, `@architect` to design,
  and `@coder` to implement — but each step is a deliberate selection, not a
  mandatory rung in a chain;
- authentication or user-data changes add `@security` because risk triggers it,
  not because every task must run every agent.

There is **no mandatory agent chain**. The only fixed sequence is the core's
gate order: implementation → deterministic checks → review → security (when
applicable) → human approval (when applicable) → merge/integrate →
post-merge checks → done.

The core can also invoke the existing `@reviewer` and `@security` through
`review-run`/`security-run` and record their structured evidence. Agents may
advise; they do not waive core gates.

---

## Who This Guide Is For

This guide is for:

- **Product Designers** who want to use AI to accelerate development.
- **Developers** who want to improve quality and security.
- **Product Managers** who want to manage tasks with backlog.
- **AI Beginners** who want to learn how to use agents.
- **Teams** who want to standardize workflows.

**Not required**:
- Being a senior developer.
- Prior experience with AI.
- Knowing how to program in specific languages.

**Useful to have**:
- Basic Git knowledge.
- Familiarity with terminal.
- Willingness to learn and test.

---

## Prerequisites

Before starting, you need:

### 1. OpenCode 2.x (V2)

Juicer Kit targets **OpenCode 2.x/V2**. The version measured in this environment is:

```bash
opencode --version
# opencode v2.2.7
```

**Installation**:

```bash
# macOS/Linux
curl -fsSL https://opencode.ai/install | bash

# Or upgrade a V1 install to the V2 line
opencode upgrade --major

# Windows
# Download installer at https://opencode.ai
```

The kit detects the binary through `OPENCODE_BIN`, then `PATH`, then
`~/.opencode/bin`, then the Zed registry. A V1 binary can still be detected for
diagnostics, but it is reported as `degraded`; **V1 compatibility is not
promised**.

Check what the core sees:

```bash
python3 bin/juicer discover
```

### 2. Python 3 (for the orchestration core)

The core uses only the Python standard library. Python 3.8+ is sufficient
(measured with Python 3.8.5). You only need Python if you use `bin/juicer`; the
Markdown kit works without it.

### 3. Git

The core creates a dedicated git worktree and branch per task, integrates with
an explicit `--no-ff` merge and keeps evidence tied to commits and tree hashes.
The project must be a git repository with at least one commit.

### 4. Code Editor

Juicer Kit works in:

- **VS Code** (recommended for beginners)
- **Zed** (lighter, via ACP)
- **Any editor** with integrated terminal

### 5. GitHub Account (optional)

For using Git submodules and contributing to the kit.

### 6. API Keys (optional)

OpenCode works with various providers:

- **OpenAI** (GPT-4, GPT-5)
- **Anthropic** (Claude)
- **Google** (Gemini)
- **OpenRouter** (170+ models)

Configure your keys in `~/.config/opencode/opencode.json`, or run `/connect` inside OpenCode.

> **Model quota matters for the core.** Each `juicer run`, `review-run` and
> `security-run` makes a real model call. During the 4.1.0 validation, the free
> provider hit HTTP 429 (usage limit) and the default provider returned HTTP 402
> (quota). Those are provider limits, not core failures, but they block live
> agent calls until quota is available.

---

## Installation

There are 4 ways to install Juicer Kit in your project. Options 1, 2 and 4
install the Markdown kit; Option 3 sets up the orchestration core. You can
combine them (for example, copy `.opencode/` and use the core from a clone).

### Option 1: Manual Copy

**Ideal for**: Beginners, single projects, quick tests.

**Steps**:

1. **Download Juicer Kit**:

   ```bash
   # Clone the repository
   git clone https://github.com/diogocvc/juicer-kit.git
   ```

2. **Copy folders to project**:

   ```bash
   # Enter project
   cd my-project

   # Copy folders
   cp -r ../juicer-kit/.opencode ./
   cp -r ../juicer-kit/backlog ./
   ```

   Agents, commands and skills all live inside `.opencode/` — these two commands are enough.

3. **Verify structure**:

   ```bash
   ls -la
   # Should show: .opencode/, backlog/
   ```

**Advantages**:
- Simple and fast.
- Works in any project.
- Easy to test.

**Disadvantages**:
- Doesn't update automatically.
- Duplicates code in multiple projects.

---

### Option 2: Git Submodule

**Ideal for**: Multiple projects, automatic updates, teams.

**Steps**:

1. **Add as submodule**:

   ```bash
   # Enter project
   cd my-project

   # Add submodule
   git submodule add https://github.com/diogocvc/juicer-kit.git juicer-kit
   ```

2. **Link the kit into the project**:

   ```bash
   ln -s juicer-kit/.opencode ./.opencode
   cp -r juicer-kit/backlog ./
   ```

   `backlog/` is copied because each project keeps its own tasks.

3. **Commit**:

   ```bash
   git add .
   git commit -m "Add Juicer Kit as submodule"
   ```

**To update in the future**:

```bash
git submodule update --remote
```

The symlink already points to the updated content — restart OpenCode after updating.

**Advantages**:
- Automatic updates.
- Single repository to maintain.
- Easy to sync across multiple projects.

**Disadvantages**:
- Requires Git knowledge.
- Can conflict if you modify files.

---

### Option 3: Orchestration Core

**Ideal for**: Auditable execution, deterministic checks, explicit merge gates.

**Requirements**: Python 3.8+, git, and a git repository with at least one
commit. The core uses only the Python standard library.

**Steps**:

1. **Clone the kit** (the core is executed from the clone):

   ```bash
   git clone https://github.com/diogocvc/juicer-kit.git ~/juicer-kit
   ```

2. **Initialize the core in your project**:

   ```bash
   cd my-project
   python3 ~/juicer-kit/bin/juicer --root . init
   ```

   `init` creates `.juicer/` (mission, tasks, executions, evidence, events,
   worktrees) and writes a scoped `.juicer/.gitignore` for state internals.

3. **Check the harness**:

   ```bash
   python3 ~/juicer-kit/bin/juicer --root . discover
   ```

   Expected: `opencode v2.2.7`, `v2: true`, `status: supported`. Override the
   binary with `export OPENCODE_BIN=/path/to/opencode` if auto-detection fails.

4. **Follow the core workflow** (see
   [Orchestration Core (4.1.0)](#orchestration-core-410)):

   ```bash
   python3 ~/juicer-kit/bin/juicer --root . mission --title "..." --objective "..."
   python3 ~/juicer-kit/bin/juicer --root . import-backlog
   python3 ~/juicer-kit/bin/juicer --root . run TASK-001
   python3 ~/juicer-kit/bin/juicer --root . review-run TASK-001
   python3 ~/juicer-kit/bin/juicer --root . integrate TASK-001
   ```

**Advantages**:
- Isolated worktree/branch per task.
- Deterministic checks and honest `PASS / FAIL / BLOCKED / NOT RUN` statuses.
- Evidence tied to commit/tree, explicit human approval and post-merge checks.
- Recoverable with `checkpoint`/`resume`.

**Disadvantages**:
- Requires Python and git.
- Each `run`/`review-run`/`security-run` makes a real model call (provider
  quota/timeout applies).
- Local coordination only; not a distributed scheduler.

**Note**: if you prefer to keep the core inside the project, copy `juicer/` and
`bin/` into the repository and run `python3 bin/juicer init`. Do not copy
`.juicer/` between projects; it is per-project operational state.

---

### Option 4: Symlink

**Ideal for**: Local development, testing, contributions.

**Steps**:

1. **Clone Juicer Kit**:

   ```bash
   git clone https://github.com/diogocvc/juicer-kit.git ~/juicer-kit
   ```

2. **Create symlinks in project**:

   ```bash
   cd my-project

   ln -s ~/juicer-kit/.opencode ./.opencode
   ln -s ~/juicer-kit/backlog ./backlog
   ```

**Advantages**:
- Automatic update (point to latest version).
- No file duplication.
- Easy to test changes.

**Disadvantages**:
- Only works locally.
- Doesn't work in CI/CD without adjustments.

---

## Kit Structure

Juicer Kit has the following structure:

```
juicer-kit/
├── README.md                 # Main documentation
├── AGENTS.md                 # Minimal project instructions for OpenCode
├── LICENSE
├── VERSION                   # 4.1.0
├── STATUS.md                 # Measured capabilities and limitations
├── bin/
│   └── juicer                # CLI entrypoint (python3)
├── juicer/                   # Orchestration core (Python stdlib only)
│   ├── cli.py                # Command-line interface
│   ├── model.py              # Mission/Task/Execution contracts
│   ├── state.py              # Atomic writes, flock, revision fence, events
│   ├── graph.py              # Dependencies and eligibility
│   ├── scheduler.py          # Automatic release, --jobs parallelism
│   ├── checks.py             # PASS / FAIL / BLOCKED / NOT RUN
│   ├── gates.py              # Technical gate (NOT RUN never passes)
│   ├── gitops.py             # Worktrees, explicit merge, conflict abort
│   ├── scope.py              # Scope and protected-path enforcement
│   ├── evidence.py           # Structured review/security evidence
│   ├── approval.py           # Human approval linked to commit/tree
│   ├── backlog.py            # One-way backlog import
│   ├── orchestrator.py       # Mission → run → integrate → resume flow
│   └── harness/
│       ├── contract.py       # discover/run request-result contract
│       └── opencode.py       # OpenCode V2 adapter (run --format json --standalone)
├── tests/                    # 345 default pytest tests + 2 opt-in V2 smoke checks
├── backlog/
│   ├── backlog.md            # Pending tasks
│   ├── in-progress.md        # Tasks in progress
│   └── done/                 # Completed tasks
├── docs/
│   ├── GUIDE.md              # This guide
│   ├── HARNESS_CONTRACT.md   # Internal discover/run contract
│   └── PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md  # Approved 4.0 plan
└── .opencode/
    ├── agents/               # 18 activity capabilities
    │   ├── orchestrator.md       # Coordination
    │   ├── finder.md             # Codebase scouting
    │   ├── analyst.md            # Analysis
    │   ├── researcher.md         # External research
    │   ├── architect.md          # Design
    │   ├── planner.md            # Decomposition
    │   ├── coder.md              # Implementation
    │   ├── editor.md             # Compatibility change
    │   ├── fixer.md              # Bug fix
    │   ├── refactorer.md         # Refactoring
    │   ├── reviewer.md           # Review
    │   ├── tester.md             # Testing
    │   ├── debugger.md           # Diagnosis
    │   ├── security.md           # Security audit
    │   ├── documenter.md         # Technical writing
    │   ├── commenter.md          # Code commentary
    │   ├── devops.md             # Infrastructure
    │   └── optimizer.md          # Performance
    ├── skills/               # 6 reusable skills
    │   ├── tdd-workflow/SKILL.md
    │   ├── security-review/SKILL.md
    │   ├── prd-template/SKILL.md
    │   ├── api-design/SKILL.md
    │   ├── code-review-checklist/SKILL.md
    │   └── context-management/SKILL.md
    └── commands/             # 9 slash commands
        ├── add-backlog.md
        ├── start.md
        ├── edit-backlog.md
        ├── remove-backlog.md
        ├── plan.md
        ├── review.md
        ├── security-audit.md
        ├── test.md
        └── document.md
```

After `juicer init`, the target project also contains runtime state:

```
my-project/
└── .juicer/
    ├── .gitignore            # Scoped ignores for state internals
    ├── config.json           # Core configuration (max_jobs, protected paths, …)
    ├── mission.json          # Mission, acceptance criteria and gaps
    ├── tasks/                # One JSON file per task
    ├── executions/           # One JSON file per execution attempt
    ├── checks/               # Deterministic check logs and results
    ├── evidence/             # Captured output, diffs, review/security evidence
    ├── approvals/            # Human approval records linked to commit/tree
    ├── checkpoints/          # Recovery checkpoints
    ├── imports/              # One-way backlog import journal
    ├── worktrees/            # Isolated git worktree per task
    └── events.jsonl          # Append-only event log
```

`.juicer/` is **operational state**, not planning. It is created by the core and
is canonical after a validated backlog import. Do not edit it by hand; use the
CLI so locks, revisions and evidence stay consistent.

### What each part does:

- **`.opencode/agents/`** → Activity capabilities selected per task.
- **`backlog/`** → Planning task board (Markdown).
- **`.opencode/skills/`** → Reusable playbooks (e.g., TDD, security review).
- **`.opencode/commands/`** → Slash shortcuts (e.g., `/add-backlog`, `/plan`).
- **`juicer/` + `bin/juicer`** → Orchestration core and CLI.
- **`.juicer/`** → Mission, tasks, executions, evidence and events created at runtime.
- **`tests/`** → Core test suite, including the deterministic V2 E2E flow.
- **`AGENTS.md`** → Your project's own instructions for OpenCode (optional).
- **`docs/GUIDE.md`** → This guide.
- **`docs/HARNESS_CONTRACT.md`** → Internal `discover`/`run` contract.
- **`docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md`** → Approved plan, gates and phases.
- **`STATUS.md`** → Measured capabilities versus planned gaps.

---

## Initial Setup

After installing the kit, do these configurations:

### 1. Verify Agents Are Loaded

In OpenCode, type:

```
@
```

Should show a list with all agents:
- `@orchestrator`
- `@finder`
- `@analyst`
- `@architect`
- `@planner`
- `@coder`
- `@reviewer`
- `@tester`
- `@security`
- etc.

If not showing, check:
- Is `.opencode/agents/` folder in the right place?
- Was OpenCode restarted after copying files?

### 2. Configure AI Model

Juicer Kit works with various models. To configure:

**Option A: Global (recommended)**

Edit `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4.5"
}
```

**Option B: Per Session**

In OpenCode chat:

```
/models
```

This opens the model selector (alias `/mo`).

**Option C: Per Task/Session**

Juicer Kit 4.1.0 does not pin a model to an agent persona. Choose the model
with the task contract or session, using `/models` (below). A capability such
as `@commenter` or `@documenter` can run on whichever model the task selects;
if an agent frontmatter still contains a `model` field, treat it as a local
override, not as part of the kit philosophy.

```md
---
description: "..."
# no model: the task/session decides
---
```

### 3. Customize `backlog/backlog.md`

The 4.1.0 repository ships with an empty pending backlog plus a task template. You
can:

- **Add your own tasks** with `/add-backlog` or by editing the Markdown.
- **Keep the template** as a reference.
- **Import pending tasks into a mission** later with `juicer import-backlog`
  (one-way, once per mission).

Backlog entries are planning input. Once imported, `.juicer/` becomes the
canonical operational state; later backlog edits do not overwrite an in-progress
mission.

### 4. Test with a Simple Command

In OpenCode chat:

```
@finder Map the project structure.
```

If the agent responds with project structure, everything is working!

### 5. Initialize the Core (optional)

If you want auditable execution, initialize `.juicer/` from your project root:

```bash
python3 /path/to/juicer-kit/bin/juicer --root . init
python3 /path/to/juicer-kit/bin/juicer --root . discover
```

Then define a mission and import the backlog:

```bash
python3 /path/to/juicer-kit/bin/juicer --root . mission \
  --title "My first mission" \
  --objective "Deliver one small, verifiable change" \
  --criterion "tests pass"

python3 /path/to/juicer-kit/bin/juicer --root . import-backlog
python3 /path/to/juicer-kit/bin/juicer --root . status
```

`status` shows the mission state, eligible tasks and the next action. See
[Orchestration Core (4.1.0)](#orchestration-core-410) for the full flow.

---

## Getting Started

Let's do a complete flow from scratch.

### Starting OpenCode

**In VS Code**:

```bash
opencode serve
```

Or use the OpenCode extension (if available).

**In Zed**:

1. Start OpenCode: `opencode serve`
2. Connect Zed via ACP (configure endpoint in Zed settings).

### Testing Agents

#### Example 1: Map Project

```
@finder Map the project structure and find key files.
```

**Expected Response**:

```
## Project Structure
- /src — Main application code
- /tests — Test suite
- /docs — Documentation

## Key Files
- src/index.ts — Entry point
- src/api/auth.ts — Authentication logic

## Patterns
- TypeScript with strict mode
- Feature-based folder organization
```

#### Example 2: Analyze Code

```
@analyst Analyze the authentication flow in src/auth/.
```

**Expected Response**:

```
## Code Overview
JWT-based authentication with refresh tokens.

## Dependencies
- Internal: src/utils/crypto.ts
- External: bcrypt, jsonwebtoken

## Risks
- Refresh tokens stored in localStorage (security risk)
- No rate limiting on login endpoint

## Recommendations
- Move refresh tokens to httpOnly cookies
- Add rate limiting
```

#### Example 3: Add Task to Backlog

```
/add-backlog Create user profile API with CRUD operations
```

**Expected Response**:

```
Task Added to Backlog

### Task: [TASK-003] Create user profile API

**Description**: Create user profile API with CRUD operations
**Priority**: P2-Medium
**Dependencies**: None
**Acceptance Criteria**:
- [ ] GET /api/users/:id returns profile
- [ ] PUT /api/users/:id updates profile
- [ ] DELETE /api/users/:id deletes account
**Estimated Effort**: M

**Next Steps**:
- Type `/start TASK-003` to start now
- Type `/edit-backlog TASK-003` to modify
- Or continue conversation
```

---

## Orchestration Core (4.1.0)

The core is optional. Use it when you want the machine, not the chat, to enforce
what "done" means: isolated execution, deterministic checks, linked evidence,
explicit approval and an auditable merge.

### What the Core Does

1. **Defines a mission** with objective, scope, constraints, acceptance
   criteria and open gaps. Gaps keep the mission `waiting_human` until resolved.
2. **Registers tasks** from JSON (`decompose`) or from the backlog Markdown
   (`import-backlog`, one-way and once per mission).
3. **Runs each task in its own git worktree and branch**
   (`juicer/<TASK-ID>`; retries use `juicer/<TASK-ID>-attempt-<n>`), never on
   your checkout. The OpenCode subprocess runs with the worktree as both `cwd`
   and `PWD`, because V2 resolves the project from `PWD`.
4. **Captures evidence**: session id, exit code, raw output, diff, commit, tree
   hash, check logs and the check results. Agent prose is never evidence.
5. **Evaluates the declared technical gates** in deterministic order:
   `verification` → `review` → `security` → `approval`. `PASS`, `FAIL`,
   `BLOCKED` and `NOT RUN` are distinct; **`NOT RUN` never passes**.
6. **Requires explicit integration** (`juicer integrate`) with a `--no-ff`
   merge, acceptance-criteria evaluation and post-merge checks on the merged
   commit. Only then does the task become `done`.
7. **Supports recovery**: `retry`, `checkpoint` and `resume` reconcile
   interrupted executions without silently discarding work or evidence.

The core does **not** add review or security gates implicitly. Declare them in
the task's `approval_policy.required_gates`. High risk always requires recorded
human approval; security is still a separate gate only when declared.

### State and Ownership

Two different sources of truth coexist:

| Path | Owner | Meaning |
| --- | --- | --- |
| `backlog/*.md` | You / the Markdown kit | Planning board. Pending, in-progress and done tasks written as Markdown. |
| `.juicer/` | The core | Operational state after a validated mission import: mission, tasks, executions, evidence, checks and events. |

After `juicer import-backlog`, `.juicer/` is canonical. There is **no
bidirectional sync**: later backlog edits do not overwrite an in-progress
mission. Import is allowed once into an empty mission and refuses to overwrite
existing tasks; re-importing unchanged content is reported as `unchanged`.

Task status lifecycle:

```
ready → in_progress → completed → done
             │            │
             ├→ failed    └→ blocked   (post-merge failure)
             └→ blocked

failed / blocked → ready   (retry)
```

- `completed` means **pre-merge work is finished**; it is not `done`.
- `done` requires a technical gate PASS, an explicit integration and a
  post-merge check PASS.
- A post-merge failure leaves the task `blocked`, never `completed`/`done`.

### Quick Start

```bash
# 1. Initialize state (from the project root)
python3 /path/to/juicer-kit/bin/juicer --root . init

# 2. Define the mission
python3 /path/to/juicer-kit/bin/juicer --root . mission \
  --title "Add rate limiting" \
  --objective "429 responses on public endpoints" \
  --criterion "limiter active + tests" \
  --constraint "no new dependencies"

# 3. Register tasks (or use `import-backlog`)
cat > tasks.json <<'EOF'
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Token-bucket limiter",
      "description": "Implement the limiter in src/limiter.py with tests.",
      "depends_on": [],
      "agent": "coder",
      "priority": "P1",
      "acceptance_criteria": [
        {"id": "AC-001", "description": "tests pass", "verification": "check:tests", "required": true}
      ],
      "approval_policy": {
        "human_approval_required": false,
        "required_gates": ["verification", "review"]
      },
      "checks": [
        {"id": "tests", "command": ["python3", "-m", "pytest", "-q", "tests/"], "required": true}
      ],
      "scope": {"paths": ["src/limiter.py", "tests/"], "constraints": []}
    }
  ]
}
EOF

python3 /path/to/juicer-kit/bin/juicer --root . decompose tasks.json

# 4. Inspect and execute
python3 /path/to/juicer-kit/bin/juicer --root . status
python3 /path/to/juicer-kit/bin/juicer --root . run TASK-001
# or run all eligible tasks: ... run --jobs 4

# 5. Produce evidence for declared gates
python3 /path/to/juicer-kit/bin/juicer --root . review-run TASK-001
# if security is declared: ... security-run TASK-001

# 6. Record human approval when required
python3 /path/to/juicer-kit/bin/juicer --root . approve TASK-001 \
  --approver "your-name" --reason "reviewed the limiter behavior"

# 7. Explicit merge + post-merge checks
python3 /path/to/juicer-kit/bin/juicer --root . integrate TASK-001 --approve

# 8. Audit and recover if needed
python3 /path/to/juicer-kit/bin/juicer --root . status
python3 /path/to/juicer-kit/bin/juicer --root . events
python3 /path/to/juicer-kit/bin/juicer --root . resume
```

**Importing the Markdown backlog instead of writing JSON**:

```bash
python3 /path/to/juicer-kit/bin/juicer --root . import-backlog
```

The importer validates the Markdown schema, IDs, priorities, dependencies,
acceptance criteria and scope. Invalid entries fail the import; they are not
silently skipped.

### CLI Commands

| Command | Purpose |
| --- | --- |
| `juicer init` | Create `.juicer/` state in the current repo |
| `juicer mission --title --objective --criterion --constraint` | Define the mission |
| `juicer gap "question" --answer "..."` | Resolve a mission gap |
| `juicer inspect` | Snapshot of project, dependencies and open tasks |
| `juicer decompose tasks.json` | Validate and register tasks (stable IDs, dependencies) |
| `juicer import-backlog [--file PATH]` | Validate backlog Markdown and import pending tasks once into an empty mission |
| `juicer status` | Mission state, eligibility and next action |
| `juicer run [TASK-ID] [--jobs N]` | Execute eligible tasks (serial by default) |
| `juicer retry TASK-ID` | Return a failed or blocked task to `ready` (new attempt, history preserved) |
| `juicer review TASK-ID --commit --tree-hash` | Record a structured review artifact manually |
| `juicer security TASK-ID --commit --tree-hash` | Record a structured security artifact manually |
| `juicer review-run TASK-ID` | Trigger the existing `@reviewer`, require structured JSON and record evidence |
| `juicer security-run TASK-ID` | Trigger the existing `@security`, require structured JSON and record evidence |
| `juicer approve TASK-ID --approver NAME [--reason] [--note]` | Record human approval linked to the task commit/tree |
| `juicer integrate TASK-ID [--approve]` | Gates + criteria + explicit merge + post-merge checks |
| `juicer checkpoint` | Force a consistency checkpoint |
| `juicer resume` | Reconcile interrupted tasks after a crash/restart |
| `juicer events` | Tail the append-only JSONL event log |
| `juicer discover` | Show the detected OpenCode binary and capabilities |

Run `juicer --help` or `juicer <command> --help` for the exact flags. All
commands accept `--root PATH` (default: current directory).

### Gates and Human Approval

The core evaluates exactly the gates declared in
`approval_policy.required_gates`:

| Gate | Evidence | Missing evidence | Stale evidence |
| --- | --- | --- | --- |
| `verification` | Required deterministic check results for the task commit | `NOT RUN` | `NOT RUN` |
| `review` | Structured `@reviewer` artifact linked to commit/tree | `BLOCKED` | `NOT RUN` |
| `security` | Structured `@security` artifact linked to commit/tree | `BLOCKED` | `NOT RUN` |
| `approval` | `juicer approve` record for the exact commit/tree | `BLOCKED` | `NOT RUN` |

Important rules:

- **`NOT RUN` never passes.** A check that could not be obtained is not a pass.
- **Review is a gate only when declared.** When declared, critical findings in
  a `FAIL` verdict block the merge until fixed.
- **Security is not added implicitly**, including for high-risk tasks. Declare
  `security` in `required_gates` when the risk applies.
- **High risk always requires human approval**, even if the policy does not
  list `approval` explicitly.
- **Approval is never anonymous or inferred.** `integrate --approve` expresses
  merge intent only; it is refused without a matching `juicer approve` record.
  A new commit invalidates the approval.
- **Approval never replaces tests or review.** It is an additional gate, not a
  waiver.
- **OpenCode V2 permissions are an additional execution barrier**, not a
  substitute for core scope, evidence or approval.

`review-run`/`security-run` refuse to review the wrong tree: the task must be
`completed`, its worktree must still exist, be free of tracked changes and be at
the task commit. Otherwise the command returns `BLOCKED` instead of producing
evidence for a different state.

### Resume and Recovery

The core is designed to fail closed and remain recoverable:

- **Interrupted task**: `juicer resume` reconciles the execution. A missing
  worktree yields `failed`; an interrupted worktree yields `blocked`, with the
  next step recorded.
- **Retry**: `juicer retry TASK-ID` starts a new attempt with a new branch and
  worktree. The previous attempt's HEAD, tree, diff, branch tip and durable ref
  are preserved under `.juicer/evidence/`.
- **Merge conflict**: the merge is aborted; no partial merge is left behind.
  The task is `blocked` with the commit/branch recorded for intervention.
- **Post-merge failure**: the task is `blocked`, never `completed`/`done`.
- **Checkpoint**: `juicer checkpoint` records status, next step, blocked reason,
  execution/branch/commit/tree and merged state per task.
- **Event log**: `.juicer/events.jsonl` is append-only; `juicer events` tails it.

### Measured Capabilities and Limitations

These are the claims the 4.1.0 release actually measured. See
[`STATUS.md`](../STATUS.md) for the complete matrix.

**Measured** (OpenCode `v2.2.7`):

- `discover` reports `v2=true`, `status=supported`.
- `run --format json --agent <name> --standalone` works; events are NDJSON with
  `sessionID` and `part`.
- `--dir` is **absent** in V2; the workspace is anchored by `cwd` **and**
  `PWD`. V2 resolves the project from `PWD`, so the adapter pins both.
- A real `run` + deterministic checks + `integrate` + post-merge flow completed
  with a free model, delivering the file in the worktree and reaching `done`
  with PRE_MERGE PASS and POST_MERGE PASS.
- The deterministic E2E in `tests/test_e2e_v2.py` drives the real core and the
  real V2 adapter for the full mission → import → run → review → security →
  approval → merge → post-merge flow and its negative paths.

**Partial / not measured**:

- Live `review-run`/`security-run` after the `PWD` fix were blocked by provider
  quota/limits (HTTP 402/429). The full path is covered by the deterministic
  E2E; do not treat a blocked provider call as a PASS.
- Real session resume via `--session`/`--continue` was not exercised.
- A restrictive headless V2 permission policy (`allow`/`ask`/`deny`) was not
  measured. `external_directory` is allowed by default in V2; restrict it in
  `opencode.json` if the agent must not read/write outside the worktree.
- Parallel `--jobs 2` was validated on the historical V1 smoke, not revalidated
  with V2 `--standalone`.

**Known constraints**:

- **V1 is not a target.** A V1 binary is detected as `degraded`; compatibility
  is not promised.
- **Local only.** Locks and revision fences coordinate multiple processes on
  one machine; there is no distributed coordination.
- **Serial by default.** `max_jobs=1`; pass `--jobs N` explicitly to parallelize.
- **Worktrees stay inside the project.** V2 discovers `.opencode/` by walking
  up from `PWD`; keeping worktrees in `.juicer/worktrees/<task>` keeps the
  project config visible. Moving them outside requires `.opencode/` in the
  worktree or global config, otherwise OpenCode fails with `Agent not found`.
- **Config/agents are not protected by default.** `.opencode/`,
  `opencode.json(c)` and `AGENTS.md` are not in `DEFAULT_PROTECTED_PATHS`. Keep
  them out of task scope or add them to `scope.protected_paths`.
- **Ignored files are not in the scope diff.** A gitignored file written by the
  agent will not appear in the diff used for scope enforcement; use the
  permission/sandbox barrier as well.
- **Preserved evidence may contain secrets.** `preserved-*.diff` captures the
  worktree content; treat `.juicer/` as sensitive and restrict access.
- **Each agent call costs a model call.** `run`, `review-run` and
  `security-run` depend on provider quota, latency and timeout.

---

## Backlog System

The backlog system is one of the most powerful features of Juicer Kit.

### What is the Backlog

The **backlog** is a list of pending, in-progress, and completed tasks. It works like a **Kanban board** in Markdown.

**Files**:

- `backlog/backlog.md` → Pending tasks.
- `backlog/in-progress.md` → Tasks being done now.
- `backlog/done/` → Completed tasks (one per file).

The backlog is **planning input**. It is not the core's operational state. If
you use the orchestration core, `juicer import-backlog` validates the Markdown
and copies pending tasks into `.juicer/` **once**; from then on `.juicer/` is
canonical and backlog edits do not overwrite an in-progress mission.

The examples below use illustrative task IDs (TASK-001, TASK-003, …) and a
generic JWT feature. They show the Markdown shape, not the content of the 4.1.0
repository, whose pending backlog ships empty.

### Adding Tasks

#### Method 1: `/add-backlog` Command

```
/add-backlog Create user authentication with JWT

**Priority**: P1-High
**Dependencies**: None
**Acceptance Criteria**:
- User can register with email/password
- User can login and receive JWT tokens
- Refresh token flow works correctly
```

**Response**:

```
Task Added to Backlog

### Task: [TASK-003] Create user authentication with JWT

**Priority**: P1-High
**Dependencies**: None
**Acceptance Criteria**:
- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Refresh token flow works correctly
**Estimated Effort**: L

**Next Steps**:
- Type `/start TASK-003` to start now
- Type `/edit-backlog TASK-003` to modify
```

#### Method 2: `/add-backlog` Command

```
/add-backlog Create password reset flow with email
```

#### Method 3: Editing `backlog.md` Manually

Open `backlog/backlog.md` and add:

```md
### Task: [TASK-004] Create password reset flow

**Description**: Implement password reset via email with token.

**Priority**: P1-High

**Dependencies**: TASK-003

**Acceptance Criteria**:
- [ ] User can request password reset
- [ ] Email with reset token is sent
- [ ] Token expires after 1 hour
- [ ] User can set new password with valid token

**Estimated Effort**: M
```

### Viewing the Backlog

Read `backlog/backlog.md` (pending tasks) and `backlog/in-progress.md` (tasks in progress).

**Response**:

```
## Backlog (Pending Tasks)

| ID | Title | Priority | Dependencies | Effort |
|----|-------|----------|--------------|--------|
| TASK-001 | JWT Authentication | P1 | None | L |
| TASK-002 | User Profile API | P2 | TASK-001 | M |
| TASK-003 | Password Reset | P1 | TASK-001 | M |

**Actions**:
- `/start TASK-001` — Start a task
- `/edit-backlog TASK-001` — Edit task
- `/remove-backlog TASK-001` — Remove task
```

### Starting a Task

```
/start TASK-001
```

**Response**:

```
Starting Task: TASK-001 JWT Authentication

**Priority**: P1-High
**Dependencies**: None
**Assigned To**: [@orchestrator]

**Selected capabilities**:
- @finder → Locate auth-related files and existing patterns
- @architect → Design the JWT auth system
- @coder → Implement the approved design
- @tester → Produce deterministic check evidence
- @reviewer → Review after deterministic checks, before merge
- @security → Audit because authentication is a risk trigger
- @documenter → Document only if the task changes public behavior

This is a selection, not a mandatory chain. The core may drop capabilities
that the task does not need; `@planner` is added only when decomposition is
useful, and a small fix may need only `@fixer` plus checks.

**Next**: @orchestrator will confirm the selection, or `juicer` will run the
task with its declared gates.
```

The orchestrator:
1. Moves task to `in-progress.md`.
2. Selects the capabilities the task needs (no fixed pipeline).
3. Updates status as it progresses and hands gate enforcement to the core.

### Editing Tasks

```
/edit-backlog TASK-001
```

**Response**:

```
Editing Task: TASK-001 JWT Authentication

**Current Details**:
- Description: Create user authentication with JWT
- Priority: P1-High
- Dependencies: None
- Acceptance Criteria: [3 criteria]
- Effort: L

**What would you like to edit?**
- Type the field name and new value
- Or type 'cancel' to abort
```

### Removing Tasks

```
/remove-backlog TASK-001
```

**Response**:

```
Remove Task: TASK-001 JWT Authentication

**Task Details**:
- Description: Create user authentication with JWT
- Priority: P1-High
- Status: Pending

**Are you sure you want to remove this task?** (yes/no)
```

### Importing the Backlog into the Core

If you use the orchestration core, the backlog Markdown can seed a mission:

```bash
python3 /path/to/juicer-kit/bin/juicer --root . mission \
  --title "My mission" --objective "Deliver the pending backlog"

python3 /path/to/juicer-kit/bin/juicer --root . import-backlog
python3 /path/to/juicer-kit/bin/juicer --root . status
```

Rules enforced by the importer:

- one import into an **empty** mission; it refuses to overwrite existing tasks;
- schema, ID, priority, dependency, acceptance-criteria and scope validation;
- unknown `required_gates` are rejected;
- the Markdown file is not modified (one-way import);
- re-importing unchanged content is reported as `unchanged`.

After import, track execution and merge state with `.juicer/`, not by editing
`backlog/in-progress.md`. Move the finished task to `backlog/done/` only after
the core reaches `done` (technical gate PASS, explicit integration and
post-merge PASS).

---

## Agents

Each agent is an **activity-oriented capability**, not a job title. The model
is chosen per task/session, and you invoke a capability with `@agent-name` only
when the task needs it. There is no mandatory chain across the agents below.

### Orchestrator

**Capability**: Coordination. Reads the task, selects only the capabilities it
needs and delegates; it never replaces the core's scope or gates.

**When to use**:
- Complex sessions with multiple steps.
- When you want help choosing capabilities, not a fixed pipeline.

**Example**:

```
@orchestrator Start working on the backlog.
```

**What it does**:
1. Reads the task contract and backlog.
2. Selects only the capabilities the task needs.
3. Delegates to those capabilities inside `scope.paths`.
4. Updates status as it progresses.
5. Leaves gate decisions to the core.

**Core note**: `@orchestrator` coordinates the Markdown workflow. It does not
replace the core. For auditable execution, use `juicer run` + the declared
gates; the core, not the agent's prose, decides whether a task may merge.

---

### Finder

**Capability**: Codebase scouting. Locates files, patterns and structure so the
next capability has context.

**When to use**:
- When you need to locate code or understand project structure.
- Before analysis or implementation on an unfamiliar area.

**Example**:

```
@finder Map the project structure and find auth-related files.
```

**Typical Response**:

```
## Project Structure
- /src — Main application code
- /tests — Test suite

## Key Files
- src/index.ts — Entry point
- src/api/auth.ts — Authentication logic

## Patterns
- TypeScript with strict mode
- Feature-based folder organization
```

---

### Analyst

**Capability**: Deep code analysis. Maps dependencies, data flow, coupling and
risks with evidence.

**When to use**:
- When dependencies, data flow or risk must be understood.
- Before designing or changing a non-trivial area.

**Example**:

```
@analyst Analyze the authentication flow in src/auth/.
```

**Typical Response**:

```
## Code Overview
JWT-based authentication with refresh tokens.

## Dependencies
- Internal: src/utils/crypto.ts
- External: bcrypt, jsonwebtoken

## Risks
- Refresh tokens stored in localStorage
- No rate limiting on login endpoint

## Recommendations
- Move refresh tokens to httpOnly cookies
- Add rate limiting
```

---

### Researcher

**Capability**: External research. Finds and evaluates authoritative sources
with citations and stated confidence.

**When to use**:
- When you need knowledge outside the code.
- To integrate with new APIs.
- To follow compliance standards (OWASP, GDPR).

**Example**:

```
@researcher Find best practices for JWT token storage and refresh.
```

**Typical Response**:

```
## Sources
- [OWASP JWT Cheat Sheet](URL)
- [RFC 7519](URL)

## Key Findings
- Refresh tokens should be stored in httpOnly cookies, not localStorage.
- Access tokens should have short expiration (15-30 minutes).
- Implement token rotation for refresh tokens.

## Recommendations
- Use httpOnly + Secure + SameSite cookies for refresh tokens.
- Implement token binding to prevent theft.
```

---

### Architect

**Capability**: Design. Defines components, interfaces, integrations and
architectural decisions; never edits code.

**When to use**:
- When interfaces, components or trade-offs need a design.
- Before implementing a feature that spans modules.

**Example**:

```
@architect Design a JWT-based authentication system with refresh tokens.
```

**Typical Response**:

```
## Architecture Overview
JWT authentication with access and refresh tokens.

## Components
- **AuthService**: Handles login, register, token generation
- **TokenService**: Manages token creation, validation, refresh
- **AuthMiddleware**: Protects routes, validates tokens

## Interfaces
- **POST /api/auth/register**: Register new user
- **POST /api/auth/login**: Login and receive tokens
- **POST /api/auth/refresh**: Refresh access token

## Data Models
- **User**: id, email, passwordHash, createdAt
- **Token**: id, userId, refreshToken, expiresAt

## Security Considerations
- Passwords hashed with bcrypt (cost 12)
- Refresh tokens in httpOnly cookies
- Rate limiting on auth endpoints
```

---

### Planner

**Capability**: Task decomposition. Turns a design into atomic tasks with
dependencies, acceptance criteria and scope.

**When to use**:
- When a design needs to become atomic, checkable tasks.
- Before parallel or multi-step implementation.

**Example**:

```
@planner Break down the JWT authentication system into implementable tasks.
```

**Typical Response**:

```
## Task List

### Task 1: Create User Model
- **Description**: Create User model with bcrypt password hashing
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] User model with email, passwordHash fields
  - [ ] Password hashed with bcrypt
  - [ ] Email validation
- **Complexity**: S
- **Files**: src/models/User.ts

### Task 2: Create AuthService
- **Description**: Implement register and login methods
- **Dependencies**: Task 1
- **Acceptance Criteria**:
  - [ ] Register method creates user
  - [ ] Login method validates credentials
  - [ ] Returns JWT tokens
- **Complexity**: M
- **Files**: src/services/AuthService.ts

### Task 3: Create TokenService
- **Description**: Implement JWT token generation and validation
- **Dependencies**: Task 1
- **Acceptance Criteria**:
  - [ ] Generate access token (15 min)
  - [ ] Generate refresh token (7 days)
  - [ ] Validate tokens
- **Complexity**: M
- **Files**: src/services/TokenService.ts

## Critical Path
Task 1 → Task 2 → Task 3
```

---

### Coder

**Capability**: Implementation. Creates new code from an explicit task
contract, inside `scope.paths`.

**When to use**:
- Implement well-defined tasks.
- Create files, functions, classes, components.

**Example**:

```
@coder Implement Task 1: Create User model with bcrypt password hashing.
```

**Typical Response**:

```
## Changes Made
- Created: `src/models/User.ts`

## Implementation
- User model with email, passwordHash fields
- Password hashed with bcrypt (cost 12)
- Email validation with regex
- Timestamps (createdAt, updatedAt)

## Tests Added
- `tests/models/User.test.ts`
  - should create user with valid email
  - should hash password
  - should reject invalid email

## Verification
- [x] Lint passed
- [x] Type-check passed
- [x] Tests passed

## Notes
- Used bcrypt for password hashing
- Email validation regex from validator.js
```

---

### Editor

**Capability**: Compatibility-focused change. Modifies existing code without
breaking its public contract.

**When to use**:
- Change existing code.
- Add features to existing code.

**Example**:

```
@editor Add rate limiting to the login endpoint in src/api/auth.ts.
```

**Typical Response**:

```
## Files Modified
- `src/api/auth.ts`

## Changes
- Added rate limiting with express-rate-limit
- 5 attempts per 15 minutes per IP
- Returns 429 Too Many Requests when exceeded

## Tests Updated
- `tests/api/auth.test.ts`
  - should allow 5 login attempts
  - should return 429 on 6th attempt

## Verification
- [x] Lint passed
- [x] Type-check passed
- [x] Tests passed
- [x] No regressions detected
```

---

### Fixer

**Capability**: Bug fix. Fixes the root cause with a regression test, given an
existing diagnosis.

**When to use**:
- Bug with a known or diagnosed cause.
- Fix specific errors with a minimal change.

**Example**:

```
@fixer Fix the bug where refresh tokens are not being validated correctly.
```

**Typical Response**:

```
## Bug Description
Refresh tokens were being validated against expired tokens in database.

## Root Cause
The validation query was not checking the `expiresAt` field.

## Fix Applied
- Modified: `src/services/TokenService.ts`
- Added `expiresAt > NOW()` check in validation query

## Regression Test
- Created: `tests/services/TokenService.test.ts`
- Test: should reject expired refresh tokens

## Verification
- [x] Bug is fixed
- [x] All tests pass
- [x] No new issues introduced
```

---

### Refactorer

**Capability**: Refactoring. Improves structure without changing observable
behavior.

**When to use**:
- Clean, organize, or improve code.
- Reduce duplication, improve readability.

**Example**:

```
@refactorer Refactor the authentication service to reduce duplication and improve readability.
```

**Typical Response**:

```
## Refactoring Goals
- Reduce code duplication in register/login methods
- Improve readability with helper functions
- Extract token generation logic

## Changes Made
- Refactored: `src/services/AuthService.ts`
  - Extracted `hashPassword()` helper
  - Extracted `generateTokens()` helper
  - Split register and login into separate methods

## Tests
- [x] All existing tests pass
- [ ] New tests added: `tests/services/AuthService.test.ts`

## Verification
- [x] Lint passed
- [x] Type-check passed
- [x] All tests passed

## Notes
- Behavior unchanged — only structure improved
```

---

### Reviewer

**Capability**: Read-only review. Evaluates one change set against its task
contract and returns structured evidence; the core records the verdict.

**When to use**:
- After deterministic checks and before merge, when the task declares the
  review gate (required for code changes by policy).

**Example**:

```
@reviewer Review the changes in src/auth/ for the JWT authentication feature.
```

**Typical Response**:

```
## Review Summary
Overall good implementation with proper error handling and tests.

## Issues Found

### Medium
- `src/services/TokenService.ts:45` — Refresh token expiration is 30 days (too long, recommend 7 days)
- `src/api/auth.ts:23` — No input validation on email field

### Suggestions
- Consider extracting token validation logic into a separate middleware
- Add logging for failed login attempts

## Test Coverage
- Good coverage on happy path
- Missing edge cases: invalid tokens, expired tokens

## Verdict
- [x] Approved with minor suggestions

## Notes
- Address medium issues before deploying to production
```

---

### Tester

**Capability**: Testing. Writes deterministic tests and reports artifacts; the
core owns PASS/FAIL and evidence.

**When to use**:
- After implementation and before review, to produce check evidence.
- To ensure the change has meaningful coverage.

**Example**:

```
@tester Write and run tests for the JWT authentication feature.
```

**Typical Response**:

```
## Tests Created
- `tests/services/AuthService.test.ts`
  - should register user with valid email
  - should login user with correct credentials
  - should reject invalid email
  - should reject incorrect password

- `tests/services/TokenService.test.ts`
  - should generate valid access token
  - should generate valid refresh token
  - should validate tokens
  - should reject expired tokens

## Test Results
- Total: 12
- Passed: 12
- Failed: 0
- Skipped: 0

## Coverage
- Lines: 87%
- Branches: 79%

## Issues
- None

## Recommendations
- Add E2E tests for auth flow
- Test rate limiting scenarios
```

---

### Debugger

**Capability**: Diagnosis. Read-only root-cause investigation with explicit
hypotheses and evidence.

**When to use**:
- Bug without a clear cause.
- Difficult problems to diagnose.

**Example**:

```
@debugger Investigate why users are getting "Invalid token" errors randomly.
```

**Typical Response**:

```
## Bug Description
Users randomly receive "Invalid token" errors even with valid tokens.

## Reproduction Steps
1. Login successfully
2. Make multiple API requests
3. After 10-15 requests, get "Invalid token" error

## Evidence
- Error logs show token validation failing
- Tokens are not expired (checked expiresAt)
- Issue occurs more frequently under high load

## Hypotheses
1. **Race condition in token validation** — High likelihood
2. **Database connection pool exhaustion** — Medium likelihood
3. **Clock skew between servers** — Low likelihood

## Investigation
- Added logging to token validation
- Found: Multiple validation queries for same token
- Database returns stale data under load

## Root Cause
Database connection pool is exhausted under high load, causing stale reads.

## Recommended Fix
- Increase connection pool size
- Add connection timeout
- Implement retry logic for validation queries
```

---

### Security

**Capability**: Security audit. Risk-triggered, read-only assessment of
vulnerabilities, data handling and missing controls.

**When to use**:
- Changes involving authentication, authorization, user data, secrets,
  payments, external APIs or permissions.
- After review and before merge when risk applies; the task must declare the
  `security` gate.

**Example**:

```
@security Audit the JWT authentication implementation for OWASP compliance.
```

**Typical Response**:

```
## Security Audit Report

### Critical Issues
- `src/services/TokenService.ts:12` — Refresh tokens stored in localStorage (XSS vulnerability)
  - **OWASP**: A07:2021 — Cross-Site Scripting
  - **Fix**: Move to httpOnly cookies

### Medium Issues
- `src/api/auth.ts:45` — No rate limiting on login endpoint
  - **OWASP**: A07:2021 — Identification and Authentication Failures
  - **Fix**: Add rate limiting (5 attempts per 15 min)

- `src/models/User.ts:23` — Password hash cost is 10 (too low)
  - **Fix**: Increase to 12 or higher

### Recommendations
- Add Content-Security-Policy header
- Implement token binding to prevent theft
- Add logging for failed login attempts

## Compliance
- [ ] OWASP Top 10 addressed (2 critical issues)
- [ ] PII protection verified
- [x] Secrets management secure

## Verdict
- [ ] Changes required (critical issues found)

## Notes
- Do not deploy to production until critical issues are fixed
```

---

### Documenter

**Capability**: Technical writing. Produces README, API reference, guides and
decision records for verified behavior.

**When to use**:
- After major features.
- API changes.
- To create tutorials.

**Example**:

```
@documenter Create API documentation for the authentication endpoints.
```

**Typical Response**:

```
## Documentation Created/Updated
- `docs/api/auth.md` — Authentication API documentation

## Key Sections

### Authentication API

#### POST /api/auth/register
Register a new user.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (201)**:
```json
{
  "data": {
    "userId": "123",
    "email": "user@example.com"
  }
}
```

#### POST /api/auth/login
Login and receive JWT tokens.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200)**:
```json
{
  "data": {
    "accessToken": "eyJhbG...",
    "refreshToken": "eyJhbG..."
  }
}
```

## Notes
- Added examples for all endpoints
- Included error responses
- Documented rate limiting
```

---

### Commenter

**Capability**: Code commentary. Adds JSDoc/TSDoc and inline comments that
explain intent and constraints without changing behavior.

**When to use**:
- After implementation.
- For readability.

**Example**:

```
@commenter Add JSDoc and inline comments to the authentication service.
```

**Typical Response**:

```
## Files Documented
- `src/services/AuthService.ts`
  - Added JSDoc to register(), login(), logout() methods
  - Added inline comments to complex validation logic

- `src/services/TokenService.ts`
  - Added JSDoc to generateAccessToken(), generateRefreshToken(), validateToken()
  - Added inline comments to token validation algorithm

## Documentation Style
- JSDoc with @param, @returns, @throws
- Inline comments for complex logic only

## Notes
- All public APIs are documented
- Private helper functions have minimal comments
```

---

### DevOps

**Capability**: Infrastructure change. CI/CD, containers and deployment
configuration, with inspection-only shell access.

**When to use**:
- Infrastructure changes.
- Deployment.
- Automation.

**Example**:

```
@devops Create a CI/CD pipeline for the authentication service.
```

**Typical Response**:

```
## Changes Made
- Created: `.github/workflows/ci.yml`
- Created: `Dockerfile`
- Created: `docker-compose.yml`

## Infrastructure Updates
- CI pipeline runs on every push to main
- Runs lint, type-check, tests
- Builds Docker image on success
- Deploys to staging automatically

## Verification
- [x] Pipeline runs successfully
- [x] Docker build passes
- [x] Deploy tested in staging

## Documentation
- Updated: `docs/deployment.md`

## Notes
- Production deploy requires manual approval
- Secrets configured via GitHub Secrets
```

---

### Optimizer

**Capability**: Performance. Measures a baseline, removes a proven bottleneck
and reports before/after evidence.

**When to use**:
- Performance optimization tasks.
- When there are performance issues.

**Example**:

```
@optimizer Optimize the token validation query for better performance.
```

**Typical Response**:

```
## Performance Issues Found
- Token validation query does full table scan
- No index on `refreshToken` column
- N+1 queries in auth middleware

## Optimizations Applied
- Modified: `src/services/TokenService.ts`
  - Added index on `refreshToken` column
  - Added caching with Redis (5 min TTL)
  - Batched validation queries

## Benchmarks
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Avg Response Time | 150ms | 25ms | 83% |
| P95 Response Time | 450ms | 75ms | 83% |
| DB Queries/sec | 100 | 600 | 500% |

## Verification
- [x] Tests pass
- [x] No regressions
- [x] Performance improved

## Notes
- Trade-off: Added Redis dependency
- Cache invalidation on token refresh
```

---

## Skills

Skills are **reusable playbooks** that you follow when you want a specific work pattern.

The agent loads a skill automatically when the task matches it. To force one, ask in plain language — no special syntax needed.

### TDD Workflow

**Function**: Guides the agent to follow TDD rigorously: test first, implementation later, refactoring last.

**When to use**:
- Implement new features.
- Fix bugs with tests.

**How to use**:

```
Use the tdd-workflow skill: implement the user registration endpoint.
```

**What happens**:
1. Agent writes a failing test.
2. Implements minimum to pass.
3. Refactors.
4. Repeats for next requirement.

---

### Security Review

**Function**: Security checklist based on OWASP Top 10.

**When to use**:
- Before merge.
- Security audits.

**How to use**:

```
Use the security-review skill: review the authentication module.
```

**What happens**:
1. Checks injection, XSS, CSRF, etc.
2. Validates authentication and authorization.
3. Checks sensitive data and secrets.
4. Generates report with severity.

---

### PRD Template

**Function**: Standard structure for Product Requirements Documents.

**When to use**:
- Create PRDs for new features.
- Document product requirements.

**How to use**:

```
Use the prd-template skill: create a PRD for the password reset feature.
```

**What happens**:
1. Generates PRD with: problem, goal, metrics.
2. Defines scope (in/out).
3. Creates user stories with criteria.
4. Documents technical requirements.

---

### API Design

**Function**: Standards for designing RESTful APIs.

**When to use**:
- Design new APIs.
- Review existing APIs.

**How to use**:

```
Use the api-design skill: design the user profile API.
```

**What happens**:
1. Defines URL structure.
2. Specifies HTTP methods.
3. Documents request/response.
4. Includes pagination, filters, errors.

---

### Code Review Checklist

**Function**: Structured checklist for code review.

**When to use**:
- Code reviews.
- Ensure consistency.

**How to use**:

```
Use the code-review-checklist skill: review the auth service implementation.
```

**What happens**:
1. Checks functionality.
2. Checks code quality.
3. Validates tests.
4. Audits security.
5. Evaluates performance.
6. Verifies documentation.

---

### Context Management

**Function**: Token usage and context optimization.

**When to use**:
- Long sessions.
- To reduce token consumption.

**How to use**:

```
Use the context-management skill: optimize the current session context.
```

**What happens**:
1. Removes irrelevant files.
2. Summarizes long conversations.
3. Loads only necessary context.
4. Uses context cache.

---

## Commands

Commands are **slash shortcuts** you type in chat for specific actions.

### Backlog Commands

#### `/add-backlog`

Adds task to backlog.

```
/add-backlog Create password reset flow with email verification
```

#### `/start`

Starts a task from backlog.

```
/start TASK-001
```

#### `/edit-backlog`

Edits a task from backlog.

```
/edit-backlog TASK-001
```

#### `/remove-backlog`

Removes a task from backlog.

```
/remove-backlog TASK-001
```

---

### Development Commands

#### `/plan`

Creates detailed implementation plan.

```
/plan Create user profile API with CRUD operations
```

#### `/document`

Creates or updates documentation.

```
/document Create API documentation for authentication endpoints
```

> **Note:** `/compact` (summarize the current session to reduce tokens) is a **native OpenCode command**, not part of the Juicer Kit. Just type `/compact` (alias `/summarize`) in the TUI.

---

### Quality Commands

#### `/review`

Reviews code changes. Runs as the `@reviewer` agent.

```
/review Review all changes in the last commit
```

#### `/security-audit`

Audits code with security focus.

```
/security-audit Audit the authentication module
```

#### `/test`

Creates and runs tests. Runs as the `@tester` agent.

```
/test Run tests for the auth module
```

---

## Capability Selection

There are no mandatory pipelines. Start from the task, then select only the
capabilities it needs. A capability may be one agent, several agents, or none
of them; the core's gate order is the only fixed sequence.

### Simple bug with a known cause

**Scenario**: A token-expiry comparison is wrong and the fix is local.

```
@fixer Fix the expiry comparison in src/services/TokenService.ts.
```

That may be the whole selection. Deterministic checks run next; review happens
if the task declares the review gate. `@finder`, `@architect` and `@planner`
are not required for a local fix.

### Complex feature

**Scenario**: Create JWT authentication across several modules.

```
@finder Locate the existing auth code, patterns and tests.
@architect Design the JWT flow, interfaces and data model.
@coder Implement the approved design inside scope.paths.
@tester Produce deterministic check evidence.
@reviewer Review after checks and before merge.
```

Each line is selected because the task needs that capability. `@analyst` is
added when dependencies or data flow are unclear; `@planner` is added when the
design must be split into atomic tasks; `@documenter` is added only if public
behavior changes. Stop when the task's contract is satisfied.

### Risk-triggered security review

**Scenario**: Audit an auth change before deployment.

```
@security Audit the authentication change.
@fixer Fix the critical findings.
@security Re-audit the fix.
```

Security is selected because authentication is a risk trigger, and the task
must declare the `security` gate. `@security` never replaces `@reviewer`.

### With the core (auditable path)

```bash
# Mission and task registration
juicer mission --title "JWT authentication" --objective "..." --criterion "tests pass"
juicer decompose tasks.json       # or: juicer import-backlog
juicer status

# Implementation in an isolated worktree
juicer run TASK-001

# Deterministic checks ran with the task; now produce gate evidence
juicer review-run TASK-001
juicer security-run TASK-001      # only when security is in required_gates

# Human approval when required (high risk always requires it)
juicer approve TASK-001 --approver "your-name"

# Explicit merge + post-merge checks
juicer integrate TASK-001 --approve
```

Canonical order enforced by the core:
**implementation → deterministic checks → review → security (when applicable) →
human approval (when applicable) → merge/integrate → post-merge checks → done.**
A task is `completed` before the merge and only becomes `done` after the
post-merge checks pass.

---

## Best Practices

### 1. Use the orchestrator to select capabilities for complex tasks

```
@orchestrator Create user authentication with JWT.
```

It helps choose the capabilities the task needs and delegates; it does not run
a mandatory chain and does not waive the core's gates.

### 2. Add tasks to backlog instead of executing immediately

```
/add-backlog Create password reset flow
```

This allows prioritization and planning.

### 3. Always test and review before merge

```
@tester Run tests.
@reviewer Review the changes.
```

Don't skip these steps. When using the core, `review` is a gate only if it is
declared in `approval_policy.required_gates`; declare it deliberately for code
changes.

### 4. Use security for critical features

```
@security Audit the authentication module.
```

Required for auth, user data, secrets and other high-risk changes. The core does
not add the security gate implicitly: declare `security` in `required_gates`.
High risk always requires recorded human approval.

### 5. Document major features

```
@documenter Create API documentation.
```

Facilitates maintenance and onboarding.

### 6. Use `/compact` in long sessions

`/compact` is a **native OpenCode command** (alias `/summarize`), not a Juicer Kit command.

```
/compact
```

Reduces token consumption and keeps focus.

### 7. Keep backlog and core state consistent

The backlog Markdown is the planning board. After a mission import, `.juicer/`
is canonical. Do not try to keep both in sync by hand:

- use `/add-backlog` and `/edit-backlog` for planning;
- use `juicer import-backlog` once to seed the mission;
- use `juicer status`/`events` for operational state;
- move the task to `backlog/done/` only after the core reaches `done`.

### 8. Treat `NOT RUN` as not passing

If a check or gate could not run (timeout, missing tool, provider quota), the
result is not a pass. Re-run it or leave the task blocked.

### 9. Require explicit approval for risky work

Record approval with `juicer approve TASK-ID --approver NAME`. `integrate
--approve` alone is not an approval record. Approval never replaces tests or
review.

### 10. Learn from repeated issues

If a bug appears multiple times, document cause and solution.

---

## Token Optimization

Token consumption can get expensive in long sessions. Here are strategies to optimize:

### 1. Context Pruning

Remove irrelevant files from context.

```
@finder Load only files related to authentication.
```

### 2. Summarization

Use `/compact` (native OpenCode command) when session exceeds ~50 messages.

```
/compact
```

### 3. Selective Loading

Load only necessary files.

```
@finder Find files related to token validation.
```

### 4. Context Cache

Store frequent context in `docs/context/`.

```
@documenter Create a context cache file for the authentication architecture.
```

### 5. Avoid Bloat

Don't repeat information already in backlog or docs.

```
See `backlog/backlog.md#TASK-001` for details.
```

---

## Troubleshooting

### Problem: Agents don't appear in list

**Solution**:

1. Check if `.opencode/agents/` folder exists.
2. Restart OpenCode.
3. Check if files have `.md` extension.

### Problem: Backlog doesn't update

**Solution**:

1. Check if `backlog.md` and `in-progress.md` files are in place.
2. Check write permissions.
3. Try editing manually to test.

### Problem: Agents don't follow the expected order

**Solution**:

1. Remember that there is no mandatory pipeline: select capabilities per task.
2. Use `@orchestrator` or the core `juicer` to choose capabilities and enforce
   the canonical gate order.
3. Call capabilities manually when the task is small and the selection is clear.
4. Check that agents are configured correctly.

### Problem: Excessive token consumption

**Solution**:

1. Use `/compact` regularly.
2. Load only necessary context.
3. Avoid very long sessions (split into multiple).

### Problem: Agents don't understand context

**Solution**:

1. Provide more context in prompt.
2. Use `@finder` to load relevant files.
3. Document context in `docs/context/`.

### Problem: `juicer discover` says the harness is unsupported or degraded

**Solution**:

1. Run `opencode --version` and confirm a 2.x version (`v2.2.7` measured).
2. Set `export OPENCODE_BIN=/path/to/opencode` if auto-detection fails.
3. Remember that a V1 binary is `degraded`; V1 compatibility is not promised.
4. Run `python3 bin/juicer discover` again and check `capabilities.v2`.

### Problem: `Agent not found` in a worktree

**Solution**:

1. Keep worktrees inside the project (`.juicer/worktrees/<task>`). V2 discovers
   `.opencode/` by walking up from `PWD`.
2. If worktrees must live outside the project, provide `.opencode/` in the
   worktree or in global OpenCode configuration.
3. Confirm the agent exists with `@` in OpenCode and that `.opencode/agents/`
   is at the project root.

### Problem: The agent edited the wrong repository

**Solution**:

1. Use the V2 adapter, which sets both `cwd` and `PWD` to the resolved
   worktree. V2 resolves the project from `PWD`; a subprocess `cwd` alone is
   not enough.
2. Do not override `PWD` in your shell wrapper.
3. Check the execution record in `.juicer/executions/` for the worktree path,
   and verify `juicer status` before integrating.

### Problem: `integrate` is blocked by review, security or approval

**Solution**:

1. The task must be `completed` and its worktree clean and at the task commit.
2. Run `juicer review-run TASK-ID` when `review` is declared.
3. Run `juicer security-run TASK-ID` when `security` is declared.
4. Run `juicer approve TASK-ID --approver NAME` when approval applies.
5. `integrate --approve` is only merge intent; it does not create approval.
6. Missing/stale evidence is `BLOCKED`/`NOT RUN`, never a pass.

### Problem: A check is `NOT RUN`

**Solution**:

1. `NOT RUN` means the required result was not obtained (missing, failed to
   start, or stale for another commit). It is not a pass.
2. Confirm the check command exists and runs locally.
3. Re-run the task or the check; a new commit invalidates previous evidence.
4. Do not edit `.juicer/` to force a status.

### Problem: Provider returns HTTP 402 or 429

**Solution**:

1. HTTP 402 is a quota/credit limit; HTTP 429 is a usage/rate limit. Both are
   provider-side, not core failures.
2. Add credits, lower `max_tokens`, or wait for the limit window.
3. Re-run `juicer run`/`review-run`/`security-run` after quota is available.
4. A blocked provider call is not evidence and never becomes a PASS.

### Problem: `juicer` complains about a dirty checkout or a missing commit

**Solution**:

1. The core refuses to overwrite pre-existing changes; commit or stash them.
2. The repository must have at least one commit.
3. Use `juicer retry` for failed/blocked tasks and `juicer resume` after an
   interruption; do not delete `.juicer/` to "reset" without preserving
   evidence.

### Problem: `juicer resume` leaves a task blocked

**Solution**:

1. Read `juicer status` and the checkpoint/events for the exact `blocked_reason`.
2. A missing worktree yields `failed`; an interrupted worktree yields
   `blocked` with a recorded next step.
3. Resolve the conflict/interruption, then `juicer retry TASK-ID` or repair the
   worktree as indicated.
4. Post-merge failure stays `blocked`; it never becomes `completed`/`done`.

### Problem: Core writes are allowed outside the worktree

**Solution**:

1. The core validates the worktree diff, but direct writes to `.juicer/` or
   other paths are a harness/sandbox concern.
2. In V2, `external_directory` is allowed by default. Configure
   `permissions[]` with `allow`/`ask`/`deny` in `opencode.json(c)`.
3. Permissions are an additional barrier; they do not replace core gates or
   evidence.

---

## Practical Examples

### Example 1: Create Feature from Scratch

```
You: @orchestrator Create user authentication with JWT.

@orchestrator: I understand. Do you want me to:
1. Execute now?
2. Add to backlog?
3. Plan first?

You: Add to backlog.

@orchestrator: Task added as TASK-001.

@orchestrator: Want to start now?

You: Yes.

@orchestrator: Starting TASK-001...

[Selects the capabilities the task needs; no fixed pipeline]
```

### Example 2: Fix Bug

```
You: @debugger Users are getting "Invalid token" errors randomly.

@debugger: [Investigates and finds root cause]

@debugger: Cause found: Database connection pool exhaustion.

You: @fixer Fix the database connection pool issue.

@fixer: [Fixes]

@tester: [Tests]

@reviewer: [Reviews]
```

### Example 3: Security Review

```
You: @security Audit the authentication module before deployment.

@security: [Audits]

@security: Critical: Refresh tokens in localStorage.

You: @fixer Move refresh tokens to httpOnly cookies.

@fixer: [Fixes]

@security: [Re-audits]

@security: No critical issues. Approved.
```

### Example 4: Auditable Task with the Core

```
You: juicer mission --title "Add request IDs" \
       --objective "Every response has a request id" \
       --criterion "header present + tests"

You: juicer import-backlog
You: juicer status

juicer: TASK-001 ready (dependencies: none)

You: juicer run TASK-001

juicer: task completed in .juicer/worktrees/TASK-001
        commit <sha>, changes: src/middleware/request_id.py, tests/...
        checks: tests PASS
        next: review-run TASK-001 (review gate declared)

You: juicer review-run TASK-001

juicer: @reviewer evidence recorded (verdict PASS, linked to <sha>/<tree>)

You: juicer integrate TASK-001

juicer: PRE_MERGE PASS
        merged <sha> (--no-ff)
        POST_MERGE PASS
        task TASK-001 done
```

If any declared gate is missing, stale or failed, `integrate` refuses with
`BLOCKED`/`NOT RUN` and the task stays `completed`, not `done`.

---

## Contribution

Want to contribute to Juicer Kit?

### 1. Fork the repository

Use the **Fork** button on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-user>/juicer-kit.git
```

### 2. Create a branch

```bash
git checkout -b feature/new-agent
```

### 3. Add the agent

Create a file in `.opencode/agents/<name>.md`.

### 4. Document

Add information in `README.md` and, when behavior changes, in this guide.

### 5. Test

For Markdown-only changes, verify the agent/command/skill is loaded in OpenCode.

For changes to the core, run the deterministic suite:

```bash
python3 -m compileall juicer/ bin/juicer
uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py
# optional, real V2 capabilities probe (no model call):
JUICER_OPENCODE_SMOKE=1 uv tool run pytest tests/test_opencode_smoke.py -q -k capabilities
```

Expected baseline for 4.1.0: **354 passed** (including 27 documentation-alignment
contracts). A `NOT RUN` or skipped test is not a pass. The opt-in model smoke
needs provider quota and is not part of the default suite.

### 6. Submit a PR

```bash
git push origin feature/new-agent
# Open a PR on GitHub
```

Changes to gates, evidence, scope or approval must include tests and a review.
Security-sensitive changes (auth, secrets, permissions, workspace isolation)
also require a security review.

---

## Conclusion

Congratulations! You completed the **Juicer Kit Complete Guide**!

Now you know:
- How to install and configure the Markdown kit and the 4.1.0 core.
- How to use all agents.
- How to manage tasks with backlog and import them into a mission.
- How the core runs tasks in isolated worktrees and enforces gates.
- How to apply skills and commands.
- How to follow workflows, from implementation to post-merge.
- How to optimize tokens and avoid mistakes.

**Next steps**:
1. Test the kit in your project.
2. Adapt agents to your context.
3. Contribute improvements.
4. Share with your team.

Questions? Suggestions? Open an issue on GitHub!

---

**License**: MIT — use freely in your projects.
