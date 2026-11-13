# STATUS — Juicer Kit 4.0.0

Estado real da implementação, capacidades validadas e limitações. Este
documento descreve apenas o que foi implementado e executado; não contém
promessas de recursos futuros. Lacunas planejadas estão mapeadas em
[`docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md`](docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md).

## Versão

- Kit: **4.0.0** (core Python + kit Markdown 3.x preservado)
- Harness alvo único: **OpenCode 2.x/V2** — versão medida no ambiente:
  **opencode v2.1.4** (`~/.opencode/bin/opencode`)
- Data desta avaliação: 2026-11-10

## Alvo e evidência

O MVP usa **OpenCode 2.0/V2** (decisão D5 revisada). A tabela abaixo separa
capacidade **medida** (probe ou smoke com o binário 2.1.4) de lacuna
planejada. O binário V1 1.19.4 ainda presente no registry do Zed não é alvo do
MVP; `discover` o marca como `degraded` se for o único encontrado.

| Capacidade | Status | Como foi validado |
| --- | --- | --- |
| Detecção de binário (OPENCODE_BIN → PATH → ~/.opencode/bin → Zed) | **supported (medida)** | `juicer discover` retornou v2.1.4; V2 preferido entre candidatos |
| Distinção V2 × V1 no probe de versão | **supported (medida)** | `caps.v2=true` em 2.1.4; V1 fake → `degraded` |
| Contrato interno `discover`/`run` | **supported (medida)** | `tests/test_harness_contract.py` + `docs/HARNESS_CONTRACT.md` |
| Execução `opencode run --format json --agent <x> --standalone` | **supported (medida)** | smoke real V2 + testes com binário falso |
| Workspace via CWD do processo (sem `--dir`) | **supported (medida)** | smoke real leu arquivo do workdir temporário |
| `--standalone` (servidor privado por execução) | **supported (medida)** | smoke real V2; padrão do adaptador |
| Captura de session id + exit code + eventos NDJSON | **supported (medida)** | smoke real + `parse_run_output` (formato `part` V2) |
| Sessão via `--session` / `--continue` | **partial** | flags detectadas e `--session` repassada; retomada real não exercitada |
| `--auto` desativado por padrão | **supported (medida)** | testes de contrato |
| Permissões estruturadas V2 no config | **documental** | docs V2 (allow/ask/deny); política restritiva headless não medida |
| Isolamento por branch/worktree git | **supported** | git CLI do core (worktree nativo V2 não usado) |
| Paralelismo local real (2 tarefas) | **supported (histórico V1)** | smoke anterior com `--jobs 2`; revalidar com V2 standalone |
| Checks determinísticos PASS/FAIL/BLOCKED/NOT RUN | **supported** | 319 testes padrão + smoke |
| Importação unidirecional do backlog | **supported (medida)** | `juicer/backlog.py` + `Juicer.import_backlog` valida schema/IDs/dependências/prioridades/critérios/escopo; importa uma vez em missão vazia, recusa missão com tarefas e backlog alterado, repete como `unchanged`; journal `pending`/`complete` com rollback ou retomada; `tests/test_backlog_import.py` |
| Gate técnico bloqueia NOT RUN/FAIL/BLOCKED | **supported** | `tests/test_gates.py` |
| Merge explícito + conflito detectado | **supported** | `tests/test_preservation.py` |
| Checks pós-integração no commit mergeado | **supported** | testes de integrate |
| Retomada após reinício (checkpoint/resume) | **supported (medida)** | `resume` reconcilia execução e worktree; interrompido+worktree → `blocked`; sem worktree → `failed`; execução terminal alinha a tarefa; histórico + relatório `.juicer/evidence/resume-*.json`; execução de outra tarefa é ignorada; `tests/test_recovery.py` |
| Transições TASK/EXECUTION validadas em todo update | **supported (medida)** | `check_transition` em `_update_task`/`_update_execution`; `tests/test_transitions.py` |
| `blocked`/`failed` retomáveis com histórico | **supported (medida)** | `retry_task` + `attempt_history` (execução/branch/worktree/commit anteriores preservados) |
| Retry não colide e preserva tentativa anterior | **supported (medida)** | nova tentativa usa `juicer/<task>-attempt-<n>` e worktree próprio, inclusive após interrupção/`resume`; tentativa anterior e branch permanecem auditáveis; `tests/test_recovery.py` |
| Falha pós-merge → `blocked` (nunca `completed`/`done`) | **supported (medida)** | `result.merged_commit` + `post_merge_gate` registrados; `test_post_merge_failure_*` |
| Conflito de merge aborta sem merge parcial | **supported (medida)** | `merge --abort`; `blocked_reason` com commit/branch; `partial_merge` no evento; merge já em andamento não é abortado; intervenção explícita; `tests/test_recovery.py` |
| Checkpoint registra próximo passo e evidência | **supported (medida)** | por tarefa: `status`, `next_step`, `blocked_reason`, execução/branch/commit/tree/merged; `tests/test_recovery.py` |
| Proteção de mudanças pré-existentes | **supported** | `test_preservation.py`, `tests/test_isolation.py` |
| Execução registra `base_commit`, `agent_head_commit`, `head_commit`, `tree_hash` e branch | **supported (medida)** | `result` e `execution.workspace`; `tests/test_isolation.py` |
| Escopo cobre rastreados + não rastreados + commits do agente | **supported (medida)** | diff contra `base_commit` (`changed_files(base)`); `tests/test_isolation.py` |
| Caminhos protegidos bloqueados no core (`.juicer/`, `.git/`, segredos, política) | **supported (medida)** | `juicer/scope.py` + rechecagem no merge sobre todo o histórico `base..commit` (inclui commits intermediários e renames); independente de permissões V2 |
| Commit do agente detectado e recusado por padrão | **supported (medida)** | `agent_head_commit != base_commit`; opt-in explícito via `allow_agent_commits` |
| Worktree/branch preservados antes da remoção (retry) | **supported (medida)** | `_preserve_prior_attempt` grava HEAD/tree/diff/branch tip e ref durável em `.juicer/evidence/`; falha do ref gera `attempt_preservation_degraded` |
| Concorrência serial por padrão | **supported (medida)** | `DEFAULT_CONFIG.max_jobs=1`; paralelismo só com `--jobs` explícito |
| Fronteira permissões V2 × gates/escopo do core | **supported (medida)** | permissões `allow-all` não afetam path protegido nem gate de review; `tests/test_isolation.py` |
| `required_gates` desconhecidos rejeitados na importação | **supported (medida)** | `validate_task` (`GATE_NAMES`); `tests/test_isolation.py` |
| Branch tip deve coincidir com o commit evidenciado no merge | **supported (medida)** | `branch_tip == result.commit`; branch movida bloqueia integração |
| Aprovação humana separada do gate técnico | **supported (medida)** | `juicer approve` grava registro aprovador/task/commit/tree/data/nota; `--approve` sem registro é recusado; novo commit invalida; não altera gates técnicos; alto risco exige aprovação; `tests/test_approval.py` |
| Critérios de aceitação verificados pelo core | **supported (medida)** | `check:<id>`, `review`, `security`, `human`; evidência vinculada a commit/tree; auditoria por critério; `tests/test_criteria.py` |
| Revisão e segurança obrigatórias no core | **supported (medida)** | `required_gates` + artefatos estruturados + gate; `tests/test_integrate.py`, `tests/test_evidence.py` |
| Acionamento de `@reviewer`/`@security` pelo core | **supported (medido: review-run)** | `review-run` executou o `@reviewer` real (V2.1.4) e retornou JSON estrito; NDJSON capturado reproduzido até `done`. `security-run`: mesmo caminho de código, coberto por testes (chamada ao vivo bloqueada por quota do provider) |
| Fail-fast de severidade/estrutura das evidências | **supported (medida)** | `validate_findings` rejeita severidade/descrição inválidas antes de gravar |
| `--dir` na CLI V2 | **ausente (medida)** | `run --help` 2.1.4 não tem `--dir`; isolamento via CWD |
| Worktrees nativos do OpenCode V2 | **documental / não usado** | API existe; MVP mantém git CLI |
| Preview/URL de preview (A15) | **unsupported** | fora do fluxo vertical MVP |
| Deploy/release (A16–A18) | **fora do MVP** | conforme escopo aprovado |
| Segundo harness, coordenação distribuída | **fora do MVP** | conforme escopo aprovado |
| Compatibilidade V1 como alvo | **não prometida** | D5/D9; V1 degradado se detectado |

