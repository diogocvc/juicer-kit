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
