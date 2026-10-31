# In Progress

## Current Tasks

### Task: [TASK-006] Registrar aprovação humana vinculada a commit/tree

**Started At**: 2026-10-29 15:20

**Assigned To**: @coder

**Current Step**: Implementado, revisado (Approved with minor suggestions) e com suíte verde; aguardando aprovação humana para commit/integração

**Blockers**: Nenhum técnico. Pendente aprovação explícita para commit/merge.

**Progress**:
- [x] `juicer/approval.py`: registro `.juicer/approvals/<task>/approval.json` com aprovador, task_id, commit, tree_hash, data, reason/note, required_by
- [x] Aprovador anônimo/vazio/invisível recusado na escrita **e** na leitura (`ApprovalError`, CLI exit 2)
- [x] Notas/reason com padrão de segredo recusados (`validate_free_text`)
- [x] `juicer approve TASK --approver` no CLI (`--approver` obrigatório)
- [x] Exigência automática: `human_approval_required`, `risk_level=high`, gate `approval` ou critério `human`
- [x] `integrate --approve` sem registro válido recusado (BLOCKED/NOT RUN); registro para commit/tree antigo invalidado (`NOT RUN`) com recuperação por re-aprovação
- [x] Gate `approval` avalia o registro (não mais o booleano); ordem canônica preservada (aprovação por último)
- [x] Aprovação não altera gates técnicos (FAIL técnico + aprovação → `blocked`, sem merge; CR-2 preservado)
- [x] Critério `human` avaliado pelo registro; auditoria `approval_required`/`approval` no registro de integração + evento `human_approval_recorded`
- [x] Testes de caminho de leitura/tampering (JSON malformado, task_id divergente, aprovador anônimo editado à mão)
- [x] `.juicer/.gitignore` inclui `approvals/`
- [x] Revisão @reviewer — Approved with minor suggestions; sugestões 🟡 aplicadas
- [ ] Aprovação humana para commit/integração

**Notes**: Trabalho não commitado (HEAD `c8d94e3`+... branch release/4.0.0; TASK-003/004/005 já integrados em `9c6b9d0`/`c8d94e3`/`2c9cf6c`). ID e histórico preservados. Suíte verde: 226 passed, 1 skipped (2026-10-29). Sugestões adiadas com justificativa: nomes desconhecidos em `required_gates` e branch-tip vs commit aprovado → escopo da TASK-007. Ver TASK-006 em `backlog/backlog.md`.
