# Task: [TASK-008] Corrigir retry, conflitos, pós-merge e recuperação

**Description**: Preservar evidências em retry, permitir retomada de `blocked`, abortar conflitos sem merge parcial, mover falha pós-merge para `blocked` e reconciliar estado após interrupção.

**Priority**: P1-High

**Status**: Done

**Completed At**: 2026-11-11

**Assigned To**: @coder

**Implementation Summary**:
- Retry (`retry_task`) permitido apenas para `failed`/`blocked`; `done` é terminal. Cada retry cria nova execução, registra `attempt_history` (execução, branch, worktree, commit, base, merged commit, motivo do bloqueio) e limpa `current_execution_id`.
- Numeração de tentativas monotônica e livre de colisão (`_next_attempt` + `_attempt_names`): considera `attempt_count`, tentativas registradas no histórico e branches/worktrees existentes. A partir da tentativa 2 usa `juicer/<task>-attempt-<n>` e `.juicer/worktrees/<task>-attempt-<n>` (dash evita conflito ref arquivo/diretório). Uma execução interrompida seguida de `resume` + retry não reutiliza a tentativa anterior.
- Preservação antes de remover: `_preserve_prior_attempt` grava HEAD/tree, dirty, diff stat, arquivos, patch com untracked e âncora durável `refs/juicer/attempts/<task>/<id>`. Âncora usa branch tip ou HEAD do worktree; se `update_ref` falhar, registra `preserved_ref_error` e emite `attempt_preservation_degraded` (nunca silencioso). Retries não apagam a branch anterior.
- `resume` reconcilia cada tarefa `in_progress` a partir da execução/worktree registrados (com fallback ao caminho canônico legado): execução terminal alinha a tarefa (`succeeded` → `completed`, demais → `failed`); execução `claimed`/`running` é cancelada com motivo; worktree existente → `blocked`, ausente → `failed`. Registra `attempt_history`, limpa vínculo inválido e grava relatório `.juicer/evidence/resume-*.json` (`artifact_ref`). Idempotente e sem iniciar execução duplicada. Execução de outra tarefa é ignorada (`resume_execution_mismatch`) e não contamina resultado/histórico.
- Conflito de merge: `merge --abort`, tarefa → `blocked` com commit/branch/motivo e evento com `partial_merge`. Se o abort falhar (`MERGE_HEAD` presente), a mensagem/estado dizem explicitamente que o repositório continua em merge e exigem `git merge --abort`/resolução. Um merge já em andamento não é abortado por engano.
- Falha pós-merge: tarefa → `blocked` (nunca `completed`/`done`), registra `result.merged_commit` e `post_merge_gate`; caminho de sucesso também grava `merged_commit`, `post_merge_gate` e `integrated_at` no `result`, de modo que checkpoints de tarefas `done` carreguem o commit integrado.
- Checkpoint por tarefa: `status`, `revision`, `current_execution_id`, `next_step` (`run`/`resume`/`retry`/`integrate`/`none`), `blocked_reason` e evidência (execução, branch, commit, tree, artefato, merged commit). `next_action` global reporta `resume in-progress tasks: ...`; nomes de checkpoint incluem sufixo aleatório para não sobrescrever artefatos no mesmo segundo.
- Logs de checks separados por fase (`<check>-<pre_merge|post_merge>.log`), evitando que o pós-merge sobrescreva a evidência do pré-merge. Resultados/eventos carregam o número da tentativa.

**Test Coverage**:
- [x] `tests/test_recovery.py` (11 casos): retry com nova branch/worktree e tentativa anterior auditável; conflito com `merge --abort` e retry explícito; falha de abort reportada como "still mid-merge"; `resume` com evidência/idempotência/workspace da execução; resume→retry sem reutilizar tentativa; execução de outra tarefa ignorada; falha de preservação registrada; falha pós-merge com `merged_commit` e correção→`done`; logs por fase; checkpoint com próximo passo/evidência e nomes únicos.
- [x] Suítes existentes de transições, integração, preservação, isolamento e estado continuam verdes.
- [x] Suíte completa pós-merge: **271 passed** (`uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py`).

**Review**:
- [x] Revisado por @reviewer em três rodadas — **Approved** na final.
- [x] Correções solicitadas: numeração de tentativas após interrupção, preservação fail-closed, isolamento de execução de outra tarefa no `resume`, `merged_commit` no sucesso, logs por fase e `next_action` para `in_progress`.
- [x] Sem findings críticos em aberto. Follow-ups não bloqueantes registrados: unificar tratamento de erro de `resume` entre align/recover e normalizar `attempt_count` × número da tentativa após resume.

**Security Review**:
- [x] Não aplicável (sem autenticação, segredos ou APIs externas novas). Integridade de estado/evidência coberta pelo @reviewer; patches preservados continuam documentados como artefatos sensíveis.

**Documentation**:
- [x] `STATUS.md`: matriz de capacidades, contagem de testes e limitações atualizadas.
- [x] `README.md`/CLI: `juicer retry` descreve `failed` ou `blocked`.
- [x] Backlog e critérios de aceitação sincronizados; `backlog/in-progress.md` atualizado.

**Notes**: Ver seção 10 do plano. Commit da feature `9368d41` (`feat(core): harden retry, resume, conflicts and post-merge recovery (plan §10)`). Baseline anterior `5b8443e`.
