# Juicer Kit v2.3 — Guia Completo

> Um sistema operacional agnóstico de harness para desenvolvimento de software AI-native.

## 1. Introdução

Juicer Kit v2.3 é um sistema de workflow portátil para desenvolvimento de software AI-native. Ele separa o estado de workflow persistente, os contratos de workers, skills reutilizáveis e adapters específicos de cada harness.

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
│   └── workflows/
├── agents/
├── .agents/skills/
├── adapters/
├── bin/juicer
├── docs/
└── tests/
```

`.juicer/` é o estado de workflow persistente. `agents/` contém os contratos canônicos de workers. `.agents/skills/` contém as skills portáveis. `adapters/` contém as integrações com harnesses. `AGENTS.md` é o entrypoint universal de agentes do projeto. `bin/juicer` gerencia o estado de forma determinística.

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

O inicializador cria o estado `.juicer/` e sincroniza os adapters suportados.

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

O Juicer usa quatro gates explícitos:

1. **Planejamento** — a implementação só começa após a aprovação do plano.
2. **Escopo** — cada unidade tem escopo e critérios de aceitação explícitos.
3. **Verificação** — conclusão exige evidências.
4. **Ship** — ações com impacto em produção exigem aprovação humana explícita.

Comandos:

```bash
./bin/juicer approve
./bin/juicer ship-approve
```

Agentes nunca devem inferir aprovação.

A aprovação fica no estado: `./bin/juicer status` mostra `approved` e
`ship_approved`. O CLI não executa nenhuma ação de produção por si, então
as skills e workflows de release devem verificar que `ship_approved` é
`true` antes de qualquer passo com impacto em produção e parar enquanto
for `false`.

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

A v2.3 inclui:

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

## 12. CLI

```bash
./bin/juicer init
./bin/juicer status
./bin/juicer mission "Build feature X"
./bin/juicer approve
./bin/juicer start UNIT-001
./bin/juicer checkpoint executing
./bin/juicer checkpoint blocked
./bin/juicer checkpoint ready
./bin/juicer checkpoint done
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

## 13. Workflows principais

### Feature

```text
finder → analyst → architect → planner
                 ↓
         APROVAÇÃO HUMANA
                 ↓
        coder/editor → reviewer → tester → documenter
                 ↓
        APROVAÇÃO HUMANA DE SHIP
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
reviewer → tester → security (quando aplicável) → APROVAÇÃO HUMANA → devops
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

Ações destrutivas e com impacto em produção permanecem atrás de aprovação humana explícita.

Adapters de projeto são Python executável e não confiados por padrão
(veja a seção 19); carregue-os apenas em repositórios confiáveis.

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
2. Instale a v2.3.
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
