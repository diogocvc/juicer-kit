# Plano de Implementação — Juicer Kit 4.0

**Status:** aprovado para execução; implementação ainda não iniciada.

**Data:** 2026-10-25

**Decisão de arquitetura:** B — confirmar com ajustes. O MVP usa OpenCode
1.19.4/V1, com contrato interno mínimo de harness e testes de contrato. V2 é
uma migração futura, não uma promessa do MVP.

**Escopo deste documento:** consolidar requisitos, decisões, lacunas, fases,
critérios de conclusão e tarefas de backlog. Este documento não implementa o
MVP.

## 1. Objetivo, escopo e não objetivos

### Objetivo

Entregar um fluxo vertical auditável para transformar uma missão em tarefas,
executá-las em isolamento, verificar critérios e gates, exigir revisão e
aprovação humana quando aplicável, integrar explicitamente e só então marcar a
tarefa como concluída.

Fluxo canônico:

```text
missão
  -> importação validada do backlog
  -> tarefas
  -> execução em worktree
  -> diff e escopo
  -> checks determinísticos
  -> revisão
  -> segurança (quando aplicável)
  -> aprovação humana (quando aplicável)
  -> merge explícito
  -> checks pós-merge
  -> done
```

### Dentro do MVP

- OpenCode **1.19.4/V1** como harness validado.
- Core Python stdlib já existente em `juicer/`.
- Worktrees git e branches isoladas.
- Estados, transições, critérios de aceitação, gates técnicos e aprovação
  humana separada.
- Revisão obrigatória para mudanças de código.
- Segurança obrigatória para mudanças de alto risco.
- Retry, recuperação, conflitos, falha pós-merge e retomada.
- Backlog Markdown como planejamento e `.juicer/` como estado operacional
  canônico após a importação.
- Testes unitários, testes de contrato, smoke real V1 e E2E.

### Fora do MVP

- Adaptador V2 ou declaração de compatibilidade V2.
- Preview de build/URL (A15).
- Release, deploy e operações (A16–A18).
- UI, orquestração distribuída, múltiplos projetos e segundo harness.
- Sincronização bidirecional entre backlog e `.juicer/`.
- Novos agentes.
- Implementação de código nesta etapa de planejamento.

### Critério de sucesso do MVP

O fluxo completo deve funcionar em um repositório temporário com o binário V1
real, incluindo os caminhos negativos: gate ausente, revisão ausente, segurança
exigida e não executada, aprovação ausente, alteração fora de escopo, commit
feito pelo agente, falha pós-merge, interrupção e retry. Nenhum desses caminhos
pode resultar em `done` silencioso.

## 2. Decisões e premissas

| ID | Decisão | Consequência |
| --- | --- | --- |
| D1 | Backlog Markdown é a fonte de planejamento; `.juicer/` é a fonte operacional canônica após a importação para uma missão. | A importação valida os dados. Não há sincronização bidirecional silenciosa nem sobrescrita automática de missão em andamento. |
| D2 | Preview (A15) fica fora do MVP. | A limitação deve ser explícita em `STATUS.md` e no plano. |
| D3 | Release/deploy A16–A18 ficam fora do MVP. | Nenhuma tarefa do backlog 4.0 deve prometer essas capacidades. |
| D4 | Aprovação humana é obrigatória conforme risco e política explícita da tarefa. | Aprovação não substitui gates técnicos e deve ser registrada com aprovador, tarefa, commit, tree hash, data e nota. |
| D5 | O harness alvo do MVP é OpenCode 1.19.4/V1. | O adaptador V1 permanece mínimo e baseado nas necessidades reais do core. V2 não é implementado nem declarado compatível. |
| D6 | `TASK-001` e `TASK-002` são preservadas. | Novas tarefas usam `TASK-003` a `TASK-011`, sem renumerar ou reescrever o histórico existente. |
| D7 | Não criar agentes novos. | A implementação reutiliza `@orchestrator`, `@reviewer`, `@security` e `@tester` já existentes. |

### Premissas

