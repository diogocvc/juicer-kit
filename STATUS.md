# STATUS — Juicer Kit 4.0.0

Estado real da implementação, capacidades validadas e limitações. Este
documento descreve apenas o que foi implementado e executado; não contém
promessas de recursos futuros. Lacunas planejadas estão mapeadas em
[`docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md`](docs/PLANO_IMPLEMENTACAO_JUICER_KIT_4.0.md).

## Versão

- Kit: **4.0.0** (core Python + kit Markdown alinhado ao fluxo 4.0)
- Harness alvo único: **OpenCode 2.x/V2** — versão medida no ambiente:
  **opencode v2.2.7** (`~/.opencode/bin/opencode`)
- Medição anterior registrada: `opencode v2.1.4` (mantida como histórico em
  STATUS/contrato).
- Data desta avaliação: 2026-11-12

## Alvo e evidência

O MVP usa **OpenCode 2.0/V2** (decisão D5 revisada). A tabela abaixo separa
capacidade **medida** (probe ou smoke com o binário 2.2.7) de lacuna
planejada. O binário V1 1.19.4 ainda presente no registry do Zed não é alvo do
MVP; `discover` o marca como `degraded` se for o único encontrado.
Documentação de agentes/comandos é **orientativa**: não substitui nem amplia os
gates, evidências e aprovação aplicados pelo core.

