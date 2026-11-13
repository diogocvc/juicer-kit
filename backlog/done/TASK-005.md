# Task: [TASK-005] Verificar critérios, gates e evidências de revisão/segurança

**Description**: Tornar critérios de aceitação e `required_gates` efetivos, vincular evidências ao commit/tree corretos e exigir revisão e segurança quando aplicável, usando os agentes existentes.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-10-29 15:15

**Assigned To**: @coder

**Implementation Summary**:
- `juicer/evidence.py`: artefatos estruturados de review/security vinculados a commit/tree; `validate_findings` fail-fast (severidade/descrição/linha); guard M-4 (PASS não sobrescreve FAIL, inclusive FAIL derivado de achado crítico) com `--force`.
- Semântica M-2: artefato ausente/malformado → BLOCKED; artefato stale (outro commit/tree) → NOT RUN.
- Critérios de aceitação: `verification` validado (`check:<id>`, `review`, `security`, `human`) e avaliado no `integrate` com auditoria por critério (`acceptance_criteria` + evento `criteria_evaluated`).
- Acionamento dos agentes existentes: `juicer review-run`/`security-run` executam `@reviewer`/`@security`, exigem um bloco JSON estrito, validam e gravam o artefato com commit/tree calculados pelo core; prosa é rejeitada.
- Fail-closed: worktree ausente/sujo/HEAD divergente recusa; mutação do worktree pelo agente descarta a evidência.
- Parse V2 real: texto assistente do NDJSON exposto como `agent_output` pelo adaptador.

**Test Coverage**:
- [x] Unit tests (`tests/test_evidence.py`, `tests/test_criteria.py`, `tests/test_agent_evidence.py`)
- [x] Integração (`tests/test_integrate.py`, `tests/test_cli.py`, `tests/test_transitions.py`)
- [x] Regressão do formato NDJSON real V2 e wrapper end-to-end com binário fake
- [x] Smoke real opt-in: `@reviewer` executado no V2.1.4 (JSON estrito) e saída real reproduzida até `done`

**Security Review**:
- [x] Revisado por @reviewer (incremento: changes requested → corrigido → approved)
- [x] Sem achados críticos após correções

**Documentation**:
- [x] README, STATUS, HARNESS_CONTRACT e CHANGELOG atualizados
- [x] `backlog/review-findings-TASK-003-005.md` com achados e decisões

**Notes**: `security-run` ao vivo não executado (mesmo caminho de código, coberto por testes; segunda chamada bloqueada por quota HTTP 402 do provider). Pendência registrada no `STATUS.md`.
