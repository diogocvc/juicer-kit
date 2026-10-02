# Juicer Kit v2.4.0 — Guia Completo

> Um sistema operacional agnóstico de harness para desenvolvimento de software AI-native.

## 1. Introdução

Juicer Kit v2.4.0 é um sistema de workflow portátil para desenvolvimento de software AI-native. Ele separa o estado de workflow persistente, os contratos de workers, skills reutilizáveis e adapters específicos de cada harness.

O princípio central é: **o usuário é dono da missão; os agentes executam o trabalho dentro dela.**

## 2. Arquitetura

```text
                         HUMAN
                           |
                        MISSION
                           |
                       .juicer/
                           |
              +------------+------------+
              |                         |
           WORKERS                   SKILLS
           agents/               .agents/skills/
              |                         |
              +------------+------------+
                           |
                    ADAPTER CONTRACT
                           |
       +---------+---------+---------+---------+
       |         |         |         |         |
     Codex    OpenCode   Claude    Cursor     Zed
                           |
                       MODEL(S)
```

O core portátil é `.juicer/`, `agents/`, `.agents/skills/`, `AGENTS.md` e as definições de workflow. Adapters traduzem esse core em mecanismos de execução específicos de cada harness.

Adicionar uma futura ferramenta como o Gemini CLI deve normalmente significar adicionar `adapters/gemini-cli/`, sem alterar o workflow core.

## 3. Estrutura do repositório

```text
juicer-kit/
├── AGENTS.md
├── README.md
├── kit.yaml
├── VERSION
├── .juicer/
│   ├── mission.md
│   ├── plan.md
│   ├── state.json
│   ├── handoff.md
│   ├── decisions.md
│   ├── learnings.md
│   ├── templates/
│   └── workflows/
├── agents/
├── .agents/skills/
├── adapters/
├── bin/juicer
├── docs/
└── tests/
```

`.juicer/` é o estado de workflow persistente. `agents/` contém os contratos canônicos de workers. `.agents/skills/` contém as skills portáveis. `adapters/` contém as integrações com harnesses. `AGENTS.md` é o entrypoint universal de agentes do projeto. `bin/juicer` gerencia o estado de forma determinística.

`.juicer/templates/` guarda os arquivos prístines que `init` e
`juicer mission` copiam. Os arquivos `.juicer/*.md` no nível superior são
estado de workflow vivo — neste repositório eles são os do próprio kit e
nunca servem de modelo para outro projeto.

## 4. Pré-requisitos

Obrigatório:

- projeto Git
- terminal
- um harness de desenvolvimento AI capaz de ler instruções do projeto e/ou executar prompts
- Python 3 para o CLI

A arquitetura foi desenhada para suportar Codex, OpenCode, Claude Code, Cursor, Zed e ferramentas futuras.

Modelos não são definidos nos contratos dos workers. A seleção de modelo/provider pertence à camada do harness.

## 5. Instalação

```bash
./bin/juicer init
./bin/juicer status
./bin/juicer adapters
```

O inicializador cria o estado `.juicer/` e sincroniza os adapters
suportados. Ele se recusa a rodar em um subdiretório de um workspace
Juicer existente, a menos que você passe `--nested`, que cria ali um
workspace separado de propósito, em vez de conectar silenciosamente duas
raízes.

O bloco gerenciado que ele escreve no `.gitignore` lista os caminhos
exatos que o Juicer gera (`.claude/agents/`, `.opencode/agents/`, …),
não diretórios inteiros do harness — assim a configuração que é sua
(`opencode.json`, `.claude/settings.json`, `.mcp.json`) continua
versionada. Rodar `init` de novo reescreve um bloco obsoleto no lugar e
não toca em nenhuma outra linha.

Adapters do diretório `adapters/` do projeto são Python executável e não
são carregados por padrão; use `--trust-project-adapters` (ou
`JUICER_TRUST_PROJECT_ADAPTERS=1`) — veja a seção 19.

A árvore canônica de skills portáveis é `.agents/skills/`.

## 6. Modelo de missão

Uma missão contém:

- objetivo;
- critérios de sucesso;
- restrições;
- escopo;
- decisões;
- unidade de execução atual;
- estado de aprovação.