| Capacidade | Status | Como foi validado |
| --- | --- | --- |
| Detecção de binário (OPENCODE_BIN → PATH → ~/.opencode/bin → Zed) | **supported (medida)** | `juicer discover` retornou v2.2.7; V2 preferido entre candidatos |
| Distinção V2 × V1 no probe de versão | **supported (medida)** | `caps.v2=true` em 2.2.7; V1 fake → `degraded` |
| Contrato interno `discover`/`run` | **supported (medida)** | `tests/test_harness_contract.py` + `docs/HARNESS_CONTRACT.md` |
| Execução `opencode run --format json --agent <x> --standalone` | **supported (medida)** | smoke real V2 + testes com binário falso |
| Workspace via cwd + `PWD` do processo (sem `--dir`) | **supported (medida)** | V2 resolve o projeto por `PWD`; em 2.2.7 o cwd do subprocesso sozinho não basta. O adaptador fixa `cwd` e `PWD`; regressão em `tests/test_opencode_adapter.py` e no binário V2 scriptado do E2E |
| Realinhamento do worktree após medir `PWD` | **supported (medida)** | execução real no worktree entregou `hello.txt` no worktree e integrou com pós-merge PASS; antes do fix, o agente escrevia no repositório chamador |
| `--standalone` (servidor privado por execução) | **supported (medida)** | smoke real V2; padrão do adaptador |
| Captura de session id + exit code + eventos NDJSON | **supported (medida)** | smoke real + `parse_run_output` (formato `part` V2) |
| Sessão via `--session` / `--continue` | **partial** | flags detectadas e `--session` repassada; retomada real não exercitada |
| `--auto` desativado por padrão | **supported (medida)** | testes de contrato |
| Permissões estruturadas V2 no config | **documental** | docs V2 (allow/ask/deny); política restritiva headless não medida |
| Isolamento por branch/worktree git | **supported** | git CLI do core (worktree nativo V2 não usado) |
| Paralelismo local real (2 tarefas) | **supported (histórico V1)** | smoke anterior com `--jobs 2`; revalidar com V2 standalone |
| Checks determinísticos PASS/FAIL/BLOCKED/NOT RUN | **supported** | 345 testes padrão + checks opt-in de V2 |
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
| Revisão e segurança como gates quando exigidos pela política | **supported (medida)** | `required_gates` + artefatos estruturados + gate; o core não adiciona gates implícitos; alto risco exige aprovação humana e segurança só é gate se declarada; `tests/test_integrate.py`, `tests/test_evidence.py` |
| Acionamento de `@reviewer`/`@security` pelo core | **partial** | `review-run` executou o `@reviewer` real na medição V2.1.4 (antes do fix de `PWD`) e retornou JSON estrito; NDJSON capturado reproduzido até `done`. `security-run` ao vivo nunca foi executado. Em V2.2.7 o probe de capabilities e uma execução real de tarefa passaram, mas `review-run`/`security-run` ao vivo ficaram bloqueados por quota/limite do provider (HTTP 402/429). O caminho completo é coberto por testes e pelo E2E determinístico |
| Fail-fast de severidade/estrutura das evidências | **supported (medida)** | `validate_findings` rejeita severidade/descrição inválidas antes de gravar |
| `--dir` na CLI V2 | **ausente (medida)** | `run --help` em 2.1.4 e 2.2.7 não tem `--dir`; isolamento via `cwd` + `PWD` |
| Worktrees nativos do OpenCode V2 | **documental / não usado** | API existe; MVP mantém git CLI |
| Preview/URL de preview (A15) | **unsupported** | fora do fluxo vertical MVP |
| Deploy/release (A16–A18) | **fora do MVP** | conforme escopo aprovado |
| Segundo harness, coordenação distribuída | **fora do MVP** | conforme escopo aprovado |
| Compatibilidade V1 como alvo | **não prometida** | D5/D9; V1 degradado se detectado |
| Alinhamento de agentes, comandos e documentação ao alvo V2 | **supported (documental)** | `AGENTS.md`, README, STATUS e `docs/HARNESS_CONTRACT.md` declaram a ordem canônica, a separação backlog/`.juicer` e medida × lacuna; `@reviewer`/`@security` são read-only e não substituem gates; `tests/test_docs_alignment.py` |
| Fluxo E2E V2 completo (missão → import → run → review → security → approval → merge → pós-merge) | **supported (medido por E2E determinístico)** | `tests/test_e2e_v2.py` aciona o core real e o adaptador V2 real contra um binário V2 scriptado que fala o NDJSON medido; importa backlog, executa, dispara `review-run`/`security-run`, exige aprovação, integra e roda checks pós-merge até `done` |
| Caminhos negativos do fluxo E2E | **supported (medido)** | revisão/segurança/aprovação ausentes bloqueiam o merge; alteração fora de escopo, commit do agente e path protegido falham a tarefa; falha pós-merge deixa `blocked` (nunca `completed`/`done`); interrupção + retry + `resume` preservam evidência e worktree |
| Smoke real V2 (capabilities, sem chamada de modelo) | **supported (medido em 2026-11-12)** | `JUICER_OPENCODE_SMOKE=1 pytest tests/test_opencode_smoke.py -q -k capabilities` → 1 passed; binário `opencode v2.2.7`, `v2=true`, `run_json=true`, `standalone_flag=true`, `dir_flag=false`, `events=jsonl-stream` |
| Smoke real V2 com chamada de modelo | **parcialmente medido** | Uma execução real completa de `run` + checks + `integrate` + pós-merge passou com o modelo free `opencode/deepseek-v4.1-flash-free` (`changed_files=['hello.txt']`, `done` com PRE/POST PASS). `review-run`/`security-run` ao vivo não rodaram: o provider free retornou HTTP 429 (limite de uso) e o provider padrão retorna HTTP 402 (quota). O caminho de review/security/approval é coberto pelo E2E determinístico |

## Limitações ambientais

1. **Binário V2**: instalado via `opencode upgrade --major` em
   `~/.opencode/bin/opencode` (v2.2.7). Em outros ambientes, defina
   `OPENCODE_BIN` ou instale no PATH.
2. **Configuração/agentes no worktree**: a V2 descobre `.opencode/` subindo a
   partir do `PWD`. Os worktrees ficam em `.juicer/worktrees/<task>` dentro do
   projeto, então o `.opencode/` do topo é encontrado. Se os worktrees forem
   movidos para fora do projeto, o `.opencode/` precisa existir no worktree ou
   na configuração global; caso contrário a V2 falha com `Agent not found`.
3. **Custo de modelo**: cada `juicer run` faz uma chamada real de modelo via
   `opencode run --standalone`. O tempo e o custo dependem do provider.
