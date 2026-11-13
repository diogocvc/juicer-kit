# Task: [TASK-004] Aplicar transições e reconciliar retomada de estado

**Description**: Fazer todas as atualizações de tarefa e execução passarem pela validação de transições, preservar revisão e histórico e reconciliar `in_progress` com execuções/worktrees reais no `resume`.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-10-29 15:15

**Assigned To**: @coder

**Implementation Summary**:
- `check_transition` aplicado em `_update_task`/`_update_execution` com `TASK_TRANSITIONS`/`EXECUTION_TRANSITIONS`.
- `resume` reconcilia execução + worktree: succeeded→completed copiando `result` (commit/branch), interrompido+worktree→blocked, sem worktree→failed.
- `retry_task` retoma failed/blocked preservando `attempt_history`.
- CR-2: gate FAIL no `integrate` move `completed → blocked` com `blocked_reason` + evento `integration_gate_failed` (nunca estado-armadilha).
- M-1: `integrate` falha limpo (BLOCKED) quando commit/branch ausente.
- M-3: `_check_scope` com fronteira de caminho (`src/` não casa `srcx/evil.py`).
- Falha pós-merge sempre termina em `blocked`.

**Test Coverage**:
- [x] Unit tests (`tests/test_transitions.py`, `tests/test_runs.py`, `tests/test_gates.py`)
- [x] Integração (`tests/test_integrate.py`, recuperação pós-FAIL e resume→integrate)
- [x] Invariantes de `completed`/`done` e falha pós-merge

**Security Review**:
- [x] Revisado por @reviewer (CR-2/M-1/M-3 resolvidos)
- [x] Sem achados críticos na re-revisão

**Documentation**:
- [x] Invariantes documentadas em `juicer/model.py` e no plano
- [x] Backlog e findings atualizados

**Notes**: Nenhuma pendência técnica. Ver `backlog/review-findings-TASK-003-005.md`.
