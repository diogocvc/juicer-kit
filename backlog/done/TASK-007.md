# Task: [TASK-007] Reforçar isolamento, escopo, caminhos protegidos e fronteira de permissões V2

**Description**: Validar o diff completo da execução, detectar commits e arquivos não rastreados criados pelo agente, bloquear caminhos protegidos e impedir alterações fora do escopo. Distinguir explicitamente permissões do OpenCode V2 (allow/ask/deny no config) dos gates, escopo e validações do core: permissões do harness são barreira adicional, nunca substituto da verificação interna.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-11-10

**Assigned To**: @coder

**Implementation Summary**:
- `juicer/scope.py`: política de caminhos protegidos (`.juicer/`, `.git/`, segredos clássicos, `.aws/credentials`, `.ssh`) e opt-in explícito de commits do agente (`allow_agent_commits` na tarefa/política; config só com `true` literal). Templates `.env.example`/`.sample`/`.template`/`.dist` são seguros apenas contra os globs genéricos de segredo.
- `run_task` registra `base_commit`, `agent_head_commit`, `head_commit`, `tree_hash`, branch e `touched_files` em `result` e `execution.workspace`; `no_changes` é explícito.
- Escopo avaliado sobre o diff completo contra `base_commit` (rastreados, staged, não rastreados) **e** todo o histórico `base..head` (`git log --no-renames`), cobrindo commits intermediários e renames. `--no-renames` no diff evita que um rename esconda o caminho de origem.
- Enforcement antes do commit: stage → valida índice + histórico → `commit_index`; no pós-commit revalida o histórico e desfaz o commit do coordenador (`reset --soft`) se algo escapou. Commit surgido abaixo do commit do coordenador é tratado como commit do agente.
- Commit do agente falha por padrão (detectado por `agent_head != base` e pela cadeia de parentesco no commit do coordenador).
- Worktree corrompido/removido falha fechado (`is_worktree_root`: o toplevel precisa ser exatamente o worktree, sem fallback silencioso para o repositório pai); falha de setup do worktree encerra tarefa/execução como `failed`, sem `running` pendurado.
- Tentativa anterior preservada antes de remover worktree/branch: HEAD/tree, dirty, diff stat, arquivos, patch com untracked (`git add -N`) e ref durável `refs/juicer/attempts/<task>/<id>`; nomes com UUID.
- Integração: exige `base_commit` resolvível, ancestral de `commit` e coerente com `execution.workspace`; `branch_tip == result.commit`; recheca protegidos/escopo sobre `changed_in_range ∪ changed_between`; rejeita gates desconhecidos; merge fixado no commit evidenciado.
- Concorrência permanece serial por padrão (`max_jobs=1`); paralelismo só com `--jobs` explícito.
- Limitação documentada: escrita fora do worktree (ex.: direto em `.juicer/`) depende da barreira de permissões/sandbox do harness; o core enxerga o diff/branch do worktree. Patch preservado pode conter segredo escrito pelo agente — artefato sensível.

**Test Coverage**:
- [x] Unit/integration (`tests/test_isolation.py`: 34 casos) — metadados da execução, escopo com untracked/commits/renames, protegidos (parametrizado, incluindo `.aws/credentials` aninhado), template seguro, política declarada, commit do agente (padrão e opt-in), histórico add-then-delete, renomeação, escopo por caminho exato, árvore suja, preservação com patch/ref, serial por padrão, fronteira de permissões V2, gates desconhecidos, branch movida, base inválida/ausente/igual ao commit, `no_changes` adulterado, worktree destruído/stale.
- [x] Suíte completa pós-merge: **260 passed**, 1 skipped (smoke opt-in).

**Security Review**:
- [x] Revisado por @reviewer em três rodadas — **Approved** na final.
- [x] Críticos corrigidos: vazamento por commit intermediário (add-then-delete) e recheck de protegidos fail-open sem `base_commit`.
- [x] Maiores corrigidos: basename em escopo, renames, TOCTOU, template seguro sobre política, evidência de tentativa anterior, commit antes do enforcement, ancestralidade de `base_commit`.

**Documentation**:
- [x] `STATUS.md`: matriz de capacidades e limitações ambientais (escrita fora do worktree; evidência sensível).
- [x] Backlog e critérios de aceitação sincronizados; `backlog/in-progress.md` atualizado.

**Notes**: Revisão final aprovada sem findings críticos/médios. Commit `3f8ea8d` (`feat(core): enforce isolation, scope and protected paths (plan §8)`). Ver seção 8 do plano e decisão D8. Não depender de permissões do harness para garantias de isolamento.
