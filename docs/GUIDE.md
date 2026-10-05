# Juicer Kit Complete Guide

## Table of Contents

1. [Introduction](#introduction)
2. [What is Juicer Kit](#what-is-juicer-kit)
3. [Who This Guide Is For](#who-this-guide-is-for)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
   - [Option 1: Manual Copy](#option-1-manual-copy)
   - [Option 2: Git Submodule](#option-2-git-submodule)
   - [Option 3: Symlink](#option-3-symlink)
6. [Kit Structure](#kit-structure)
7. [Initial Setup](#initial-setup)
8. [Getting Started](#getting-started)
   - [Starting OpenCode](#starting-opencode)
   - [Testing Agents](#testing-agents)
9. [Backlog System](#backlog-system)
   - [What is the Backlog](#what-is-the-backlog)
   - [Adding Tasks](#adding-tasks)
   - [Viewing the Backlog](#viewing-the-backlog)
   - [Starting a Task](#starting-a-task)
   - [Editing Tasks](#editing-tasks)
   - [Removing Tasks](#removing-tasks)
10. [Agents](#agents)
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
11. [Skills](#skills)
    - [TDD Workflow](#tdd-workflow)
    - [Security Review](#security-review)
    - [PRD Template](#prd-template)
    - [API Design](#api-design)
    - [Code Review Checklist](#code-review-checklist)
    - [Context Management](#context-management)
12. [Commands](#commands)
    - [Backlog Commands](#backlog-commands)
    - [Development Commands](#development-commands)
    - [Quality Commands](#quality-commands)
13. [Workflows](#workflows)
    - [New Feature](#new-feature)
    - [Bug Fix](#bug-fix)
    - [Refactoring](#refactoring)
    - [Security Review](#security-review-1)
14. [Best Practices](#best-practices)
15. [Token Optimization](#token-optimization)
16. [Troubleshooting](#troubleshooting)
17. [Practical Examples](#practical-examples)
18. [Contribution](#contribution)

---

## Introduction

Welcome to the **Juicer Kit Complete Guide**! This guide was created to help people of **all skill levels** use agents in OpenCode efficiently, securely, and productively.

Whether you are:
- **Beginner** in AI and agents → This guide will teach you from scratch.
- **Intermediate** → Will optimize your workflow.
- **Advanced** → Will find patterns and practices to scale.

The goal is that by the end of this guide, you will be able to:
- Set up Juicer Kit in your project.
- Use all agents autonomously.
- Manage tasks with the backlog system.
- Apply skills and commands to accelerate work.
- Follow proven workflows.
- Avoid common mistakes and optimize token usage.

Let's go!

---

## What is Juicer Kit

**Juicer Kit** is a set of **specialized agents**, **skills**, and **commands** for OpenCode, inspired by Mission Kit and optimized for workflows with:

- **Human autonomy** → You decide when and how to use each agent.
- **Security** → Mandatory reviews and audits for critical features.
- **Quality** → Defined pipelines with review and tests on every change.
- **Reusability** → Structure that works in VS Code, Zed, and other editors.

### Analogy

Think of Juicer Kit as a **complete development team**:

- **Product Owner** → `@orchestrator` (manages backlog, prioritizes)
- **Architect** → `@architect` (designs solutions)
- **Developer** → `@coder` (implements code)
- **Reviewer** → `@reviewer` (reviews quality)
- **QA** → `@tester` (creates and runs tests)
- **Security** → `@security` (audits vulnerabilities)
- **DevOps** → `@devops` (CI/CD, deployment)
- **Tech Writer** → `@documenter` (documentation)

Each agent is a **specialist** in one area, and you call them as needed.

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

### 1. OpenCode Installed

Juicer Kit works with **OpenCode**, an open-source coding agent.

**Installation**:

```bash
# macOS/Linux
curl -fsSL https://opencode.ai/install | bash

# Windows
# Download installer at https://opencode.ai
```

**Verification**:

```bash
opencode --version
```

### 2. Code Editor

Juicer Kit works in:

- **VS Code** (recommended for beginners)
- **Zed** (lighter, via ACP)
- **Any editor** with integrated terminal

### 3. GitHub Account (optional)

For using Git submodules and contributing to the kit.

### 4. API Keys (optional)

OpenCode works with various providers:

- **OpenAI** (GPT-4, GPT-5)
- **Anthropic** (Claude)
- **Google** (Gemini)
- **OpenRouter** (170+ models)

Configure your keys in `~/.config/opencode/config.json` or via environment variables.

---

## Installation

There are 3 ways to install Juicer Kit in your project.

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
   cp -r ../juicer-kit/skills ./
   cp -r ../juicer-kit/commands ./
   ```

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
   git submodule add https://github.com/diogocvc/juicer-kit.git .opencode
   ```

2. **Copy other folders** (backlog, skills, commands):

   ```bash
   cp -r .opencode/backlog ./
   cp -r .opencode/skills ./
   cp -r .opencode/commands ./
   ```

3. **Commit**:

   ```bash
   git add .
   git commit -m "Add Juicer Kit as submodule"
   ```

**To update in the future**:

```bash
git submodule update --remote
```

**Advantages**:
- Automatic updates.
- Single repository to maintain.
- Easy to sync across multiple projects.

**Disadvantages**:
- Requires Git knowledge.
- Can conflict if you modify files.

---

### Option 3: Symlink

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
   ln -s ~/juicer-kit/skills ./skills
   ln -s ~/juicer-kit/commands ./commands
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
├── .opencode/
│   └── agents/
│       ├── orchestrator.md       # Product Owner
│       ├── finder.md             # Explorer
│       ├── analyst.md            # Analyst
│       ├── researcher.md         # Researcher
│       ├── architect.md          # Architect
│       ├── planner.md            # Planner
│       ├── coder.md              # Developer
│       ├── editor.md             # Editor
│       ├── fixer.md              # Fixer
│       ├── refactorer.md         # Refactorer
│       ├── reviewer.md           # Reviewer
│       ├── tester.md             # Tester
│       ├── debugger.md           # Debugger
│       ├── security.md           # Security Auditor
│       ├── documenter.md         # Documenter
│       ├── commenter.md          # Commenter
│       ├── devops.md             # DevOps
│       └── optimizer.md          # Optimizer
├── backlog/
│   ├── backlog.md            # Pending tasks
│   ├── in-progress.md        # Tasks in progress
│   └── done/                 # Completed tasks
├── .opencode/skills/
│   ├── tdd-workflow/SKILL.md
│   ├── security-review/SKILL.md
│   ├── prd-template/SKILL.md
│   ├── api-design/SKILL.md
│   ├── code-review-checklist/SKILL.md
│   └── context-management/SKILL.md
└── .opencode/commands/
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

### What each part does:

- **`.opencode/agents/`** → Specialized agents (the "team" of AI).
- **`backlog/`** → Task management system.
- **`.opencode/skills/`** → Reusable playbooks (e.g., TDD, security review).
- **`.opencode/commands/`** → Slash shortcuts (e.g., `/add-backlog`, `/plan`).

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

Edit `~/.config/opencode/config.json`:

```json
{
  "default_model": "anthropic/claude-sonnet-4.5"
}
```

**Option B: Per Session**

In OpenCode chat:

```
/model openai/gpt-5.2-high
```

**Option C: Per Agent**

Each agent has a `model` field in frontmatter. You can edit:

```md
---
description: "..."
model: "anthropic/claude-sonnet-4.5"  # Suggestion
---
```

### 3. Customize `backlog/backlog.md`

The backlog comes with example tasks. You can:

- **Delete example tasks**.
- **Add your own tasks**.
- **Leave as is** and use the system.

### 4. Test with a Simple Command

In OpenCode chat:

```
@finder Map the project structure.
```

If the agent responds with project structure, everything is working!

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

## Backlog System

The backlog system is one of the most powerful features of Juicer Kit.

### What is the Backlog

The **backlog** is a list of pending, in-progress, and completed tasks. It works like a **Kanban board** in Markdown.

**Files**:

- `backlog/backlog.md` → Pending tasks.
- `backlog/in-progress.md` → Tasks being done now.
- `backlog/done/` → Completed tasks (one per file).

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

**Plan**:
1. @finder → Map auth-related files
2. @architect → Design JWT auth system
3. @planner → Break down into tasks
4. @coder → Implement
5. @reviewer → Review
6. @tester → Test
7. @security → Security audit
8. @documenter → Document

**Next**: @orchestrator will begin execution.
```

The orchestrator automatically:
1. Moves task to `in-progress.md`.
2. Starts the agent pipeline.
3. Updates status as it progresses.

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

---

## Agents

Each agent is a **specialist** in one area. You call them with `@agent-name`.

### Orchestrator

**Function**: Product Owner. Manages backlog, prioritizes tasks, delegates to sub-agents.

**When to use**:
- Complex sessions with multiple steps.
- When you want the system to manage flow automatically.

**Example**:

```
@orchestrator Start working on the backlog.
```

**What it does**:
1. Reads backlog.
2. Prioritizes tasks.
3. Pulls first task.
4. Delegates to appropriate agents.
5. Updates status.

---

### Finder

**Function**: Fast codebase scout. Finds files, patterns, structure.

**When to use**:
- First step of any task.
- To understand project structure.

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

**Function**: Deep code analysis. Dependencies, risks, data flow.

**When to use**:
- After `@finder`.
- Before planning or implementing.

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

**Function**: External research. Official docs, best practices, compliance.

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

**Function**: Solution architect. Designs components, interfaces, patterns.

**When to use**:
- After analysis.
- Before detailing tasks.

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

**Function**: Task decomposer. Breaks architecture into atomic tasks.

**When to use**:
- After architecture.
- Before coding.

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

**Function**: Main developer. Creates new code from scratch.

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

**Function**: Code editor. Safely modifies existing code.

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

**Function**: Bug fixer. Fixes with minimal changes.

**When to use**:
- Bug with known cause.
- Fix specific errors.

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

**Function**: Refactoring specialist. Improves structure without changing behavior.

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

**Function**: Code reviewer. Quality, best practices, issue identification.

**When to use**:
- After any code change (**mandatory**).
- Before merge.

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

**Function**: Test engineer. Creates and runs unit, integration, E2E tests.

**When to use**:
- After implementation and review (**mandatory**).
- To ensure test coverage.

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

**Function**: Bug investigator. Root cause, diagnosis, hypotheses.

**When to use**:
- Bug without clear cause.
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

**Function**: Security auditor. OWASP, sensitive data, authentication.

**When to use**:
- Features with auth, user data, secrets, external APIs (**mandatory**).
- Before production deployment.

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

**Function**: Technical writer. README, API docs, guides, tutorials.

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

**Function**: Code commenter. Adds JSDoc, TSDoc, and inline comments.

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

**Function**: DevOps engineer. CI/CD, Docker, deployment, infrastructure.

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

**Function**: Performance optimizer. Bottlenecks, memory, efficiency.

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

Skills are **reusable playbooks** that you invoke when you want to follow a specific work pattern.

### TDD Workflow

**Function**: Guides the agent to follow TDD rigorously: test first, implementation later, refactoring last.

**When to use**:
- Implement new features.
- Fix bugs with tests.

**How to use**:

```
@skill tdd-workflow Implement the user registration endpoint.
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
@skill security-review Review the authentication module.
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
@skill prd-template Create a PRD for the password reset feature.
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
@skill api-design Design the user profile API.
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
@skill code-review-checklist Review the auth service implementation.
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
@skill context-management Optimize the current session context.
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

Reviews code changes.

```
/review Review all changes in the last commit
```

#### `/security-audit`

Audits code with security focus.

```
/security-audit Audit the authentication module
```

#### `/test`

Creates and runs tests.

```
/test Run tests for the auth module
```

---

## Workflows

Let's see complete flows from start to finish.

### New Feature

**Scenario**: Create JWT authentication.

**Flow**:

```
1. @finder → Map project structure
2. @analyst → Analyze existing code
3. @architect → Design JWT architecture
4. @planner → Break down into tasks
5. @coder → Implement task 1
6. @reviewer → Review
7. @tester → Test
8. @security → Security audit
9. @documenter → Document
```

**With orchestrator**:

```
@orchestrator Create JWT authentication feature.

@orchestrator: I understand. Do you want me to:
1. Execute now?
2. Add to backlog?
3. Plan first?

You: Execute now.

@orchestrator: Starting...

[Follows pipeline automatically]
```

---

### Bug Fix

**Scenario**: Users randomly get "Invalid token" error.

**Flow**:

```
1. @finder → Map auth code
2. @debugger → Investigate root cause
3. @fixer → Fix bug
4. @reviewer → Review
5. @tester → Test
```

**With orchestrator**:

```
@orchestrator Fix the "Invalid token" error that users are experiencing.

@orchestrator: I understand. I'll investigate root cause first.

@debugger: [Investigates and finds cause]

@fixer: [Fixes]

@reviewer: [Reviews]

@tester: [Tests]
```

---

### Refactoring

**Scenario**: Improve auth service structure.

**Flow**:

```
1. @finder → Map code
2. @analyst → Analyze current structure
3. @refactorer → Refactor
4. @reviewer → Review
5. @tester → Test
```

---

### Security Review

**Scenario**: Audit auth module before deployment.

**Flow**:

```
1. @security → Audit vulnerabilities
2. @reviewer → Review code
3. @fixer → Fix critical issues
4. @security → Re-audit
```

---

## Best Practices

### 1. Always use orchestrator for complex tasks

```
@orchestrator Create user authentication with JWT.
```

It manages the flow automatically.

### 2. Add tasks to backlog instead of executing immediately

```
/add-backlog Create password reset flow
```

This allows prioritization and planning.

### 3. Always review and test before merge

```
@reviewer Review the changes.
@tester Run tests.
```

Don't skip these steps.

### 4. Use security for critical features

```
@security Audit the authentication module.
```

Mandatory for auth, user data, secrets.

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

### 7. Keep backlog updated

Always move task to `done/` when completed.

### 8. Learn from repeated issues

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

### Problem: Agents don't follow pipeline

**Solution**:

1. Use `@orchestrator` to manage flow.
2. Call agents manually in correct order.
3. Check if agents are configured correctly.

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

[Follows pipeline automatically]
```

### Example 2: Fix Bug

```
You: @debugger Users are getting "Invalid token" errors randomly.

@debugger: [Investigates and finds root cause]

@debugger: Cause found: Database connection pool exhaustion.

You: @fixer Fix the database connection pool issue.

@fixer: [Fixes]

@reviewer: [Reviews]

@tester: [Tests]
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

---

## Contribution

Want to contribute to Juicer Kit?

### 1. Fork the repository

```bash
git fork https://github.com/diogocvc/juicer-kit.git
```

### 2. Create a branch

```bash
git checkout -b feature/new-agent
```

### 3. Add the agent

Create a file in `.opencode/agents/<name>.md`.

### 4. Document

Add information in `README.md`.

### 5. Submit a PR

```bash
git push origin feature/new-agent
# Open a PR on GitHub
```

---

## Conclusion

Congratulations! You completed the **Juicer Kit Complete Guide**!

Now you know:
- How to install and configure.
- How to use all agents.
- How to manage tasks with backlog.
- How to apply skills and commands.
- How to follow workflows.
- How to optimize tokens and avoid mistakes.

**Next steps**:
1. Test the kit in your project.
2. Adapt agents to your context.
3. Contribute improvements.
4. Share with your team.

Questions? Suggestions? Open an issue on GitHub!

---

**License**: MIT — use freely in your projects.
