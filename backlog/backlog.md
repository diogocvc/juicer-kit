# Backlog

## Task Template

```md
### Task: [TASK-XXX] [Title]

**Description**: [What needs to be done]

**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]

**Status**: [Pending | In Progress | Blocked | Done]

**Dependencies**: [TASK-XXX, TASK-YYY]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Estimated Effort**: [S/M/L or hours]

**Notes**: [Any additional context]
```

## Pending Tasks

### Task: [TASK-001] Create user authentication with JWT

**Description**: Implement JWT-based authentication with access and refresh tokens.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: None

**Acceptance Criteria**:
- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Refresh token flow works correctly
- [ ] Protected routes require valid token
- [ ] Tests cover all scenarios

**Estimated Effort**: L

**Notes**: Use bcrypt for password hashing, store tokens in httpOnly cookies.

---

### Task: [TASK-002] Create user profile API

**Description**: Build REST API for user profile management.

**Priority**: P2-Medium

**Status**: Pending

**Dependencies**: TASK-001

**Acceptance Criteria**:
- [ ] GET /api/users/:id returns profile
- [ ] PUT /api/users/:id updates profile
- [ ] DELETE /api/users/:id deletes account
- [ ] Authorization checks (user can only edit own profile)
- [ ] Tests cover all scenarios

**Estimated Effort**: M

**Notes**: Include validation with Zod.

---

### Task: [TASK-003] Definir contrato do harness e validar OpenCode V2

**Description**: Definir o contrato interno mínimo do harness (`discover` e `run`), normalizar o resultado e registrar capabilities comprovadas do OpenCode 2.0/V2. O alvo do MVP é a CLI V2 (D5/D9 do plano); o trabalho V1 já realizado (contrato, testes de contrato, estrutura do adaptador, STATUS parcial) é preservado como base e reaproveitado apenas onde justificado, sem manter integração V1 paralela. Provisionar/detectar o binário V2 é passo bloqueante antes de qualquer declaração de compatibilidade.

**Priority**: P0-Critical

**Status**: In Progress

**Dependencies**: None

**Acceptance Criteria**:
- [x] Binário OpenCode 2.0/V2 provisionado e detectado (`OPENCODE_BIN`, PATH ou instalador oficial); `discover` distingue V2 de V1 e não reporta suporte V2 sem binário V2.
- [x] Contrato documenta descoberta, execução, timeout, sessão quando suportada e resultado normalizado (base V1 preservada em `docs/HARNESS_CONTRACT.md`, ajustada ao alvo V2).
- [x] Adaptador alinhado à CLI V2 real; reporta apenas capabilities medidas no binário V2; nenhuma compatibilidade V1 paralela é mantida.
- [x] Testes de contrato usam binário falso e cobrem descoberta, comando, parsing, timeout e falha (reaproveitar os existentes quando compatíveis).
- [x] Smoke real V2 registra versão, binário, execução, session id e limitações ambientais.
- [x] Política de permissões V2 (quando usada) não substitui gates do core; `--auto` não é usado por padrão.
- [x] `STATUS.md` reflete capacidades **medidas** no V2 e separa o que permanece apenas documental ou bloqueado.

**Estimated Effort**: 2–3,5 dev-days (executado no limite inferior; revisar pós-integração)

**Notes**: Executado em 2026-10-26: binário `opencode v2.1.4` em `~/.opencode/bin`; `discover` status=supported, `v2=true`; smoke real `SMOKE-OK-7Q2` com `--standalone` e sem `--dir` (V2 não possui `--dir`; workspace via CWD). Suíte 83 passed + 1 smoke. Trabalho V1 preservado e adaptado (contrato, parsing, testes). CR-1 (regex V2) resolvido 2026-10-29. Status permanece **In Progress** até aprovação humana e integração (workflow do kit); critérios técnicos acima cumpridos no working tree e re-revisão @reviewer aprovada em 2026-10-29 (Approved with minor suggestions). Ver `docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md` seções 11 e D.

---

### Task: [TASK-004] Aplicar transições e reconciliar retomada de estado

**Description**: Fazer todas as atualizações de tarefa e execução passarem pela validação de transições, preservar revisão e histórico e reconciliar `in_progress` com execuções/worktrees reais no `resume`.

