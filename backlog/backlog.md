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

### Task: [TASK-003] Definir contrato do harness e validar OpenCode V1

**Description**: Definir o contrato interno mínimo do harness (`discover` e `run`), normalizar o resultado e registrar capabilities comprovadas do OpenCode 1.19.4/V1. Manter o adaptador baseado em CLI, sem SDK nem código V2.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Contrato documenta descoberta, execução, timeout, sessão quando suportada e resultado normalizado.
- [ ] Adaptador V1 reporta apenas capabilities comprovadas; nenhuma compatibilidade V2 é declarada.
- [ ] Testes de contrato usam binário falso e cobrem descoberta, comando, parsing, timeout e falha.
- [ ] Smoke real V1 registra versão, binário, execução, session id e limitações ambientais.
- [ ] `STATUS.md` reflete as capacidades e limitações medidas.
- [ ] `--auto` não é usado por padrão.

**Estimated Effort**: 1,5–2 dev-days

**Notes**: A CLI V1 oferece `run`, `--format json`, `--agent`, `--dir`, `--session`, `--continue`, `--attach` e `serve`; o adaptador atual usa apenas parte disso. Ver `docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md` seção 11.

---

### Task: [TASK-004] Aplicar transições e reconciliar retomada de estado

**Description**: Fazer todas as atualizações de tarefa e execução passarem pela validação de transições, preservar revisão e histórico e reconciliar `in_progress` com execuções/worktrees reais no `resume`.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003

**Acceptance Criteria**:
- [ ] Toda mudança de status de tarefa usa `TASK_TRANSITIONS`; transições inválidas falham com teste.
- [ ] Toda mudança de status de execução usa `EXECUTION_TRANSITIONS`.
- [ ] `completed` e `done` têm invariantes documentadas e testadas.
- [ ] `resume` não marca `in_progress` como `failed` sem reconciliar execução e worktree.
- [ ] Revision fence e locks impedem atualização perdida em concorrência.
- [ ] `blocked` pode ser retomado explicitamente e o histórico anterior é preservado.

**Estimated Effort**: 2–2,5 dev-days

**Notes**: Falha pós-merge deve terminar em `blocked`, nunca em `completed`. Ver seções 4 e 10 do plano.

---

### Task: [TASK-005] Verificar critérios, gates e evidências de revisão/segurança

**Description**: Tornar critérios de aceitação e `required_gates` efetivos, vincular evidências ao commit/tree corretos e exigir revisão e segurança quando aplicável, usando os agentes existentes.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003, TASK-004

**Acceptance Criteria**:
- [ ] Critérios declaram verificação (`check:<id>`, `review`, `security` ou `human`) e bloqueiam quando não há evidência válida.
- [ ] `approval_policy.required_gates` é aplicado; `NOT RUN` nunca permite merge.
- [ ] Revisão é obrigatória para mudanças de código e ocorre antes do merge.
- [ ] Segurança é obrigatória para tarefas de alto risco e não é substituída por revisão.
- [ ] Artefatos de revisão/segurança são estruturados, vinculados a commit/tree e validados pelo core.
- [ ] Achado crítico resulta em `FAIL`; artefato ausente ou malformado resulta em `BLOCKED`.
- [ ] O core aciona `@reviewer` e `@security` existentes, sem criar agentes novos.

**Estimated Effort**: 3–4 dev-days

**Notes**: Texto afirmativo do agente não é evidência. Ver seções 5, 6 e 9 do plano.

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

### Task: [TASK-007] Reforçar isolamento, escopo e caminhos protegidos

**Description**: Validar o diff completo da execução, detectar commits e arquivos não rastreados criados pelo agente, bloquear caminhos protegidos e impedir alterações fora do escopo.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003

**Acceptance Criteria**:
- [ ] Execução registra `base_commit`, `head_commit`, `tree_hash` e branch.
- [ ] Escopo considera arquivos rastreados, não rastreados e commits feitos pelo agente.
- [ ] `.juicer/`, `.git/`, segredos e caminhos declarados pela política são protegidos.
- [ ] Commit feito pelo agente é detectado e falha por padrão, salvo política explícita.
- [ ] Árvore de destino suja bloqueia integração sem sobrescrever mudanças pré-existentes.
- [ ] Worktree e branch não são removidos antes de registrar evidência.
- [ ] Concorrência permanece serial por padrão até testes comprovarem isolamento.

**Estimated Effort**: 2–3 dev-days

**Notes**: Ver seção 8 do plano. A validação atual de escopo cobre apenas parte do diff.

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

### Task: [TASK-010] Alinhar agentes, comandos e documentação

**Description**: Alinhar a ordem dos gates e os contratos de `@orchestrator`, `@reviewer`, `@security` e `@tester` com o core; corrigir `AGENTS.md`, README, STATUS e referências ao plano, sem criar agentes.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: TASK-005, TASK-006

**Acceptance Criteria**:
- [ ] `AGENTS.md` declara 4.0, a ordem canônica e a separação backlog/`.juicer`.
- [ ] `@orchestrator` não promete gate que o core não aplica.
- [ ] `@reviewer` continua sem permissão de edição e é acionado antes do merge.
- [ ] `@security` é acionado por risco e não substitui revisão.
- [ ] README e STATUS apontam para o plano e distinguem capacidade validada de lacuna planejada.
- [ ] Comandos `/review` e `/test` permanecem compatíveis com o fluxo.

**Estimated Effort**: 1–1,5 dev-day

**Notes**: Ver seção 12 do plano. Não alterar silenciosamente decisões aprovadas.

---

### Task: [TASK-011] Validar fluxo E2E V1 e aceitação do MVP

**Description**: Validar o fluxo completo em repositório temporário com OpenCode 1.19.4 real e cobrir os caminhos negativos que hoje poderiam produzir conclusão indevida.

**Priority**: P0-Critical

**Status**: Pending

**Dependencies**: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010

**Acceptance Criteria**:
- [ ] E2E cobre missão, importação, execução, checks, revisão, segurança, aprovação, merge e pós-merge.
- [ ] Gate ausente, revisão ausente, segurança exigida e não executada e aprovação ausente bloqueiam.
- [ ] Alteração fora de escopo, commit do agente e path protegido bloqueiam.
- [ ] Falha pós-merge não deixa tarefa `completed` ou `done`.
- [ ] Interrupção, retry e `resume` são validados sem perda de evidência.
- [ ] Suíte completa passa e o smoke real V1 é registrado.
- [ ] Documentação final não declara compatibilidade V2.

**Estimated Effort**: 2–3 dev-days

**Notes**: Ver Apêndice A do plano. Este é o gate de aceitação do MVP, não de release/deploy.