## Limitações ambientais

1. **Binário V2**: instalado via `opencode upgrade --major` em
   `~/.opencode/bin/opencode` (v2.1.4). Em outros ambientes, defina
   `OPENCODE_BIN` ou instale no PATH.
2. **Custo de modelo**: cada `juicer run` faz uma chamada real de modelo via
   `opencode run --standalone`. O tempo e o custo dependem do provider.
3. **Escopo local**: locks `flock` + fence de revisão cobrem concorrência
   multi-processo **local**. `--standalone` isola sessões por processo; não há
   coordenação entre máquinas.
4. **Python**: o core usa apenas a biblioteca padrão; testes usam pytest via
   `uv tool run pytest`.
5. **`completed` ≠ `done`**: uma tarefa só fica `done` após gates técnicos
   PASS, integração explícita e checks pós-merge PASS.
6. **Permissões V2 ≠ gates**: política `permissions[]` do OpenCode é barreira
   adicional; escopo, evidência e aprovação permanecem no core.
7. **Escrita fora do worktree**: o agente executa em
   `.juicer/worktrees/<task>`, dentro do diretório de estado. O core valida o
   diff/branch do worktree; escrita direta em `.juicer/` por processos do
   agente não aparece nesse diff e depende da barreira de permissões/sandbox do
   harness. Configure `permissions[]` com `deny` para escrita fora do cwd; a
   permissão continua sendo barreira adicional, nunca evidência.