- O binário OpenCode 1.19.4 continua disponível no registry do Zed, via
  `OPENCODE_BIN` ou no `PATH`.
- A suíte atual de 64 testes permanece verde como linha de base.
- O core continua em Python stdlib, sem novas dependências obrigatórias.
- O responsável pela implementação conhece o core e pode trabalhar em uma
  única sessão por tarefa.
- O design de artefatos de revisão e segurança pode ser implementado sem criar
  um novo agente ou um serviço externo.
- O custo e a latência de chamadas reais ao modelo não entram na estimativa.

### Incertezas conhecidas

- O comportamento real de permissões headless do OpenCode 1.19.4 ainda não foi
  validado com uma política restritiva.
- O formato estruturado de evidência de revisão e segurança precisa ser
  desenhado e testado; texto livre de agente não é prova suficiente.
- A segurança de paralelismo local precisa ser confirmada antes de habilitar
  concorrência por padrão.
- A importação do backlog pode revelar necessidades de validação de IDs,
  dependências e critérios ainda não cobertas.
- Não há binário V2 disponível para validar APIs, eventos, permissões ou
  workspaces nativos.

## 3. Arquitetura e fonte de verdade

### Fronteiras

```text
backlog/*.md
  -> importador validado (uma vez por missão)
  -> .juicer/ (missão, tarefas, execuções, evidências, checks, eventos)
  -> core (estado, escopo, gates, aprovação, retry, retomada)
  -> harness (executa o agente)
  -> git (worktree, diff, commit, merge, pós-merge)
```

O core é responsável por estado, política, evidências, gates, escopo,
aprovação, recuperação e integração. O harness apenas executa uma solicitação e
devolve um resultado normalizado. O harness não decide se uma tarefa está
concluída.

### Fonte de verdade

1. O backlog Markdown é usado para planejar, priorizar e selecionar tarefas.
2. Ao iniciar uma missão, o backlog é importado com validação de schema, IDs,
   dependências, prioridades, critérios e escopo.
3. Depois da importação, `.juicer/` é a fonte operacional canônica.
4. Alterações posteriores no backlog não sobrescrevem automaticamente uma
   missão em andamento.
5. Não há sincronização bidirecional silenciosa. Uma eventual reconciliação
   explícita deve ser uma operação deliberada, registrada em eventos.
6. O kit Markdown 3.x continua funcionando isoladamente como legado, sem
   sincronização automática com o core 4.0.

### Componentes existentes relevantes

- `juicer/model.py`: contratos de missão, tarefa, execução e check.
- `juicer/state.py`: escrita atômica, lock, revision fence e eventos.
- `juicer/gates.py`: semântica `PASS/FAIL/BLOCKED/NOT RUN`.
- `juicer/orchestrator.py`: fluxo missão -> execução -> integração -> retomada.
- `juicer/gitops.py`: worktrees, branches, merge e conflitos.
- `juicer/harness/opencode.py`: adaptador V1.
- `juicer/cli.py`: interface de linha de comando.

## 4. Modelo de estados e transições

### Tarefa

| Estado | Significado |
| --- | --- |
| `ready` | Pode ser executada; dependências concluídas. |
| `in_progress` | Execução em andamento ou interrompida. |
| `blocked` | Exige intervenção humana, correção ou nova tentativa. |
| `failed` | Execução falhou e pode ser retentada. |
| `completed` | Pré-merge concluído; ainda não integrada. |
| `done` | Integrada e com checks pós-merge aprovados; estado terminal. |

Transições permitidas devem seguir `TASK_TRANSITIONS` em `juicer/model.py`.
Toda atualização de tarefa e execução deve passar por validação explícita de
transição. Atualizações diretas de status não são permitidas.

Invariantes:

- `completed` nunca significa integração concluída.
- `done` só é alcançado depois de merge explícito e gate pós-merge `PASS`.
- Falha pós-merge deve mover a tarefa para `blocked`, nunca deixá-la em
  `completed` ou `done`.
