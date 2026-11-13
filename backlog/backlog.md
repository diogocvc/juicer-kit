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

### Task: [TASK-011] Validar fluxo E2E V2 e aceitação do MVP

**Description**: Validar o fluxo completo em repositório temporário com OpenCode 2.0/V2 real (binário medido, não apenas documental) e cobrir os caminhos negativos que hoje poderiam produzir conclusão indevida.

**Priority**: P0-Critical

**Status**: In Progress

**Dependencies**: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010

**Acceptance Criteria**:
- [x] E2E cobre missão, importação, execução, checks, revisão, segurança, aprovação, merge e pós-merge.
- [x] Gate ausente, revisão ausente, segurança exigida e não executada e aprovação ausente bloqueiam.
- [x] Alteração fora de escopo, commit do agente e path protegido bloqueiam.
- [x] Falha pós-merge não deixa tarefa `completed` ou `done`.
- [x] Interrupção, retry e `resume` são validados sem perda de evidência.
- [x] Suíte completa passa e o smoke real **V2** é registrado (versão e capabilities medidas).
- [x] Documentação final não declara compatibilidade V1 nem capacidade V2 não medida.

**Estimated Effort**: 2,5–3,5 dev-days

**Notes**: Ver Apêndice A do plano. Gate de aceitação do MVP V2, não de release/deploy. Evidência: `tests/test_e2e_v2.py` (8 testes determinísticos com adaptador V2 real e binário scriptado), smoke opt-in de capabilities em `opencode v2.2.7`, e execução real de `run`+checks+merge+pós-merge com modelo free. Review/security ao vivo ficaram limitados por quota (HTTP 402/429); aprovação é local e coberta pelo E2E. O caminho completo é coberto pelo E2E determinístico. A validação revelou e corrigiu a âncora de workspace por `PWD`.
