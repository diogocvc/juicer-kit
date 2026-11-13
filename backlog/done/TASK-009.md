# Task: [TASK-009] Implementar importação unidirecional do backlog

**Description**: Importar tarefas do backlog Markdown para uma missão com validação de IDs, dependências, prioridades, critérios e escopo; após a importação, `.juicer/` é canônico e não há sincronização bidirecional silenciosa.

**Priority**: P1-High

**Status**: Done

**Completed At**: 2026-11-12

**Assigned To**: @coder

**Implementation Summary**:
- Novo parser/validador read-only `juicer/backlog.py`: aceita apenas tarefas pendentes/em progresso, exige `Description`, `Priority`, `Status`, `Dependencies` e critérios em checkbox; valida IDs, prioridade (`P0`–`P3` com label coerente), dependências duplicadas/inexistentes/auto-referência, ciclos, escopo relativo e cabeçalhos/fences malformados. Blocos em fence (template) são ignorados; `[x]` é preservado como `satisfied`; `Notes` é incorporado à descrição e `Estimated Effort` fica em `origin`.
- `Juicer.import_backlog()` + `juicer import-backlog [--file PATH]`: importa uma única vez para missão `ready` e vazia; fonte confinada ao project root (symlinks resolvidos); dependências já arquivadas em `backlog/done/*.md` são removidas de `depends_on` e registradas em `origin.completed_dependencies`; dependências desconhecidas são rejeitadas.
- Importação unidirecional: o backlog nunca é escrito e a missão nunca é alterada. Registro `.juicer/imports/backlog.json` vincula SHA-256, caminho da fonte e instância da missão; cópia de evidência relativa em `.juicer/evidence/backlog-<sha12>.md`.
- Idempotência e falha segura: mesma fonte → `unchanged` sem reescrever tarefas; fonte alterada, missão substituída, fonte diferente ou registro/tarefas divergentes → erro explícito sem sobrescrever; evidência ausente/adulterada é regenerada e o registro atualizado.
- Journal `pending`/`complete` sob `state_lock("tasks")`: tarefas são gravadas após o journal pendente e o registro só vira completo ao final. Exceção faz rollback de tarefas/evidência/registro; um journal pendente remanescente de crash retoma apenas tarefas ausentes, revalidando o conjunto de IDs. Tarefas extras adicionadas depois da importação são informativas (`extra_task_ids`), não erro.
- `priority` opcional no modelo de task, validação de `origin` e `instance_id` UUID por missão; `.juicer/.gitignore` passa a mesclar `imports/` em projetos já inicializados.

**Test Coverage**:
- [x] `tests/test_backlog_import.py` (48 casos): parse/import válido, bytes do backlog e missão preservados, idempotência byte-level, fonte alterada, missão com tarefas, missão substituída, IDs duplicados/arquivados, dependência desconhecida/satisfeita, prioridade/status/critérios inválidos ou ausentes, template em fence, ciclo/auto-dependência, escopo `..`/Windows, fence não fechado, cabeçalho malformado, fonte fora do root e via symlink, `done` não-UTF-8, registro corrompido, rollback de escrita parcial, retomada de journal pendente, evidência regenerada, tarefas extras, CLI e backlog real com `TASK-001`/`TASK-002` intactos.
- [x] Suíte completa pós-merge: **319 passed** (`uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py`).
- [x] `python3 -m compileall juicer/ -q` OK.

**Review**:
- [x] Revisado por @reviewer em duas rodadas — **Approved** na final.
- [x] Primeira rodada (Changes Requested): H1 (estado parcial irrecuperável), M1/M2 (perda silenciosa por cabeçalho/fence), M4–M6, M8 e M9/AC6. Corrigidos com journal/rollback/retomada, parser estrito, tratamento de registro/evidência e testes adversariais.
- [x] Follow-ups não bloqueantes para backlog futuro: (1) detectar variantes quase-cabeçalho sem `Task:`/colchetes; (2) vincular o journal ao estado de `backlog/done` para retomada determinística após arquivamento; (3) sinalizar journal pendente em `status`/`resume` e evitar `add_tasks` concorrente; (4) revalidar `origin` atribuído em `add_tasks`; (5) auditar regeneração de evidência com evento; (6) aceitar BOM (`utf-8-sig`) e normalizar `source` em POSIX.

**Security Review**:
- [x] Não aplicável (sem autenticação, segredos ou APIs externas novas). Fronteira de caminhos coberta por `resolve()` antes da comparação, rejeição de `..`/paths absolutos e ignoração de symlinks de `backlog/done` que escapem do projeto.

**Documentation**:
- [x] `STATUS.md`: linha de capacidade de importação e contagem **319 passed**.
- [x] `README.md`: comando `juicer import-backlog`.
- [x] Backlog e critérios de aceitação sincronizados; `backlog/in-progress.md` atualizado.

**Notes**: Ver seção 3 e decisões D1/D6 do plano. Commit da feature `073839a` (`feat(core): import backlog Markdown one-way with validation (plan §3)`). Baseline anterior `45cff67`.
