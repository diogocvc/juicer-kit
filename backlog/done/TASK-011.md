# Task: [TASK-011] Validar fluxo E2E V2 e aceitação do MVP

**Description**: Validar o fluxo completo em repositório temporário com OpenCode 2.0/V2 real (binário medido, não apenas documental) e cobrir os caminhos negativos que hoje poderiam produzir conclusão indevida.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-11-13

**Assigned To**: @tester

**Implementation Summary**:
- `tests/test_e2e_v2.py` (8 testes) exercita o core real e o adaptador V2 real contra um binário V2 scriptado que fala o NDJSON medido, sem chamar provider:
  - fluxo completo: missão → importação de backlog → execução → checks → review → security → aprovação → merge → pós-merge;
  - gate de verificação ausente/NOT RUN, review ausente, security exigida e não executada, e aprovação ausente bloqueiam;
  - alteração fora de escopo, commit do agente e path protegido falham a tarefa;
  - falha pós-merge deixa `blocked`, nunca `completed`/`done`;
  - interrupção + retry + `resume` preservam worktree, execução anterior e artefatos `preserved-*`.
- A validação real expôs que o OpenCode V2 resolve o projeto pelo `PWD`, não apenas pelo `cwd` do subprocesso. Sem o fix, o agente executava no repositório chamador em vez do worktree. `juicer/harness/opencode.py` agora resolve o workspace e fixa `cwd` + `PWD`; `tests/test_opencode_adapter.py` cobre a regressão de forma fail-closed.
- O `cwd` é normalizado com `Path.resolve()` e precisa ser diretório; caso contrário a execução retorna `BLOCKED`.
- `tests/test_opencode_smoke.py` ganhou probe opt-in de capabilities sem chamada de modelo. Medição: `opencode v2.2.7`, `v2=true`, `run_json=true`, `agent_flag=true`, `standalone_flag=true`, `dir_flag=false`, `events=jsonl-stream`.
- Execução real de `run` + checks + `integrate` + pós-merge passou com o modelo free `opencode/deepseek-v4.1-flash-free`: `changed_files=['hello.txt']`, `done` com PRE_MERGE PASS e POST_MERGE PASS. Chamadas seguintes foram bloqueadas por limite free (HTTP 429) e o provider padrão por quota (HTTP 402); portanto `review-run`/`security-run` ao vivo não foram declarados como medidos.
- Documentação corrigida para `opencode v2.2.7`, 346 testes padrão, `PWD` como âncora de workspace e limites de quota. Nenhuma compatibilidade V1 nem capacidade V2 não medida foi declarada.

**Test Coverage**:
- [x] `tests/test_e2e_v2.py` — 8 testes de fluxo completo e caminhos negativos.
- [x] `tests/test_opencode_adapter.py::test_execute_pins_pwd_to_workspace` — PWD e `cwd` relativo normalizado.
- [x] `tests/test_opencode_smoke.py::test_real_v2_capabilities_are_measured` — opt-in, sem modelo.
- [x] Suíte completa pós-merge: **346 passed** (`uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py`).
- [x] `python3 -m compileall juicer/ -q` OK.
- [x] `git diff --check` limpo.

**Review**:
- [x] Revisado por @reviewer — **Approved**, sem findings critical/high.
- [x] Findings medium corrigidos: contradição HARNESS_CONTRACT × STATUS, status de review/security marcado como `partial`, suposição de CWD no plano corrigida, regressões PWD fail-closed, asserção de path protegido efetiva, gate de verificação NOT RUN coberto, conteúdo de evidência preservada verificado.
- [x] Findings low endereçados quando aplicáveis: `.juicer/` no `.gitignore` do fixture, docstring do smoke, versão do fake, redação de aprovação no backlog.

**Security Review**:
- [x] Revisado por @security — **Approved**, sem findings critical/high.
- [x] `PWD` reduz a superfície do bug medido; testes falham sem o fix.
- [x] Riscos residuais documentados em STATUS/HARNESS_CONTRACT: configuração/agentes (`.opencode/`, `AGENTS.md`, `opencode.json`) não são paths protegidos por padrão; `external_directory` é permitido por padrão na V2; arquivos gitignorados não aparecem no diff de escopo. Nenhum deles é novo gate implícito ou substituto das permissões do harness.

**Documentation**:
- [x] README, STATUS, AGENTS, `docs/HARNESS_CONTRACT.md`, `docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md` e CHANGELOG atualizados.
- [x] Backlog e `backlog/in-progress.md` sincronizados; TASK-011 movida para `backlog/done/`.

**Notes**: Feature commit `b93005d` (`test(e2e): validate V2 acceptance flow and pin PWD workspace (TASK-011)`). Baseline anterior `a59cf0b`. Ver Apêndice A do plano. Gate de aceitação do MVP V2, não de release/deploy. Follow-ups não bloqueantes: repetir `review-run`/`security-run` ao vivo com quota disponível; avaliar proteção de `.opencode/`/`AGENTS.md` e varredura de arquivos ignorados em uma tarefa futura.
