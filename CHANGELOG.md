# Changelog

## 4.0.0 — 2026-11-13

Primeira versão com core executável, fiel ao modelo aprovado no documento
estrutural v2.0 (escopo MVP) e no mapa de atividades v2.

### Adicionado

- `juicer/` — core Python (biblioteca padrão apenas):
  - `state.py` — escrita atômica, lock `flock`, fence de `revision`,
    eventos JSONL append-only, path confinement.
  - `model.py` — contratos Mission/Task/Execution/CheckResult conforme
    B.12/B.13 (IDs estáveis, status ready→in_progress→completed→done).
  - `graph.py` — grafo de dependências, ciclos, elegibilidade
    (ready + deps done), ondas topológicas.
  - `scheduler.py` — liberação automática de tarefas elegíveis; paralelismo
    real com `--jobs` ou serialização com motivo registrado.
  - `checks.py` — execução de checks do projeto; resultados
    `PASS/FAIL/BLOCKED/NOT RUN` (NOT RUN nunca passa).
  - `gates.py` — gate técnico; resultado obsoleto conta como NOT RUN.
  - `gitops.py` — worktree/branch por tarefa, merge `--no-ff` explícito,
    conflito aborta sem sobrescrever, evidência de diff.
  - `harness/opencode.py` — adapter OpenCode: detecção de binário
    (`OPENCODE_BIN` → PATH → registry Zed), `run --format json --agent`,
    workspace isolado por `cwd` + `PWD` (V2 não tem `--dir`), captura de
    session id/exit code; texto do agente nunca é tratado como prova.
  - `orchestrator.py` — fluxo vertical: missão (com lacunas → waiting_human),
    inspeção, decomposição, execução isolada, checks, importação unidirecional
    de backlog, gates de review/security, aprovação humana vinculada a
    commit/tree, integração com gate + pós-merge, checkpoint/resume.
  - `backlog.py` — importação one-way do Markdown com validação de schema,
    IDs, dependências, prioridades, critérios e escopo; journal com rollback e
    retomada.
  - `cli.py` + `bin/juicer` — comandos `init`, `mission`, `gap`, `inspect`,
    `decompose`, `import-backlog`, `status`, `run`, `retry`, `review`,
    `security`, `review-run`, `security-run`, `approve`, `integrate`,
    `checkpoint`, `resume`, `events`, `discover`.
- `tests/` — 345 testes (pytest): estado/retomada, transições, grafo,
  elegibilidade, falha+recuperação, captura por tarefa, gates
  NOT RUN/FAIL/BLOCKED, isolamento/escopo/paths protegidos, commits do agente,
  revisão/segurança/aprovação, importação de backlog, E2E V2 com fluxo
  completo e caminhos negativos, adapter com fake binário e CLI.
- `STATUS.md` — matriz de capacidades validadas/pendentes e limitações.

### Não alterado

- Kit Markdown 3.x (agentes, comandos, skills, `backlog/`) permanece
  funcional e intacto.
- Documentos aprovados de referência não foram modificados.

### Limitações registradas

- OpenCode validado: **2.2.7 (V2)** — `discover` v2=true, smoke de
  capabilities, execução real de `run`+checks+integração+pós-merge e E2E
  determinístico completo. `review-run`/`security-run` ao vivo ficaram
  bloqueados por quota/limite do provider (HTTP 402/429); o caminho é coberto
  por testes. V1 permanece degradado e fora do alvo (ver STATUS.md).
- Workspace V2 resolvido por `cwd` + `PWD`; worktrees devem permanecer dentro
  do projeto para a descoberta de `.opencode/`.
- Sem coordenação entre máquinas, sem preview/URL, sem deploy: fora do MVP
  aprovado.

## 3.0.0 — 2026-10-06

Retorno à estrutura simples do kit (linha v1), adaptada ao OpenCode 1.18.34:

- Kit somente Markdown: `.opencode/` (agents, commands e skills) +
  `backlog/` próprio de cada projeto.
- Instalação conforme o README: cópia de `.opencode/` e `backlog/`,
  git submodule ou symlink.
- README e `docs/GUIDE.md` alinhados ao kit e ao OpenCode 1.18.34.
- `VERSION` na raiz como fonte de versão do kit.

### Linha 2.x arquivada

A arquitetura harness-agnostic (adapters, `bin/juicer` em Python,
suíte de testes, `kit.yaml`, CI) permanece no histórico e está
arquivada na tag `v2.5.0`. O pacote npm `@juicer-kit/cli` pertence a
essa linha arquivada — o canal de instalação suportado é o Git
(conforme o README).
