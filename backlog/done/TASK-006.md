# Task: [TASK-006] Registrar aprovação humana vinculada a commit/tree

**Description**: Substituir a aprovação booleana por um registro explícito com aprovador, tarefa, commit, tree hash, data e justificativa. Aplicar a exigência conforme risco e política da tarefa.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-10-29 15:55

**Assigned To**: @coder

**Implementation Summary**:
- `juicer/approval.py`: registro `.juicer/approvals/<task>/approval.json` com `approver`, `task_id`, `commit`, `tree_hash`, `approved_at`, `reason`, `note` e `required_by`; registro único por tarefa com histórico no event log.
- Nunca anônimo: `validate_approver` recusa vazio/anônimo/invisível na escrita **e** na leitura (registro editado à mão → `BLOCKED`).
- Notas/justificativa recusam padrões de segredo (`validate_free_text` fail-fast).
- `juicer approve TASK --approver` no CLI; `ApprovalError(JuicerError)` → exit 2 limpo.
- Exigência disparada por `human_approval_required`, `risk_level=high`, gate `approval` ou critério `verification: human`.
- `integrate --approve` só expressa a intenção de merge: sem registro válido → recusado (`BLOCKED`); registro de commit/tree antigo invalidado (`NOT RUN`) com recuperação por re-aprovação.
- Gate canônico `approval` avalia o registro (não o booleano); aprovação nunca altera gate técnico (FAIL → `blocked`, CR-2 preservado); ordem canônica preservada (aprovação por último).
- Registro de integração audita `approval_required` + resumo `approval` (com triggers vigentes no merge); evento `human_approval_recorded`.
- `.juicer/.gitignore` inclui `approvals/`; README/STATUS atualizados.

**Test Coverage**:
- [x] Unit tests (`tests/test_approval.py`: 26 — campos do registro, anônimos, segredos, alto risco, `--approve` sozinho, invalidação+recuperação, tampering de leitura, ordem canônica, aprovação vs FAIL técnico)
- [x] Integração (`tests/test_integrate.py`, `tests/test_criteria.py` atualizados para o novo fluxo)
- [x] CLI (`tests/test_cli.py`: `--approver` obrigatório, anônimo → exit 2, sem commit → erro limpo, wiring)

**Security Review**:
- [x] Revisado por @reviewer — **Approved with minor suggestions** (nenhum crítico; sem caminho para merge anônimo nem para aprovação mascarar gate técnico)
- [x] Sugestões 🟡 aplicadas (param obrigatório fail-closed, testes de leitura/tampering, mensagem acionável)

**Documentation**:
- [x] README (fluxo + tabela de comandos) e STATUS.md (linha de aprovação: partial → supported)
- [x] Backlog e critérios de aceitação sincronizados

**Notes**: Sugestões adiadas com justificativa para a TASK-007: validação de nomes desconhecidos em `required_gates` e branch-tip vs commit aprovado (ambos pré-existentes). Sem classificação automática de alto risco (a política declara o risco — anotado na revisão como explicitude de uso). Suíte pós-merge: 226 passed, 1 skipped. Commit `a46c92f`.