Ciclo de vida:

```text
idle
  ↓
planning
  ↓ aprovação humana
ready
  ↓
executing
  ├── checkpoint
  ├── blocked
  └── verification
        ↓
       done
```

Uma sessão de chat é temporária. O estado da missão é persistente. Uma sessão nova deve ler `.juicer/mission.md`, `.juicer/plan.md` e `.juicer/handoff.md`.

## 7. Controle humano e gates de aprovação

O Juicer define quatro gates. O que realmente te impede varia por gate:

- **mecânico** — `bin/juicer` se recusa e sai com código 1;
- **convenção** — nada no CLI te impede; só humanos e agentes sustentam;
- **dependente do harness** — o Juicer escreve configuração que um
  harness *pode* acatar, mas não consegue verificar (`security.md` §6);
- **evidência registrada** — o Juicer persiste um registro que um
  comando posterior lê. Um registro nunca é uma barreira.

| # | Gate | Tipo | O que realmente te impede |
|---|---|---|---|
| 1 | Planejamento (**Recorded Plan Approval**) | mecânico | `juicer start` se recusa sem um registro de aprovação de plano válido |
| 2 | Escopo | convenção | nada — o CLI grava apenas o id da unidade |
| 3 | Verificação | convenção | nada — o CLI nunca confere se os testes rodaram |
| 4 | Ship (**Recorded Ship Approval**) | gate mecânico + evidência registrada | `juicer ship-approve` grava um registro ligado ao plano, à missão, à unidade e (num repositório git) ao estado do código; `juicer status` o reporta. O CLI em si não executa nenhum comando de produção, então a skill de release que confere a flag é uma regra, não uma barreira |

Comandos:

```bash
./bin/juicer approve        # Recorded Plan Approval
./bin/juicer ship-approve   # Recorded Ship Approval
```

Ambos exigem uma identidade: o usuário do sistema quando rodados em um
TTY, ou um `--by=<id>` explícito (por exemplo `--by=ci`). Sem um dos
dois, saem com código 1. O registro guarda `by`, `at`, `via`, `revision`
e o digest do alvo aprovado. Ele prova *que um registro foi gravado por
um processo que se identificou* — **não** prova que um humano em
particular estava no teclado. Essa distinção é exatamente a diferença
entre uma aprovação *registrada* e uma *autenticada*: o Juicer não faz
autenticação. Um harness pode adicionar sua própria confirmação na
frente desses comandos; o Juicer nem fornece nem verifica isso. Veja
[`security.md`](security.md) §3.

A aprovação cobre o conteúdo que ela aprovou. Editar
`.juicer/plan.md` ou `.juicer/mission.md` depois invalida o registro até
que `juicer approve` rode de novo; `juicer status` reporta `invalidated`
e o motivo. A aprovação de ship grava ainda o `code_binding`: `sha`
quando o git a ligou ao commit e à árvore de trabalho, `failed` quando o
git falhou, `none` fora de um repositório git — e nos dois últimos casos
`juicer status` avisa que a aprovação **não** cobre as mudanças de
código.

Agentes nunca devem inferir aprovação.

A aprovação fica no estado: `./bin/juicer status` mostra `approved` e
`ship_approved` juntos com seus registros. O CLI não executa nenhuma
ação de produção por si, então as skills e workflows de release devem
verificar que `ship_approved` é `true` antes de qualquer passo com
impacto em produção e parar enquanto for `false`. Essa última instrução
governa o comportamento do agente; não é um mecanismo capaz de parar um
processo sozinho.

## 8. Workers

| Worker | Responsabilidade |
|---|---|
| `finder` | Reconhecimento do repositório |
| `analyst` | Comportamento existente, dependências e restrições |
| `researcher` | Pesquisa técnica externa |
| `architect` | Arquitetura da solução |
| `planner` | Plano de implementação atômico |
| `coder` | Nova implementação |
| `editor` | Modificação segura de código existente |
| `fixer` | Correção estreita de bug conhecido |
| `refactorer` | Refatoração estrutural |
| `reviewer` | Revisão de código |
| `tester` | Testes e verificação |
| `debugger` | Investigação de causa raiz |
| `security` | Auditoria de segurança |
| `documenter` | Documentação técnica |
| `devops` | Infraestrutura e release |
| `optimizer` | Trabalho de performance baseado em evidências |

