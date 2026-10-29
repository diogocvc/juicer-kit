# Plano de Implementação — Juicer Kit 4.0

**Status:** aprovado para execução; em execução (TASK-003 com validação V2
medida no working tree, aguardando revisão/integração).

**Data:** 2026-10-25 (revisão de alvo V2: 2026-10-26)

**Decisão de arquitetura:** B — revisada. O MVP usa **OpenCode 2.0/V2** como
harness-alvo, com o mesmo contrato interno mínimo de harness (`discover`/`run`)
e testes de contrato. A decisão anterior de MVP em 1.19.4/V1 com migração V2
futura está **substituída**. Compatibilidade V1 não é prometida. Binário V2
medido: `opencode v2.1.4` (2026-10-26); smoke real e capabilities registrados
em `STATUS.md`.

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

- OpenCode **2.0/V2** como harness validado (alvo único do MVP).
- Core Python stdlib já existente em `juicer/`.
- Worktrees git e branches isoladas (git CLI do core; worktree nativo V2 só
  após prova).
- Estados, transições, critérios de aceitação, gates técnicos e aprovação
  humana separada.
- Revisão obrigatória para mudanças de código.
- Segurança obrigatória para mudanças de alto risco.
- Retry, recuperação, conflitos, falha pós-merge e retomada.
- Backlog Markdown como planejamento e `.juicer/` como estado operacional
  canônico após a importação.
- Testes unitários, testes de contrato, smoke real V2 e E2E V2.
- Validação documental + real das capabilities V2 usadas pelo core.

### Fora do MVP

- Compatibilidade ou adaptador V1 paralelo; duas integrações simultâneas.
- Preview de build/URL (A15).
- Release, deploy e operações (A16–A18).
- UI, orquestração distribuída, múltiplos projetos e segundo harness.
- Sincronização bidirecional entre backlog e `.juicer/`.
- Novos agentes.
- SDK OpenCode, Code Mode e plugins V2 (somente se uma capability validada
  exigir; por padrão o adaptador permanece CLI).
- Implementação de código nesta etapa de planejamento.

### Critério de sucesso do MVP

O fluxo completo deve funcionar em um repositório temporário com o binário
**V2 real**, incluindo os caminhos negativos: gate ausente, revisão ausente,
segurança exigida e não executada, aprovação ausente, alteração fora de escopo,
commit feito pelo agente, falha pós-merge, interrupção e retry. Nenhum desses
caminhos pode resultar em `done` silencioso. A documentação final não declara
compatibilidade não comprovada (nem V1 nem V2 sem smoke associado).

## 2. Decisões e premissas

| ID | Decisão | Consequência |
| --- | --- | --- |
| D1 | Backlog Markdown é a fonte de planejamento; `.juicer/` é a fonte operacional canônica após a importação para uma missão. | A importação valida os dados. Não há sincronização bidirecional silenciosa nem sobrescrita automática de missão em andamento. |
| D2 | Preview (A15) fica fora do MVP. | A limitação deve ser explícita em `STATUS.md` e no plano. |
| D3 | Release/deploy A16–A18 ficam fora do MVP. | Nenhuma tarefa do backlog 4.0 deve prometer essas capacidades. |
| D4 | Aprovação humana é obrigatória conforme risco e política explícita da tarefa. | Aprovação não substitui gates técnicos e deve ser registrada com aprovador, tarefa, commit, tree hash, data e nota. |
| D5 | O harness alvo do MVP é **OpenCode 2.0/V2** (revisão de 2026-10-26; substitui a decisão anterior de 1.19.4/V1). | O adaptador é validado e ajustado para a CLI V2 real; capabilities V2 são medidas, não presumidas. Compatibilidade V1 não é prometida nem mantida em paralelo. Enquanto o binário V2 não estiver disponível, qualquer afirmação de compatibilidade permanece documental e não comprovada. |
| D6 | `TASK-001` e `TASK-002` são preservadas. | Novas tarefas usam `TASK-003` a `TASK-011`, sem renumerar ou reescrever o histórico existente. |
| D7 | Não criar agentes novos. | A implementação reutiliza `@orchestrator`, `@reviewer`, `@security` e `@tester` já existentes. |
| D8 | Permissões do OpenCode V2 (allow/ask/deny) são complemento, nunca substituto dos gates, evidências e aprovação do core. | O core continua dono de escopo protegido, verificação, revisão, segurança e aprovação humana, mesmo com política restritiva no harness. |
| D9 | Integração única com V2; sem duplicar o adaptador V1. | O trabalho V1 não commitado da TASK-003 é preservado e reaproveitado onde justificado (contrato, parsing, testes), mas o entregável final do MVP é o adaptador V2 validado. |