- `blocked` e `failed` podem ser retomados explicitamente; `done` é terminal.
- `resume` não pode marcar `failed` cegamente sem reconciliar a execução e o
  worktree.

### Execução

`claimed -> running -> succeeded|failed|cancelled` deve ser validado. O
histórico de tentativas é preservado; uma nova tentativa cria nova execução e
não apaga a anterior.

### Concorrência de estado

- `revision` deve ser usado em todas as atualizações.
- Locks devem cobrir escrita de tarefas e execuções.
- Eventos devem registrar transições e decisões relevantes.
- O padrão continua serial (`max_jobs = 1`) até que isolamento e testes de
  concorrência comprovem segurança.

## 5. Fluxo de execução e gates

### Ordem canônica

1. Importar e validar a missão e as tarefas.
2. Criar worktree limpo a partir de `base_commit`.
3. Executar o agente no worktree.
4. Calcular diff, arquivos alterados, commits feitos pelo agente e escopo.
5. Executar checks determinísticos.
6. Executar revisão.
7. Executar segurança quando o risco exigir.
8. Coletar aprovação humana quando a política exigir.
9. Avaliar todos os gates obrigatórios.
10. Fazer merge explícito `--no-ff`.
11. Executar checks pós-merge no commit integrado.
12. Marcar `done` somente se o gate pós-merge for `PASS`.

A ordem de revisão e testes deve ser consistente em `AGENTS.md`, nos comandos
e no `@orchestrator`: testes/checks determinísticos antes da revisão; revisão
antes do merge; segurança antes do merge quando aplicável.

### Semântica dos gates

| Status | Significado |
| --- | --- |
| `PASS` | Evidência válida e vinculada ao commit correto. |
| `FAIL` | Evidência executada e reprovada. |
| `BLOCKED` | Condição impede a avaliação ou exige intervenção. |
| `NOT RUN` | Não existe evidência válida para o commit. |

`NOT RUN` nunca permite merge. Um resultado de commit diferente é tratado como
`NOT RUN` no commit atual.

### Gates obrigatórios

- `verification`: checks determinísticos da tarefa ou configuração.
- `review`: revisão de mudanças de código.
- `security`: obrigatório para tarefas de alto risco.
- `approval`: gate humano separado, nunca inferido de resultado técnico.

`approval_policy.required_gates` deve ser efetivamente aplicado. A política
padrão não pode ser permissiva por acidente.

## 6. Critérios de aceitação e evidências

Cada critério deve ter `id`, `description` e `verification`. Tipos de
verificação previstos:

- `check:<id>`: resultado de um check determinístico.
- `review`: artefato de revisão vinculado ao commit.
- `security`: artefato de segurança vinculado ao commit.
- `human`: aprovação humana explícita, quando o critério for subjetivo.

Regras:

- Critério sem verificação válida bloqueia a conclusão.
- Critério cuja evidência aponta para outro commit ou tree é `NOT RUN`.
- Texto afirmativo do agente não é evidência.
- Evidência deve registrar tarefa, execução, commit, tree, horário e caminho do
  artefato.
- Evidência ausente, malformada ou não legível resulta em `BLOCKED`.
- O resultado final deve permitir auditar por que cada critério passou ou
  falhou.

## 7. Aprovação humana

A aprovação humana é um gate separado e explícito. Ela não substitui
`verification`, `review` ou `security`.

### Quando é obrigatória

A política da tarefa deve declarar o risco e a exigência. Mudanças de alto
risco incluem, no mínimo:

- autenticação, autorização, sessões e dados de usuário;
- segredos, credenciais e configuração sensível;
- APIs externas e integrações de terceiros;
- migrações de dados, operações destrutivas e alterações irreversíveis;
- mudanças de release/deploy, ainda que fora do MVP;
- qualquer tarefa marcada explicitamente como alto risco.

### Registro mínimo

- identificador do aprovador;
- `task_id`;
- `commit`;
- `tree_hash`;
- data e hora;
- justificativa ou nota, quando aplicável;
- política ou motivo que exigiu a aprovação;