Workers são de primeira classe e podem ser invocados diretamente. A orquestração nativa é opcional.

## 9. Skills

As skills canônicas ficam em `.agents/skills/`.

O kit inclui:

```text
mission-control
feature-development
code-review
test-and-verify
security-review
context-management
ship
```

Skills são playbooks reutilizáveis e devem permanecer agnósticas de harness.

## 10. Contrato de Adapter

O contrato está documentado em `docs/adapter-contract.md`.

Conceitualmente:

```text
discover()
install()
sync()
invoke(worker)
capabilities()
```

As capabilities podem incluir:

```yaml
skills: true
subagents: true
parallel_agents: true
human_approval: true
persistent_context: true
```

Capabilities descrevem o harness; elas não redefinem o workflow do Juicer.

Se subagentes nativos não estiverem disponíveis, um adapter deve recorrer à execução direta dos workers em vez de quebrar o core.

## 11. Adapters atuais

### Codex

Usa `AGENTS.md` e `.agents/skills/`, com capacidades nativas de agent/subagent onde disponíveis.

### OpenCode

Pode usar agentes e skills nativos. Eles são mecanismos de execução, não a fonte de verdade.

### Claude Code

Pode usar subagentes e skills nativos. O estado persistente do Juicer permanece em `.juicer/`.

### Cursor

Pode consumir skills portáveis e usar mecanismos nativos de agentes.

### Zed

Pode usar seu ambiente nativo de agentes ou um agente ACP externo. O estado do Juicer permanece independente do Zed.

### Permissões geradas

Cada adapter renderiza o campo canônico `access:` de cada worker no
esquema de permissão próprio daquele harness; `docs/adapter-contract.md`
tem o mapeamento de chaves por harness e `docs/security.md` §6 diz
quais desses o harness realmente aplica. Os arquivos gerados são
ignorados pelo git, então o `juicer sync` avisa no stderr sempre que a
configuração de permissão que ele está reescrevendo muda — revise esse
diff antes de publicar.

## 12. CLI

```bash
./bin/juicer init
./bin/juicer status
./bin/juicer session
./bin/juicer mission "Build feature X"
./bin/juicer approve
./bin/juicer start UNIT-001
./bin/juicer checkpoint executing
./bin/juicer checkpoint blocked
./bin/juicer checkpoint ready
./bin/juicer checkpoint done
./bin/juicer checkpoint ready --note "registre por que este checkpoint aconteceu"
./bin/juicer handoff
./bin/juicer ship-approve
./bin/juicer finish
./bin/juicer adapters
./bin/juicer capabilities codex
./bin/juicer worker reviewer
./bin/juicer sync codex
./bin/juicer install codex
./bin/juicer invoke codex reviewer --unit UNIT-001
```

O CLI não chama um LLM. Ele gerencia estado de forma determinística enquanto o harness ativo executa o trabalho de IA. Os comandos de gate validam o estado do workflow primeiro e saem com código 1 em uma transição ilegal; `juicer status` lista os comandos disponíveis no estado atual.

`juicer status` é somente leitura: ele nunca cria `.juicer/mission.md`
nem reescreve `state.json`, e imprime os vereditos de aprovação de plano
e de ship (com o motivo de qualquer invalidação) no stderr enquanto o
stdout permanece JSON.

O marcador de frescor em `.juicer/handoff.md` é carimbado por
`juicer init` e `juicer handoff`; `juicer checkpoint --note` acrescenta
uma entrada no Checkpoint log e atualiza o marcador. Quando o marcador
fica atrás de `state.json`, `juicer status` imprime uma nota — apenas
informativa. A narrativa nunca sobrepõe o estado de máquina:
`state.json` sempre prevalece.

`juicer sync <adapter>|all` regenera os espelhos do harness de forma
idempotente. `--dry-run` imprime o plano e não muda nada, `--check`
imprime o plano e sai com código 1 se houver algo pendente (o gate de
deriva do CI), e `--force` também remove arquivos obsoletos modificados
pelo usuário. `juicer init --nested` cria uma raiz de workspace separada
num subdiretório de um workspace existente; sem a flag, `init` se
recusa.