**Priority**: P0-Critical

**Status**: In Progress

**Dependencies**: TASK-003

**Acceptance Criteria**:
- [x] Toda mudança de status de tarefa usa `TASK_TRANSITIONS`; transições inválidas falham com teste.
- [x] Toda mudança de status de execução usa `EXECUTION_TRANSITIONS`.
- [x] `completed` e `done` têm invariantes documentadas e testadas. (CR-2 resolvido 2026-10-29: gate FAIL no `integrate` move `completed → blocked` com `blocked_reason`; rota legal via `retry_task`)
- [x] `resume` não marca `in_progress` como `failed` sem reconciliar execução e worktree. (M-1 resolvido 2026-10-29: resume copia `result` commit/branch; `integrate` falha limpo sem commit/branch)
- [x] Revision fence e locks impedem atualização perdida em concorrência.
- [x] `blocked` pode ser retomado explicitamente e o histórico anterior é preservado.
- [x] Escopo com fronteira de caminho (M-3 resolvido 2026-10-29: `src/` não casa `srcx/evil.py`).

**Estimated Effort**: 2–2,5 dev-days (executado; achados CR-2/M-1/M-3 resolvidos 2026-10-29; re-revisão aprovada; pendente aprovação humana e integração)

**Notes**: Implementado no working tree: `check_transition` em `_update_task`/`_update_execution`; `resume` reconcilia com execução e worktree (succeeded→completed com `result` copiado; interrompido+worktree→blocked; sem worktree→failed); `retry_task` aceita failed/blocked com `attempt_history`; falha pós-merge move para `blocked`; gate FAIL pré-merge move `completed → blocked` (CR-2); `_check_scope` com fronteira de caminho (M-3). Falha pós-merge deve terminar em `blocked`, nunca em `completed`. Ver seções 4 e 10 do plano. Revisão @reviewer 2026-10-26: Changes requested — CR-2, M-1, M-3 e G-1; todos resolvidos 2026-10-29 (ver `backlog/review-findings-TASK-003-005.md`); re-revisão 2026-10-29: Approved with minor suggestions; pendente aprovação humana antes de integração.

---

### Task: [TASK-005] Verificar critérios, gates e evidências de revisão/segurança

**Description**: Tornar critérios de aceitação e `required_gates` efetivos, vincular evidências ao commit/tree corretos e exigir revisão e segurança quando aplicável, usando os agentes existentes.

**Priority**: P0-Critical

**Status**: In Progress

**Dependencies**: TASK-003, TASK-004

**Acceptance Criteria**:
- [x] Critérios declaram verificação (`check:<id>`, `review`, `security` ou `human`) e bloqueiam quando não há evidência válida. (implementado 2026-10-29: `verification` validado no modelo e avaliado no `integrate` com auditoria por critério; `tests/test_criteria.py`)
- [x] `approval_policy.required_gates` é aplicado; `NOT RUN` nunca permite merge.
- [x] Revisão é obrigatória para mudanças de código e ocorre antes do merge. (quando declarada em `required_gates` ou em critério `verification: review`)
- [x] Segurança é obrigatória para tarefas de alto risco e não é substituída por revisão. (`risk_level=high`, `required_gates` ou critério `verification: security`)
- [x] Artefatos de revisão/segurança são estruturados, vinculados a commit/tree e validados pelo core.
- [x] Achado crítico resulta em `FAIL`; artefato ausente ou malformado resulta em `BLOCKED`. (M-2 resolvido 2026-10-29: semântica única ausente/malformado→BLOCKED, stale→NOT RUN; M-4: FAIL nunca sobrescrito por PASS sem `--force`)
- [x] O core aciona `@reviewer` e `@security` existentes, sem criar agentes novos. (implementado 2026-10-29: `juicer review-run`/`security-run`; agente responde um bloco JSON estrito, core valida e grava o artefato com commit/tree próprios; prosa é rejeitada; `tests/test_agent_evidence.py`)

**Estimated Effort**: 3–4 dev-days (executado; smoke real de `review-run` no V2 validado; `security-run` ao vivo coberto por testes)

