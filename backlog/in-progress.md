# In Progress

## Current Tasks

### Task: [TASK-009] Implementar importação unidirecional do backlog

**Started At**: 2026-11-11

**Assigned To**: @coder

**Current Step**: Implementação (plano §3, D1): parser/validador do backlog Markdown, importação one-way para missão vazia, registro de importação com hash e testes de idempotência/erros.

**Blockers**: Nenhum.

**Progress**:
- [x] Validar schema, IDs únicos, dependências, prioridades, critérios e escopo
- [x] Rejeitar IDs duplicados e dependências inexistentes com erro claro
- [x] Importação unidirecional, sem sobrescrever missão em andamento
- [x] Alterações posteriores no backlog não alteram a missão
- [x] Importação idempotente ou falha segura quando repetida
- [x] `TASK-001` e `TASK-002` permanecem intactas

**Notes**: Baseline: TASK-008 integrada em `9368d41`; suíte 319 passed (271 + 48 novos). Implementação: `juicer/backlog.py`, `Juicer.import_backlog`, CLI `import-backlog`; journal com rollback/retomada; `tests/test_backlog_import.py`.