Em um repositório git, `juicer init` também instala um guard
`pre-commit` que recusa commits diretos em `main` ou `master`. Ele
acrescenta um bloco marcado ao `.git/hooks/pre-commit` do próprio
repositório: o conteúdo de hooks existente é preservado e
`core.hooksPath` nunca é definido. Escapes: `git commit --no-verify`,
`JUICER_NO_GIT_GUARD=1` e `juicer init --no-git-guard` (pula a
instalação).

## 13. Workflows principais

### Feature

```text
finder → analyst → architect → planner
                 ↓
          RECORDED PLAN APPROVAL
                 ↓
        coder/editor → reviewer → tester → documenter
                 ↓
        RECORDED SHIP APPROVAL
                 ↓
             devops
```

Nem toda feature precisa de todos os workers.

### Correção de bug

```text
finder → debugger → fixer → reviewer → tester
```

### Refatoração

```text
finder → analyst → refactorer → reviewer → tester
```

### Release

```text
reviewer → tester → security (quando aplicável) → RECORDED SHIP APPROVAL → devops
```

Nos diagramas acima, `devops` **antes** da aprovação de ship é build e
package; **depois** dela, apenas deploy ou release. `ship-approve` vincula
`git status --porcelain` (`.juicer/` excluído), então um artefato criado
depois da aprovação a invalida:

```text
build/package < ship-approve < publish/deploy/release
```

Workflows são estruturas de controle, não enxames autônomos obrigatórios.

## 14. Múltiplos harnesses

Uma missão pode começar no OpenCode:

```text
finder → architect → planner
```

e continuar no Codex depois.

A nova sessão lê:

```text
AGENTS.md
.juicer/
.agents/skills/
```

O invariante é:

```text
mesma missão
mesmo plano
mesmos critérios de aceitação
mesmos contratos de workers
mesmo estado
```

Harness e modelo são camadas de execução substituíveis.

## 15. Contexto e otimização de tokens

Prefira:

```text
missão
+
unidade ativa
+
código relevante
+
skill relevante
+
verificação
```

Evite dumps do repositório inteiro, documentação não relacionada, explicações repetidas, carregar todos os workers ou executar todos os agentes disponíveis.

Antes de encerrar uma sessão longa, atualize `.juicer/handoff.md` com o que mudou, o que foi verificado, o que resta, bloqueios e a próxima ação.

Coloque descobertas reutilizáveis em `.juicer/learnings.md`.

## 16. Segurança

Use `security` para autenticação, autorização, pagamentos, dados pessoais, segredos, APIs públicas, integrações externas, infraestrutura e mudanças de permissão.

Um relatório de segurança útil contém:

```text
Descoberta
Severidade
Evidência
Impacto
Remediação
```

Nunca faça commit de chaves de API, chaves privadas, senhas, tokens ou credenciais de produção.

Ações destrutivas e com impacto em produção permanecem atrás de um
registro de aprovação explícito (`juicer approve`, `juicer ship-approve`).
O registro nomeia uma identidade; ele não autentica uma pessoa, e é o
harness/OS que de fato pode recusar o comando. Veja
[`security.md`](security.md).

Adapters de projeto são Python executável e não confiados por padrão
(veja a seção 19); carregue-os apenas em repositórios confiáveis.

O `juicer sync` tira uma fotografia da configuração de permissão de cada
arquivo de harness gerado que está prestes a reescrever e avisa no
stderr quando ela muda. Esses espelhos são ignorados pelo git, então sem
esse aviso uma mudança no que o harness permitiria passaria invisível em
um pull request. O aviso reporta a mudança, não um julgamento sobre ela
— revise o diff antes de publicar.

`juicer capabilities` imprime o que o adapter **declara**; `discover`
reporta o que o Juicer observou (binário no `PATH`, versão). Uma
declaração é metadado, não uma verificação de que o harness a acata.

## 17. Solução de problemas

### Worker não encontrado

```bash
ls agents/
./bin/juicer worker reviewer
```

### Skills não descobertas

```bash
ls .agents/skills/
```

Depois, inspecione o `SKILL.md` relevante e sincronize o adapter apropriado.

### Delegação do harness quebra