### Premissas

- Um binário OpenCode 2.0/V2 está disponível neste ambiente (medido:
  `~/.opencode/bin/opencode` = v2.1.4; alternativa via `OPENCODE_BIN`).
- O binário 1.19.4 ainda presente no registry do Zed não é alvo do MVP; a
  detecção de versão distingue V2 de V1 e degrada V1.
- A suíte atual (94 testes padrão + 1 smoke opt-in) permanece verde como linha
  de base.
- O core continua em Python stdlib, sem novas dependências obrigatórias.
- O responsável pela implementação conhece o core e pode trabalhar em uma
  única sessão por tarefa.
- O design de artefatos de revisão e segurança pode ser implementado sem criar
  um novo agente ou um serviço externo.
- O custo e a latência de chamadas reais ao modelo não entram na estimativa.

### Incertezas conhecidas

- Permissões headless da V2 com política restritiva (deny/ask em shell, edit,
  external_directory) ainda não foram validadas.
- O formato estruturado de evidência de revisão e segurança precisa ser
  desenhado e testado; texto livre de agente não é prova suficiente.
- A segurança de paralelismo local precisa ser confirmada antes de habilitar
  concorrência por padrão; revalidar `--jobs 2` com `--standalone` V2.
- A importação do backlog pode revelar necessidades de validação de IDs,
  dependências e critérios ainda não cobertas.
- Retomada real de sessão (`--session`/`--continue`) ainda não exercitada.
- Worktree nativo V2 (API `worktree.create/refresh/remove`) não substitui o
  git CLI do core sem testes de evidência e recuperação; o MVP mantém git CLI
  como caminho padrão.

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
- `juicer/harness/contract.py`: contrato interno `discover`/`run`.
- `juicer/harness/opencode.py`: adaptador OpenCode V2 (CWD + `--standalone`;
  sem `--dir`).
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

## 11. Contrato do harness e alvo V2

### Contrato interno mínimo

```text
discover() -> capabilities
run(request) -> result
```

`request` deve conter, no mínimo: prompt, `cwd`, agente, timeout e, quando
suportado, sessão. `result` deve conter: `ok`, `status`, `exit_code`,
`session_id`, `output`, `detail` e dados de erro.

Capabilities devem ser explícitas e comprovadas. O core não deve depender de
nomes internos de eventos, SDK ou API do OpenCode. O contrato detalhado está em
`docs/HARNESS_CONTRACT.md`. O contrato é agnóstico de versão; a versão entra
apenas no adaptador e no probe de capabilities.

### Capacidades V2 (medidas em 2.1.4 em 2026-10-26)

A tabela abaixo registra o que foi **medido** com o binário local e o que
permanece documental. Nada documental pode ser anunciado como suportado sem
teste associado.