O registro deve ser vinculado ao commit e ao tree aprovados. Um novo commit
invalida a aprovação anterior. A aprovação não pode ser armazenada como um
booleano anônimo nem inferida de mensagem do agente.

## 8. Isolamento, escopo e concorrência

- Cada execução usa worktree próprio e limpo.
- `base_commit`, `head_commit`, `tree_hash` e branch devem ser registrados.
- O diff deve considerar alterações rastreadas, não rastreadas e commits
  criados pelo agente.
- O escopo deve ser validado contra o diff completo, não apenas contra o status
  não commitado.
- Caminhos protegidos devem ser bloqueados: `.juicer/`, `.git/`, arquivos de
  segredo/configuração sensível e caminhos declarados pela política.
- Commits feitos pelo agente devem ser detectados. O comportamento padrão é
  falhar a execução, salvo política explícita em contrário.
- Árvore de destino suja bloqueia a integração; alterações pré-existentes nunca
  são sobrescritas.
- O merge deve abortar sem deixar merge parcial.
- Concorrência local permanece serial por padrão. Paralelismo só pode ser
  habilitado depois de testes de isolamento, locks e evidências por execução.
- A remoção de worktree/branch não pode destruir evidência de uma tentativa
  anterior.

## 9. Revisão e segurança

### Revisão

- Obrigatória para qualquer mudança de código.
- Deve ocorrer depois dos checks determinísticos e antes do merge.
- O artefato deve conter commit, tree, escopo revisado, achados por severidade
  e veredito.
- Achado crítico impede `PASS`.
- Artefato ausente ou malformado bloqueia a integração.

### Segurança

- Obrigatória quando a política de risco exigir.
- Reutiliza o agente `@security` existente; não cria agente novo.
- O artefato deve conter commit, tree, escopo auditado, achados por severidade,
  referência OWASP quando aplicável e veredito.
- Vulnerabilidade crítica impede `PASS`.
- Segurança não pode ser substituída por revisão genérica nem por aprovação
  humana.

A revisão e a segurança são gates de evidência. O core não deve inferir
aprovação a partir de texto livre; deve validar um artefato estruturado e
vinculado ao commit correto.

## 10. Falhas, retry, pós-merge e retomada

### Retry

- Permitido para `failed` e `blocked`, não para `done`.
- Cria nova execução e preserva a anterior.
- Não apaga evidência, branch ou worktree antes de registrar a falha.
- A branch de nova tentativa deve evitar colisão com a anterior.

### Retomada

- `resume` reconcilia `in_progress` com execuções e worktrees existentes.
- Execução interrompida deve ser marcada com motivo e evidência, não apenas
  convertida em `failed`.
- Não pode iniciar duplicadamente uma tarefa já em execução.
- O próximo passo deve ser derivado do estado reconciliado.

### Conflito e pós-merge

- Conflito de merge aborta sem merge parcial e move a tarefa para `blocked`.
- Falha pós-merge move a tarefa para `blocked`, registra o commit integrado e
  exige correção ou reversão explícita.
- O estado `completed` não pode permanecer após falha pós-merge.
- Checkpoint deve registrar o próximo passo e permitir auditoria.

## 11. Contrato do harness V1 e preparação para V2

### Contrato interno mínimo

```text
discover() -> capabilities
run(request) -> result
```

`request` deve conter, no mínimo: prompt, `cwd`, agente, timeout e, quando
suportado, sessão. `result` deve conter: `ok`, `status`, `exit_code`,
`session_id`, `output`, `detail` e dados de erro.

Capabilities devem ser explícitas e comprovadas. O core não deve depender de
nomes internos de eventos, SDK ou API do OpenCode.

### Capacidades V1 no ambiente