**Notes**: Texto afirmativo do agente não é evidência. Ver seções 5, 6 e 9 do plano. Trabalho no working tree (não commitado): `juicer/evidence.py` (artefatos estruturados, `validate_findings`, proteção FAIL→PASS com `--force`, incl. FAIL derivado), `record_review`/`record_security` e `run_review`/`run_security` no orchestrator, avaliação de critérios no `integrate` com auditoria por critério, `required_gates` aplicado, CLI (`review`/`security`/`review-run`/`security-run`), semântica M-2 alinhada. Testes em `tests/test_evidence.py`, `tests/test_criteria.py`, `tests/test_agent_evidence.py`, `tests/test_integrate.py` e `tests/test_cli.py`. Achados M-2/M-4/G-1 resolvidos 2026-10-29; re-revisão @reviewer aprovada (Approved with minor suggestions); suíte 193 passed, 1 skipped. Smoke real: `@reviewer` executado no V2.1.4 (JSON estrito) e NDJSON real reproduzido até `done`; `security-run` ao vivo não executado (mesmo caminho, coberto por testes; 2ª chamada bloqueada por quota HTTP 402).

---

### Task: [TASK-006] Registrar aprovação humana vinculada a commit/tree

**Description**: Substituir a aprovação booleana por um registro explícito com aprovador, tarefa, commit, tree hash, data e justificativa. Aplicar a exigência conforme risco e política da tarefa.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-005

**Acceptance Criteria**:
- [ ] Política de alto risco exige aprovação humana antes do merge.
- [ ] Registro contém aprovador, `task_id`, commit, tree hash, data e nota/justificativa.
- [ ] Aprovação é válida apenas para o commit/tree registrados e é invalidada por novo commit.
- [ ] Aprovação humana não altera o resultado de gates técnicos.
- [ ] `--approve` sozinho não permite aprovação anônima ou sem vínculo.
- [ ] Notas não armazenam segredos.

**Estimated Effort**: 1–1,5 dev-day

**Notes**: Ver seção 7 do plano. A aprovação pode ser registrada pelo CLI, sem novo agente.

---

### Task: [TASK-007] Reforçar isolamento, escopo, caminhos protegidos e fronteira de permissões V2

**Description**: Validar o diff completo da execução, detectar commits e arquivos não rastreados criados pelo agente, bloquear caminhos protegidos e impedir alterações fora do escopo. Distinguir explicitamente permissões do OpenCode V2 (allow/ask/deny no config) dos gates, escopo e validações do core: permissões do harness são barreira adicional, nunca substituto da verificação interna.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003

**Acceptance Criteria**:
- [ ] Execução registra `base_commit`, `head_commit`, `tree_hash` e branch.
- [ ] Escopo considera arquivos rastreados, não rastreados e commits feitos pelo agente.
- [ ] `.juicer/`, `.git/`, segredos e caminhos declarados pela política são protegidos **no core**, independentemente de política de permissões do OpenCode.
- [ ] Commit feito pelo agente é detectado e falha por padrão, salvo política explícita.
- [ ] Árvore de destino suja bloqueia integração sem sobrescrever mudanças pré-existentes.
- [ ] Worktree e branch não são removidos antes de registrar evidência.
- [ ] Concorrência permanece serial por padrão até testes comprovarem isolamento.
- [ ] Política de permissões V2 (quando aplicada) não é tratada como evidência de gates nem reduz os checks do core; testes cobrem a fronteira.

**Estimated Effort**: 2–3 dev-days

**Notes**: Ver seção 8 do plano e decisão D8. A validação atual de escopo cobre apenas parte do diff. Não depender de permissões do harness para garantias de isolamento.

---

### Task: [TASK-008] Corrigir retry, conflitos, pós-merge e recuperação

**Description**: Preservar evidências em retry, permitir retomada de `blocked`, abortar conflitos sem merge parcial, mover falha pós-merge para `blocked` e reconciliar estado após interrupção.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: TASK-004, TASK-007

**Acceptance Criteria**:
- [ ] Retry cria nova execução sem apagar a anterior e evita colisão de branch/worktree.
- [ ] `blocked` e `failed` são retomáveis conforme política; `done` não é.
- [ ] `resume` reconcilia execuções interrompidas e não inicia duplicadamente.
- [ ] Falha pós-merge move a tarefa para `blocked` e registra commit integrado.
- [ ] Conflito de merge aborta sem merge parcial e exige intervenção explícita.
- [ ] Checkpoint registra próximo passo e evidência para auditoria.