| Capacidade | Situação | Observação |
| --- | --- | --- |
| Instalação/binary V2 | **medida** | `opencode v2.1.4` em `~/.opencode/bin/opencode` via `upgrade --major`. |
| `--version` | medida | Probe distingue 2.x (`v2: true`). |
| `run --format json` | medida | NDJSON com `sessionID` e `part`. |
| `--agent` | medida | Smoke e testes. |
| `--dir` | **ausente na V2** | `run --help` 2.1.4 não tem a flag; workspace fixado pelo CWD do subprocesso. |
| `--session` / `--continue` | flags medidas | Retomada real ainda não exercitada (`session_resume=false`). |
| `--standalone` | medida | Servidor privado por execução; padrão do adaptador. |
| `serve` | medida | `serve --help` responde. |
| Permissões estruturadas | documental | `permissions[]` allow/ask/deny; política restritiva headless não medida. |
| Cancelamento via API | não medida | timeout/processo é o limite atual. |
| Eventos/sessões | medida | NDJSON de `run`; parsing V2 no adaptador. |
| Worktree nativo V2 | documental (não usado) | MVP mantém git CLI do core. |
| SDK / Code Mode / plugins | fora do escopo padrão | Só entram se capability medida exigir. |
| Compatibilidade V1 | **não prometida** | D5/D9: alvo único V2; binário V1 → `degraded`. |

### Regras

- O adaptador implementa o mesmo contrato; a versão detectada alimenta
  capabilities e o `STATUS.md`.
- Instalação ou seleção do binário V2 é passo bloqueante da validação; sem
  binário V2, `discover` não pode reportar suporte V2.
- `--auto` não é usado por padrão; permissões restritivas devem ser testadas
  sem auto-approve.
- Permissões do OpenCode são barreira adicional de execução; escopo protegido,
  evidência, gates e aprovação continuam no core.
- Testes de contrato usam binário falso e, quando o ambiente permitir, smoke
  real V2.
- O smoke real deve ser isolado e não depender de estado do projeto.
- Não manter duas integrações ativas: o código V1 reaproveitado (contrato,
  parsing, testes) é refactorado para o alvo V2, não duplicado.
- Nenhuma declaração de compatibilidade V2 sem smoke e capabilities medidos.

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
- `STATUS.md` deve separar capacidade medida de lacuna planejada; com o alvo
  V2, deve registrar claramente o que foi medido com binário V2 e o que
  permanece apenas documental ou bloqueado.
- Referências a “OpenCode 1.19.4/V1” em docs e comentários do adaptador devem
  ser atualizadas na execução de TASK-003/TASK-010 para o alvo V2, sem apagar
  o histórico de medições já realizadas.

## Apêndice A — Fases, marcos e critérios de conclusão

| Fase | Tarefas | Critério de conclusão |
| --- | --- | --- |
| 1. Baseline e contrato V2 | TASK-003 | Binário V2 provisionado e detectado; contrato documentado; adaptador alinhado à CLI V2; capabilities V2 medidas; testes de contrato e smoke real V2 registrados; nenhuma promessa sem evidência. |
| 2. Integridade do core | TASK-004, TASK-005, TASK-006 | Transições validadas; critérios e gates efetivos; revisão/segurança com evidência; aprovação vinculada a commit/tree. |
| 3. Isolamento e recuperação | TASK-007, TASK-008 | Escopo completo, caminhos protegidos, commits do agente detectados; permissões V2 não confundidas com gates do core; retry/resume e pós-merge sem `done` falso. |
| 4. Integração e documentação | TASK-009, TASK-010 | Importação validada e unidirecional; agentes, comandos, `AGENTS.md`, README e STATUS alinhados ao alvo V2. |
| 5. Aceitação E2E | TASK-011 | Fluxo completo V2 e caminhos negativos comprovados em repositório temporário; suíte e documentação finais; sem declaração de compatibilidade não medida. |

## Apêndice B — Estimativa, premissas e incertezas

### Premissas de estimativa

- 1 dev-day = 6 horas focadas.
- Um desenvolvedor familiarizado com o core.
- Código, testes e documentação incluídos; deploy e operação não incluídos.
- Suíte atual verde como baseline.
- Sem novas dependências obrigatórias.
- Sem UI, release, deploy, coordenação distribuída, segundo harness ou
  integração V1 paralela.
- Latência/custo de modelo e espera por revisão humana não contam como esforço
  de engenharia.
- Provisionamento do binário V2 é esforço real e está embutido em TASK-003.

