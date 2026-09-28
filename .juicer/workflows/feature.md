# Feature Workflow

## Phase 1 — Discover

Worker: `finder`

Output:
- relevant files
- architecture map
- dependencies
- unknowns

## Phase 2 — Analyze

Worker: `analyst`

Output:
- current behavior
- constraints
- risks
- affected surfaces

## Phase 3 — Design

Worker: `architect`

Output:
- proposed architecture
- interfaces
- data flow
- migration concerns

## Phase 4 — Plan

Worker: `planner`

Output:
- atomic units
- acceptance criteria
- verification strategy

## Human Gate

User approves `.juicer/plan.md`.

## Phase 5 — Implement

Worker selected by task:
- coder
- editor
- fixer
- refactorer

## Phase 6 — Review

Worker: `reviewer`

Must identify:
- correctness
- regressions
- security
- maintainability
- missing tests

## Phase 7 — Test

Worker: `tester`

Must run the narrowest relevant tests first, then broader tests where justified.

## Phase 8 — Document

Worker: `documenter`

Update only documentation affected by the change.

## Phase 9 — Ship

Worker: `devops` if infrastructure/release work is required.

Human confirms production-impacting actions.