4. **Escopo local**: locks `flock` + fence de revisão cobrem concorrência
   multi-processo **local**. `--standalone` isola sessões por processo; não há
   coordenação entre máquinas.
5. **Python**: o core usa apenas a biblioteca padrão; testes usam pytest via
   `uv tool run pytest`.
6. **`completed` ≠ `done`**: uma tarefa só fica `done` após gates técnicos
   PASS, integração explícita e checks pós-merge PASS.
7. **Permissões V2 ≠ gates**: política `permissions[]` do OpenCode é barreira
   adicional; escopo, evidência e aprovação permanecem no core.
8. **Escrita fora do worktree**: o agente executa em
   `.juicer/worktrees/<task>`, dentro do diretório de estado. O core valida o
   diff/branch do worktree; escrita direta em `.juicer/` por processos do
   agente não aparece nesse diff e depende da barreira de permissões/sandbox do
   harness. Na V2, `external_directory` é permitido por padrão; configure
   `permissions[]` com `deny`/`ask` para escrita e leitura fora do cwd. A
   permissão continua sendo barreira adicional, nunca evidência.
9. **Evidência preservada pode conter segredo**: o patch de uma tentativa
   anterior (`preserved-*.diff`) captura o conteúdo do worktree, inclusive um
   arquivo sensível que o agente tenha escrito. Isso é intencional para
   auditoria; restrinja o acesso a `.juicer/` e trate esses artefatos como
   sensíveis.
10. **Configuração/agentes não são path protegido por padrão**: `.opencode/`,
    `opencode.json(c)` e `AGENTS.md` não estão em `DEFAULT_PROTECTED_PATHS`.
    Uma tarefa cujo escopo permita esses paths pode alterar o próprio agente de
    review/security antes do gate. Mantenha-os fora do escopo ou adicione-os a
    `protected_paths`; o core detecta a mudança, mas não valida a definição do
    agente. Arquivos ignorados pelo git também não aparecem no diff usado pelo
    escopo; a barreira de permissões/sandbox continua necessária.

## Comandos de verificação executados

```
export PATH="$HOME/.opencode/bin:$PATH"
python3 -m compileall juicer bin/juicer          # OK
uv tool run pytest -q tests/ --ignore=tests/test_opencode_smoke.py
                                                 # 345 passed (2026-11-12)
JUICER_OPENCODE_SMOKE=1 uv tool run pytest -q tests/test_opencode_smoke.py -k capabilities
                                                 # 1 passed (V2 real, sem modelo)
# smoke real V2 de review-run (2026-10-29): @reviewer executou no binário
# v2.1.4 e devolveu JSON estrito; o NDJSON real foi reproduzido no caminho de
# evidência (artefato PASS -> critérios -> done). Nova chamada ao vivo: HTTP
# 402 (quota do provider), não falha de código.
JUICER_OPENCODE_SMOKE=1 uv tool run pytest -q tests/test_opencode_smoke.py
                                                 # bloqueado: HTTP 402 quota
python3 bin/juicer discover                      # opencode v2.2.7; v2=true; status=supported
# execução real V2 (2026-11-12, modelo free, sem custo):
# core run -> changed_files=['hello.txt'] -> checks PASS -> integrate -> done
#   PRE_MERGE PASS, POST_MERGE PASS; arquivo entregue no worktree (não no repo chamador)
# depois da execução: HTTP 429 (limite de uso free) para novas chamadas
# smoke real V2 (2026-10-26, binário 2.1.4):
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
- Smoke real V2 com chamada de modelo em `v2.2.7`: uma execução completa
  (run/checks/integrate/pós-merge) passou com modelo free em 2026-11-12; novas
  chamadas foram bloqueadas por limite de uso free (HTTP 429) e o provider
  padrão por quota (HTTP 402). Repetir `review-run`/`security-run` ao vivo
  quando houver quota.
- `PWD` como âncora de projeto: medido em 2.2.7; o adaptador fixa `cwd` e
  `PWD`. Revalidar em futuras versões V2 antes de assumir apenas `cwd`.
- Preview de build/URL (A15) — não implementado no MVP.
