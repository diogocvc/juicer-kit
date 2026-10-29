# In Progress

## Current Tasks

### Task: [TASK-003] Definir contrato do harness e validar OpenCode V2

**Started At**: 2026-10-25 12:35

**Assigned To**: @coder

**Current Step**: Validação V2 medida no working tree; CR-1 resolvido; re-revisão @reviewer aprovada (Approved with minor suggestions); aguardando aprovação humana e integração

**Blockers**: Nenhum técnico. Pendente aprovação humana explícita para merge (re-revisão @reviewer 2026-10-29: Approved with minor suggestions; ver `backlog/review-findings-TASK-003-005.md`).

**Progress**:
- [x] Tarefa selecionada e movida para in-progress
- [x] Contrato e testes de contrato (base V1 preservada e adaptada)
- [x] Adaptador estruturado sobre o contrato (V2-first)
- [x] Revisão da mudança de alvo para V2 (2026-10-26)
- [x] Provisionamento/detecção do binário V2 (opencode v2.1.4)
- [x] Adaptador e capabilities alinhados à CLI V2 real (CWD, --standalone, sem --dir)
- [x] Smoke real V2 e atualização do STATUS (medido × documental)
- [x] Revisão de código (@reviewer) — Changes requested
- [x] Corrigir achado crítico CR-1 (regex de detecção V2; TDD, 2026-10-29)
- [x] Re-revisão (@reviewer) — Approved with minor suggestions (2026-10-29)
- [ ] Aprovação humana e integração

**Notes**: Critérios técnicos da TASK-003 cumpridos no working tree (não commitado). ID, estado In Progress e histórico preservados. Sem SDK, sem duas integrações paralelas. `--dir` inexistente na V2 medida; isolamento via CWD + `--standalone`. CR-1 resolvido 2026-10-29: `_version_is_v2` com parse explícito de major (≥ 2), com testes de falso positivo (`1.2.4`, `v1.2.0`) e major alto (`10.2.3` → True). Ver TASK-003 em `backlog/backlog.md`.

---

### Task: [TASK-004] Aplicar transições e reconciliar retomada de estado

**Started At**: 2026-10-26

**Assigned To**: @coder

**Current Step**: Transições, resume e escopo reconciliados; CR-2/M-1/M-3 resolvidos e aprovados na re-revisão; aguardando aprovação humana e integração

**Blockers**: Nenhum técnico. Pendente aprovação humana explícita para merge (re-revisão @reviewer 2026-10-29: Approved with minor suggestions).

**Progress**:
- [x] TASK_TRANSITIONS/EXECUTION_TRANSITIONS aplicadas em todo update de status
- [x] Invariantes completed/done documentadas e testadas
- [x] resume reconcilia execução + worktree (blocked/failed/completed)
- [x] retry de failed/blocked com attempt_history
- [x] Falha pós-merge → blocked (nunca completed/done)
- [x] CR-2 resolvido (2026-10-29, TDD): gate FAIL no integrate move completed → blocked com blocked_reason + evento; rota legal via retry
- [x] M-1 resolvido (2026-10-29, TDD): resume copia result (commit/branch); integrate falha limpo sem commit/branch
- [x] M-3 resolvido (2026-10-29, TDD): escopo com fronteira de caminho (src/ não casa srcx/)
- [x] Testes em tests/test_transitions.py e tests/test_runs.py
- [x] Re-revisão (@reviewer) — Approved with minor suggestions (2026-10-29)
- [ ] Aprovação humana e integração

**Notes**: Depende de TASK-003 apenas como precedência de fase; código independente de V2. Suíte: 144 passed, 1 skipped (2026-10-29). Ver TASK-004 em `backlog/backlog.md`.

---

### Task: [TASK-005] Verificar critérios, gates e evidências de revisão/segurança

**Started At**: 2026-10-26

**Assigned To**: @coder

**Current Step**: Critérios de aceitação e acionamento de `@reviewer`/`@security` implementados; aguardando aprovação humana e integração

**Blockers**: Nenhum técnico. Pendente aprovação humana explícita para merge (re-revisão @reviewer 2026-10-29: Approved with minor suggestions).

**Progress**:
- [x] `juicer/evidence.py`: artefatos estruturados de review/security, vinculados a commit/tree, validados pelo core
- [x] `record_review`/`record_security` expostos no orchestrator
- [x] `approval_policy.required_gates` aplicado no `integrate` (review/security)
- [x] Achado crítico → FAIL; artefato ausente/malformado → BLOCKED; artefato de commit antigo → NOT RUN
- [x] M-2 resolvido (2026-10-29): semântica única — ausente/malformado → BLOCKED, stale → NOT RUN (doc/código/testes alinhados)
- [x] M-4 resolvido (2026-10-29, TDD): PASS nunca sobrescreve FAIL (gravado ou derivado de achado crítico) sem `--force`; flag exposta no CLI; EvidenceError herda de JuicerError (exit 2 limpo)
- [x] Testes em `tests/test_evidence.py` (25), `tests/test_integrate.py` e `tests/test_cli.py`
- [x] Critérios de aceitação com `verification` (`check:<id>`, `review`, `security`, `human`) validados no modelo e avaliados no `integrate` com auditoria por critério (2026-10-29, TDD; `tests/test_criteria.py`)
- [x] Acionamento de `@reviewer`/`@security` pelo core via `review-run`/`security-run`: saída JSON estrita, prosa rejeitada, core grava o artefato (2026-10-29, TDD; `tests/test_agent_evidence.py`)
- [x] Fail-fast de severidade/estrutura dos findings (`validate_findings`) em `record_*` e no parser dos agentes
- [x] Re-revisão (@reviewer) — Approved with minor suggestions (2026-10-29)
- [x] Revisão do incremento (critérios + acionamento de agentes) — Changes requested; corrigido; Approved (2026-10-29)
- [ ] Aprovação humana e integração

**Notes**: Trabalho não commitado; ID e histórico preservados. Suíte verde: 193 passed, 1 skipped (2026-10-29). Revisão @reviewer 2026-10-26: Changes requested — achados CR/M/G resolvidos, re-revisão aprovada e incremento revisado/aprovado em 2026-10-29 (ver `backlog/review-findings-TASK-003-005.md`). Smoke real: `@reviewer` executado no V2.1.4 (JSON estrito) e NDJSON real reproduzido até `done`; `security-run` ao vivo não executado (mesmo caminho, coberto por testes). Ver TASK-005 em `backlog/backlog.md`.