8. **Evidência preservada pode conter segredo**: o patch de uma tentativa
   anterior (`preserved-*.diff`) captura o conteúdo do worktree, inclusive um
   arquivo sensível que o agente tenha escrito. Isso é intencional para
   auditoria; restrinja o acesso a `.juicer/` e trate esses artefatos como
   sensíveis.

## Comandos de verificação executados

```
export PATH="$HOME/.opencode/bin:$PATH"
python3 -m compileall juicer bin/juicer          # OK
uv tool run pytest -q tests/                     # 319 passed (2026-11-11)
# smoke real V2 de review-run (2026-10-29): @reviewer executou no binário
# v2.1.4 e devolveu JSON estrito; o NDJSON real foi reproduzido no caminho de
# evidência (artefato PASS -> critérios -> done). Nova chamada ao vivo: HTTP
# 402 (quota do provider), não falha de código.
JUICER_OPENCODE_SMOKE=1 uv tool run pytest -q tests/test_opencode_smoke.py
                                                 # 1 passed (V2 real)
python3 bin/juicer discover                      # opencode v2.1.4; v2=true; status=supported
# smoke real V2 (2026-10-26):
# SMOKE-OK-7Q2, exit_code=0, session ses_..., --standalone, sem --dir
```

## Pendências de validação

- Retomada real de sessão via `--session`/`--continue`.
- Política de permissões V2 restritiva em headless (`deny`/`ask` em shell e
  edit).
- Revalidar paralelismo `--jobs 2` com `--standalone` V2.
- Smoke real V2 de `review-run`: execução real do `@reviewer` validada
  (v2.1.4) e NDJSON real reproduzido até `done`; nova chamada ao vivo bloqueada
  por quota do provider (HTTP 402). `security-run` ao vivo não executado (mesmo
  caminho de código; coberto por testes).
- Preview de build/URL (A15) — não implementado no MVP.