**Estimated Effort**: 2–3 dev-days

**Notes**: Ver seção 10 do plano. O fluxo atual pode deixar `completed` após falha pós-merge.

---

### Task: [TASK-009] Implementar importação unidirecional do backlog

**Description**: Importar tarefas do backlog Markdown para uma missão com validação de IDs, dependências, prioridades, critérios e escopo; após a importação, `.juicer/` é canônico e não há sincronização bidirecional silenciosa.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: TASK-004

**Acceptance Criteria**:
- [ ] Importação valida schema, IDs únicos, dependências, prioridades e critérios.
- [ ] IDs duplicados ou dependências inexistentes são rejeitados com erro claro.
- [ ] Importação é unidirecional e não sobrescreve missão em andamento.
- [ ] Alterações posteriores no backlog não alteram automaticamente a missão.
- [ ] Importação é idempotente ou falha de forma segura quando repetida.
- [ ] `TASK-001` e `TASK-002` permanecem intactas.

**Estimated Effort**: 1,5–2 dev-days

**Notes**: Ver seção 3 do plano. O backlog é fonte de planejamento; `.juicer/` é fonte operacional após importar.

---

### Task: [TASK-010] Alinhar agentes, comandos e documentação ao alvo V2

**Description**: Alinhar a ordem dos gates e os contratos de `@orchestrator`, `@reviewer`, `@security` e `@tester` com o core; corrigir `AGENTS.md`, README, STATUS e referências ao plano para o alvo OpenCode 2.0/V2, sem criar agentes e sem apagar histórico de medições já realizadas.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: TASK-005, TASK-006

**Acceptance Criteria**:
- [ ] `AGENTS.md` declara 4.0, a ordem canônica e a separação backlog/`.juicer`.
- [ ] `@orchestrator` não promete gate que o core não aplica.
- [ ] `@reviewer` continua sem permissão de edição e é acionado antes do merge.
- [ ] `@security` é acionado por risco e não substitui revisão.
- [ ] README e STATUS apontam para o plano, distinguem capacidade **medida** de lacuna planejada e refletem o alvo V2 sem anunciar compatibilidade não comprovada.
- [ ] `docs/HARNESS_CONTRACT.md` e comentários do adaptador estão alinhados ao alvo V2; referências V1 remanescentes são atualizadas ou marcadas como histórico.
- [ ] Comandos `/review` e `/test` permanecem compatíveis com o fluxo.
- [ ] Permissões V2 (quando citadas) não são apresentadas como substitutas dos gates do core.

**Estimated Effort**: 1–1,5 dev-day

**Notes**: Ver seção 12 do plano. Depende dos gates de TASK-005/006 e da validação de capabilities da TASK-003 para não prometer o que não foi medido. Não alterar silenciosamente decisões aprovadas.

---

### Task: [TASK-011] Validar fluxo E2E V2 e aceitação do MVP

**Description**: Validar o fluxo completo em repositório temporário com OpenCode 2.0/V2 real (binário medido, não apenas documental) e cobrir os caminhos negativos que hoje poderiam produzir conclusão indevida.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010

**Acceptance Criteria**:
- [ ] E2E cobre missão, importação, execução, checks, revisão, segurança, aprovação, merge e pós-merge.
- [ ] Gate ausente, revisão ausente, segurança exigida e não executada e aprovação ausente bloqueiam.
- [ ] Alteração fora de escopo, commit do agente e path protegido bloqueiam.
- [ ] Falha pós-merge não deixa tarefa `completed` ou `done`.
- [ ] Interrupção, retry e `resume` são validados sem perda de evidência.
- [ ] Suíte completa passa e o smoke real **V2** é registrado (versão e capabilities medidas).
- [ ] Documentação final não declara compatibilidade V1 nem capacidade V2 não medida.

**Estimated Effort**: 2,5–3,5 dev-days

**Notes**: Ver Apêndice A do plano. Gate de aceitação do MVP V2, não de release/deploy. Bloqueado na prática até a TASK-003 provisionar e validar o binário V2.
