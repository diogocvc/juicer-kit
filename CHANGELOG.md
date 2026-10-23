# Changelog

## 4.0.0 — 2026-10-23

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
    `--dir` fixo para worktrees, captura de session id/exit code; texto do
    agente nunca é tratado como prova.
  - `orchestrator.py` — fluxo vertical: missão (com lacunas → waiting_human),
    inspeção, decomposição, execução isolada, checks, integração com gate +
    pós-merge, checkpoint/resume.
  - `cli.py` + `bin/juicer` — comandos `init`, `mission`, `gap`, `inspect`,
    `decompose`, `status`, `run`, `retry`, `integrate`, `checkpoint`,
    `resume`, `events`, `discover`.
- `tests/` — 64 testes (pytest): estado/retomada, grafo, elegibilidade,
  falha+recuperação, captura por tarefa, gates NOT RUN/FAIL/BLOCKED,
  proteção de docs aprovados e mudanças pré-existentes, paralelismo isolado
  (worktrees reais), integração com pós-merge, adapter com fake binário,
  CLI.
- `STATUS.md` — matriz de capacidades validado/pendente e limitações.

### Não alterado

- Kit Markdown 3.x (agentes, comandos, skills, `backlog/`) permanece
  funcional e intacto.
- Documentos aprovados de referência não foram modificados.

### Limitações registradas

- OpenCode validado: 1.19.4 (referência cita 2.0; só a integração foi
  adaptada — ver STATUS.md).
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