| Capacidade | Situação | Observação |
| --- | --- | --- |
| `--version` | validada | binário 1.19.4 descoberto. |
| `run --format json` | disponível na CLI | usada pelo adaptador atual. |
| `--agent` | disponível na CLI | usada pelo adaptador atual. |
| `--dir` | disponível na CLI | necessária para fixar o worktree. |
| `--session` / `--continue` | disponível na CLI | ainda não exposta pelo adaptador. |
| `serve` / `--attach` | disponível na CLI | ainda não usada pelo adaptador. |
| Permissões granulares por ferramenta | não comprovadas | `--auto` existe, mas não deve ser padrão. |
| Cancelamento via API | não disponível no adaptador | timeout/processo são o limite atual. |
| Eventos completos de API | não usados | o adaptador lê JSONL de `run`. |
| Worktrees nativos V2 | indisponível no V1 | fallback é git CLI. |
| Compatibilidade V2 | não validada | não declarar suporte. |

### Regras

- O adaptador V1 permanece mínimo e CLI-based.
- Não adicionar SDK, eventos, permissões ou workspaces V2 ao MVP.
- Não usar `--auto` por padrão.
- Testes de contrato usam binário falso e, quando o ambiente permitir, smoke
  real.
- O smoke real deve ser isolado e não depender de estado do projeto.
- V2 futuro deve implementar o mesmo contrato, com capabilities e testes
  próprios, sem exigir mudança no core.

## 12. Agentes, comandos e documentação

- Nenhum agente novo.
- `@orchestrator` deve seguir a ordem canônica e não prometer gate que o core
  não aplica.
- `@reviewer` deve continuar sem permissão de edição.
- `@security` deve ser acionado por risco, não apenas por opção do usuário.
- `@tester` deve produzir testes determinísticos e não substituir checks do
  core.
- Comandos `/review` e `/test` devem permanecer compatíveis com o fluxo.
- `AGENTS.md` deve refletir 4.0, a ordem dos gates e a separação
  backlog/`.juicer`.
- `README.md` deve apontar para este plano e para as limitações reais.
- `STATUS.md` deve separar capacidade validada de lacuna planejada, sem
  declarar V2.

## Apêndice A — Fases, marcos e critérios de conclusão

| Fase | Tarefas | Critério de conclusão |
| --- | --- | --- |
| 1. Baseline e contrato | TASK-003 | Contrato documentado, adaptador V1 mínimo, capabilities comprovadas, testes de contrato e smoke real registrados. Nenhuma promessa V2. |
| 2. Integridade do core | TASK-004, TASK-005, TASK-006 | Transições validadas; critérios e gates efetivos; revisão/segurança com evidência; aprovação vinculada a commit/tree. |
| 3. Isolamento e recuperação | TASK-007, TASK-008 | Escopo completo, caminhos protegidos, commits do agente detectados; retry/resume e pós-merge sem `done` falso. |
| 4. Integração e documentação | TASK-009, TASK-010 | Importação validada e unidirecional; agentes, comandos, `AGENTS.md`, README e STATUS alinhados. |
| 5. Aceitação E2E | TASK-011 | Fluxo completo V1 e caminhos negativos comprovados em repositório temporário; suíte e documentação finais. |

## Apêndice B — Estimativa, premissas e incertezas

### Premissas de estimativa

- 1 dev-day = 6 horas focadas.
- Um desenvolvedor familiarizado com o core.
- Código, testes e documentação incluídos; deploy e operação não incluídos.
- OpenCode 1.19.4 disponível e suíte atual verde.
- Sem novas dependências obrigatórias.
- Sem UI, release, deploy, coordenação distribuída ou segundo harness.
- Latência/custo de modelo e espera por revisão humana não contam como esforço
  de engenharia.

### Estimativa base

| Tarefa | Esforço |
| --- | --- |
| TASK-003 | 1,5–2 dev-days |
| TASK-004 | 2–2,5 dev-days |
| TASK-005 | 3–4 dev-days |
| TASK-006 | 1–1,5 dev-day |
| TASK-007 | 2–3 dev-days |
| TASK-008 | 2–3 dev-days |
| TASK-009 | 1,5–2 dev-days |
| TASK-010 | 1–1,5 dev-day |
| TASK-011 | 2–3 dev-days |
| **Total** | **16–23 dev-days** |

