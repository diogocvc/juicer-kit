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