Não mova o estado do workflow para dentro do harness. Verifique `.juicer/`, `agents/` e `.agents/skills/`, e então inspecione o adapter.

### Agente sem contexto

Leia:

```text
.juicer/mission.md
.juicer/plan.md
.juicer/handoff.md
```

### Missão bloqueada

```bash
./bin/juicer status
```

Inspecione `.juicer/plan.md` e resolva o gate. Não force uma mudança de estado.

### Testes passam, mas a tarefa está incompleta

Testes são evidência, não a definição de conclusão. Compare a implementação com os critérios de aceitação da unidade.

## 18. Exemplos práticos

### Nova feature

```bash
./bin/juicer mission "Add Stripe subscriptions"
```

Use `finder`, `analyst`, `architect` e `planner`. Revise `.juicer/plan.md`, aprove-o e execute as unidades com os workers apropriados.

### Worker direto

> Execute o worker `reviewer` sobre o diff atual. Não modifique arquivos.

Nenhum orquestrador é necessário.

### Trocar de harness

Comece no OpenCode e depois abra o mesmo repositório no Codex. Leia `AGENTS.md` e `.juicer/`; continue do estado persistido.

### Performance

Use o `optimizer`:

```text
baseline → profile → bottleneck → change → benchmark → compare
```

Nunca otimize apenas por intuição.

## 19. Estendendo o Juicer Kit

### Adicionar um worker

Crie `agents/my-worker.md` com objetivo, contrato de operação, escopo e saída.

### Adicionar uma skill

Crie `.agents/skills/my-skill/SKILL.md`. Mantenha-a portável.

### Adicionar um adapter

Crie:

```text
adapters/my-harness/
├── adapter.py
├── adapter.yaml
└── README.md
```

Implemente o contrato de adapter.

Adapters de projeto são Python executável e **não são carregados por
padrão**. Use `--trust-project-adapters` (ou defina
`JUICER_TRUST_PROJECT_ADAPTERS=1`) em `juicer sync`/`adapters`/etc. para
carregá-los — veja a seção `Trust` de `docs/adapter-contract.md`.

### Adicionar um workflow

Crie `.juicer/workflows/my-workflow.md`. Workflows devem descrever processo, não comandos específicos de fornecedor.

Direção de dependência preferida:

```text
core → adapter contract → adapter → harness
```

e não:

```text
core → OpenCode
core → Claude
core → Cursor
```

## 20. Migração da v1

A v2 substitui a arquitetura anterior centrada no OpenCode.

1. Faça backup do projeto.
2. Instale a v2.4.0.
3. Converta itens ativos do backlog em `.juicer/plan.md`.
4. Mova decisões duráveis para `.juicer/decisions.md`.
5. Mova conhecimento reutilizável para `.juicer/learnings.md`.
6. Execute `./bin/juicer init`.
7. Sincronize o harness atual.
8. Teste um worker direto.
9. Teste um workflow completo.
10. Teste o retomar de uma sessão nova.
11. Remova a v1 apenas após a verificação.

O backlog da v1 não é a nova fonte de verdade. `.juicer/` é.

## 21. Regras de contribuição

1. O repositório é a fonte de verdade.
2. Workers são independentes.
3. Skills são portáveis.
4. Adapters são finos.
5. Modelos são substituíveis.
6. Harnesses são substituíveis.
7. O usuário controla os gates de aprovação.
8. Conclusão exige evidências.
9. O contexto permanece pequeno e intencional.
10. Novas ferramentas normalmente exigem um novo adapter, não uma nova arquitetura de workflow.

## Modelo mental final

```text
                  HUMAN
                    |
                 MISSION
                    |
                 .juicer/
                    |
          +---------+---------+
          |                   |
       WORKERS             SKILLS
       agents/          .agents/skills/
          |                   |
          +---------+---------+
                    |
              ADAPTER LAYER
                    |
     +------+------+------+------+------+
     |      |      |      |      |      |
   Codex OpenCode Claude Cursor  Zed   ...
                    |
                 MODEL(S)
```

**Juicer é o workflow. Workers são o time. Skills são capacidades reutilizáveis. Adapters são traduções. Modelos são motores substituíveis. O usuário continua no controle.**