A faixa é uma estimativa de planejamento, não um compromisso. O limite superior
inclui rodadas de correção e validação; o inferior assume caminho sem
redesenho.

### Incertezas que podem elevar o esforço

- Necessidade de redesenhar o formato de evidência de revisão/segurança.
- Permissões headless exigirem mudanças no adapter ou na política.
- Concorrência local revelar corrida em worktrees, locks ou eventos.
- Importação de backlog exigir migração de schema ou reconciliação explícita.
- Refatoração de testes existentes para cobrir transições e gates.
- Custo/tempo de smoke real com modelo.

### Contingência

- Base: **16–23 dev-days**.
- Com contingência de 25% para riscos acima: **20–29 dev-days**.
- V2: **4–6 dev-days** adicionais somente depois de binário/documentação
  executável e testes de capability; não entra no MVP.
- A estimativa deve ser revista após TASK-003, quando o contrato e as
  limitações reais estiverem medidos.

## Apêndice C — Riscos e mitigação

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Declarar V2 sem teste | Alto | Capabilities explícitas; V2 fora do MVP; testes de contrato. |
| Revisão/segurança subjetivas | Alto | Artefato estruturado, commit/tree, severidade e gate; humano separado. |
| Permissões headless frouxas | Alto | Não usar `--auto` por padrão; validar política restritiva; documentar limitação. |
| Merge irreversível com falha posterior | Alto | Gate pós-merge; `blocked`; reversão/correção explícita; nunca `done` falso. |
| Duas fontes de verdade | Médio | Importação validada e unidirecional; `.juicer/` canônico após importar. |
| Agente commita ou altera caminho protegido | Alto | Diff completo, detecção de HEAD/commit, caminhos protegidos e escopo efetivo. |
| Retry apaga evidência | Médio | Preservar execução/branch/worktree; nova tentativa separada. |
| Paralelismo local inseguro | Médio | Serial por padrão; habilitar só com testes de isolamento. |
| Backlog com IDs duplicados | Médio | Validar IDs, dependências e equivalência antes de importar. |
| Estimativa otimista | Médio | Revisar após TASK-003; contingência de 25%. |

## Apêndice D — Backlog proposto

| ID | Título | Prioridade | Dependências | Esforço |
| --- | --- | --- | --- | --- |
| TASK-003 | Definir contrato do harness e validar OpenCode V1 | P0 | — | 1,5–2d |
| TASK-004 | Aplicar transições e reconciliar retomada de estado | P0 | TASK-003 | 2–2,5d |
| TASK-005 | Verificar critérios, gates e evidências de revisão/segurança | P0 | TASK-003, TASK-004 | 3–4d |
| TASK-006 | Registrar aprovação humana vinculada a commit/tree | P0 | TASK-005 | 1–1,5d |
| TASK-007 | Reforçar isolamento, escopo e caminhos protegidos | P0 | TASK-003 | 2–3d |
| TASK-008 | Corrigir retry, conflitos, pós-merge e recuperação | P1 | TASK-004, TASK-007 | 2–3d |
| TASK-009 | Implementar importação unidirecional do backlog | P1 | TASK-004 | 1,5–2d |
| TASK-010 | Alinhar agentes, comandos e documentação | P1 | TASK-005, TASK-006 | 1–1,5d |
| TASK-011 | Validar fluxo E2E V1 e aceitação do MVP | P0 | TASK-003 a TASK-010 | 2–3d |

## Pendências e observações

- A implementação do MVP não foi iniciada.
- A compatibilidade V2 não foi validada e não deve ser anunciada.
- Permissões headless restritivas continuam pendentes de validação.
- O formato final dos artefatos de revisão/segurança será definido em TASK-005.
- `TASK-001` e `TASK-002` são preservadas; não são equivalentes às tarefas
  deste plano.
- Exemplos de `TASK-003` e `TASK-004` em `docs/GUIDE.md` são ilustrativos e não
  representam tarefas reais do backlog.
- O plano deve ser revisado após TASK-003 com as capacidades medidas no
  ambiente real.