### Estimativa base (preliminar, revisar após validar V2)

| Tarefa | Esforço | Nota de impacto V2 |
| --- | --- | --- |
| TASK-003 | 2–3,5 dev-days | Provisionar V2; revalidar capabilities; adaptar adaptador/smoke. Contrato e testes V1 existentes são candidatos a reaproveitamento, **não** progresso confirmado. |
| TASK-004 | 2–2,5 dev-days | Core agnóstico; impacto V2 baixo. |
| TASK-005 | 3–4 dev-days | Core agnóstico; impacto V2 baixo. |
| TASK-006 | 1–1,5 dev-day | Core agnóstico; impacto V2 baixo. |
| TASK-007 | 2–3 dev-days | Adicionar distinção permissões V2 vs escopo/gates do core (D8). |
| TASK-008 | 2–3 dev-days | Core agnóstico; impacto V2 baixo. |
| TASK-009 | 1,5–2 dev-days | Core agnóstico; impacto V2 baixo. |
| TASK-010 | 1–1,5 dev-day | Docs/agentes alinhados ao alvo V2. |
| TASK-011 | 2,5–3,5 dev-days | E2E com binário V2 real; depende de smoke V2 da TASK-003. |
| **Total preliminar** | **17–27 dev-days** | Faixa ampla; incerteza alta até medir V2. |

**Estimativa revisada de referência: 18–28 dev-days (preliminar, incerteza
alta).** A faixa anterior de 16–23 dev-days (base V1) **não** é
automaticamente reutilizável: o alvo mudou e o binário V2 ainda não foi medido.
Revise a faixa assim que a TASK-003 concluir o smoke real V2 e registrar as
capabilities medidas.

Trabalho já realizado (contrato, testes, refatoração do adaptador, STATUS
parcial) é **candidato a reaproveitamento**; a fração estimada de ~60–70% da
TASK-003 é **preliminar e não confirmada** até diff e execução de testes após o
alvo V2. Não contabilizar como progresso concluído sem evidência.

### Decomposição do impacto

| Categoria | Trabalho | Esforço estimado |
| --- | --- | --- |
| Reaproveitável (contrato, parsing, testes de contrato, estrutura do adaptador) | já no working tree | 0d novo, se preservado |
| Adaptar/smoke V2 + provisioning | TASK-003 restante | 2–3,5d |
| Retrabalho por incompatibilidade V2 | desconhecido até smoke | 0–2d |
| Core 004–009 (baixo impacto de versão) | manter | 11,5–16d |
| Docs V2 + E2E V2 | TASK-010, TASK-011 | 3,5–5d |

### Incertezas que podem elevar o esforço

- Binário V2 indisponível ou incompatível com o ambiente de instalação.
- Flags documentadas (`--dir`, `--session`, `--standalone`) divergirem da
  ajuda real ou do comportamento headless.
- Permissões V2 exigirem reformulação do adaptador ou da política de execução.
- Serviço compartilhado da V2 interferir em worktrees concorrentes.
- Necessidade de redesenhar o formato de evidência de revisão/segurança.
- Concorrência local revelar corrida em worktrees, locks ou eventos.
- Importação de backlog exigir migração de schema ou reconciliação explícita.
- Refatoração de testes existentes para cobrir transições e gates.
- Custo/tempo de smoke real com modelo.

### Contingência

- Base preliminar: **18–28 dev-days**.
- Com contingência de 30% (incerteza V2 elevada): **~24–36 dev-days**.
- Revisão obrigatória da estimativa após a conclusão da validação V2 em
  TASK-003.
- A estimativa anterior V1 (16–23) fica registrada apenas como referência
  histórica da decisão substituída.

## Apêndice C — Riscos e mitigação

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Declarar V2 sem smoke/capabilities medidas | Alto | Capabilities explícitas (documental × medida); bloqueio até binário V2; testes de contrato. |
| Binário V2 indisponível no ambiente | Alto | Provisionamento como passo bloqueante de TASK-003; planejar sem prometer compatibilidade. |
| Reaproveitar código V1 como se fosse progresso V2 | Médio | Contabilizar só após testes verdes com alvo V2; preservar trabalho sem marcá-lo concluído. |
| Confundir permissões V2 com gates do core | Alto | D8: permissões são complemento; gates, evidência e aprovação permanecem no core e são testados. |
| Revisão/segurança subjetivas | Alto | Artefato estruturado, commit/tree, severidade e gate; humano separado. |
| Permissões headless frouxas | Alto | Não usar `--auto` por padrão; validar política restritiva V2; documentar limitação. |
| Serviço compartilhado V2 interferir em worktrees | Médio | Validar `--standalone` vs serviço em TASK-003; serial por padrão. |
| Merge irreversível com falha posterior | Alto | Gate pós-merge; `blocked`; reversão/correção explícita; nunca `done` falso. |
| Duas fontes de verdade | Médio | Importação validada e unidirecional; `.juicer/` canônico após importar. |
| Agente commita ou altera caminho protegido | Alto | Diff completo, detecção de HEAD/commit, caminhos protegidos e escopo efetivo. |
| Retry apaga evidência | Médio | Preservar execução/branch/worktree; nova tentativa separada. |
| Paralelismo local inseguro | Médio | Serial por padrão; habilitar só com testes de isolamento. |
| Backlog com IDs duplicados | Médio | Validar IDs, dependências e equivalência antes de importar. |
| Estimativa otimista pós-troca de alvo | Médio | Faixa 18–28 marcada preliminar; revisar após smoke V2; contingência 30%. |

## Apêndice D — Backlog consolidado

| ID | Título | Prioridade | Dependências | Esforço |
| --- | --- | --- | --- | --- |
| TASK-003 | Definir contrato do harness e validar OpenCode V2 | P0 | — | 2–3,5d |
| TASK-004 | Aplicar transições e reconciliar retomada de estado | P0 | TASK-003 | 2–2,5d |
| TASK-005 | Verificar critérios, gates e evidências de revisão/segurança | P0 | TASK-003, TASK-004 | 3–4d |
| TASK-006 | Registrar aprovação humana vinculada a commit/tree | P0 | TASK-005 | 1–1,5d |
| TASK-007 | Reforçar isolamento, escopo, caminhos protegidos e fronteira de permissões V2 | P0 | TASK-003 | 2–3d |
| TASK-008 | Corrigir retry, conflitos, pós-merge e recuperação | P1 | TASK-004, TASK-007 | 2–3d |
| TASK-009 | Implementar importação unidirecional do backlog | P1 | TASK-004 | 1,5–2d |
| TASK-010 | Alinhar agentes, comandos e documentação ao alvo V2 | P1 | TASK-005, TASK-006 | 1–1,5d |
| TASK-011 | Validar fluxo E2E V2 e aceitação do MVP | P0 | TASK-003 a TASK-010 | 2,5–3,5d |

`TASK-001` e `TASK-002` permanecem no backlog como exemplos preservados (D6)
e não fazem parte deste mapa de fases.

## Pendências e observações

- O alvo do MVP é **OpenCode 2.0/V2** (D5, revisão de 2026-10-26).
- Binário V2 **provisionado e medido** (`opencode v2.1.4`); smoke real V2
  passou (2026-10-26). `--dir` não existe na V2; isolamento via CWD +
  `--standalone`.
- TASK-003 permanece `In Progress` até integração/revisão humana; critérios
  de capabilities e smoke V2 foram cumpridos no working tree.
- Permissões restritivas em headless permanecem pendentes de validação.
- O formato final dos artefatos de revisão/segurança será definido em
  TASK-005.
- `TASK-001` e `TASK-002` são preservadas; não são equivalentes às tarefas
  deste plano.
- A estimativa 18–28 dev-days permanece preliminar; revisar após TASK-003
  concluir integração e revisão.
- `STATUS.md` e `docs/HARNESS_CONTRACT.md` foram atualizados com medições
  V2 (2026-10-26).
