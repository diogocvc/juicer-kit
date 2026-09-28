# Juicer Kit v2.3 — Guia Completo

> Um sistema operacional agnóstico de harness para desenvolvimento de software AI-native.

## 1. Introdução

Juicer Kit v2.3 is a portable workflow system for AI-native software development. It separates persistent workflow state, worker contracts, reusable skills, and harness-specific adapters.

O princípio central é: **o usuário é dono da mission; os agentes executam o trabalho dentro dela.**

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

O core portátil é `.juicer/`, `agents/`, `.agents/skills/`, `AGENTS.md`, and the workflow definitions. Adapters translate this core into harness-specific execution mechanisms.

Adding a future tool such as Gemini CLI should normally mean adding `adapters/gemini-cli/` without changing the core workflow.

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

`.juicer/` is persistent workflow state. `agents/` contains canonical worker contracts. `.agents/skills/` contains portable skills. `adapters/` contains harness integrations. `AGENTS.md` is the universal project-level agent entrypoint. `bin/juicer` manages deterministic state.

## 4. Pré-requisitos

Obrigatório:

- Git project
- terminal
- an AI development harness capable of reading project instructions and/or executing prompts
- Python 3 for the CLI

A arquitetura foi desenhada para suportar Codex, OpenCode, Claude Code, Cursor, Zed, and future tools.

Modelos não são definidos nos contratos dos workers. A seleção de modelo/provider pertence à camada do harness.

## 5. Instalação

```bash
./bin/juicer init
./bin/juicer status
./bin/juicer adapters
```

The initializer creates the `.juicer/` state and synchronizes supported adapters.

Adapters do diretório `adapters/` do projeto são Python executável e não
são carregados por padrão; use `--trust-project-adapters` (ou
`JUICER_TRUST_PROJECT_ADAPTERS=1`) — veja a seção 19.

The canonical portable skill tree is `.agents/skills/`.

## 6. Modelo de Mission

A mission contains:

- objective;
- success criteria;
- constraints;
- scope;
- decisions;
- current execution unit;
- approval state.

Lifecycle:

```text
idle
  ↓
planning
  ↓ human approval
ready
  ↓
executing
  ├── checkpoint
  ├── blocked
  └── verification
        ↓
       done
```

A chat session is temporary. Mission state is persistent. A fresh session should read `.juicer/mission.md`, `.juicer/plan.md`, and `.juicer/handoff.md`.

## 7. Controle humano e gates de aprovação

Juicer uses four explicit gates:

1. **Planning** — implementation starts only after plan approval.
2. **Scope** — every unit has explicit scope and acceptance criteria.
3. **Verification** — completion requires evidence.
4. **Ship** — production-impacting actions require explicit human approval.

Commands:

```bash
./bin/juicer approve
./bin/juicer ship-approve
```

Agents must never infer approval.

A aprovação fica no estado: `./bin/juicer status` mostra `approved` e
`ship_approved`. O CLI não executa nenhuma ação de produção por si, então
as skills e workflows de release devem verificar que `ship_approved` é
`true` antes de qualquer passo com impacto em produção e parar enquanto
for `false`.

## 8. Workers

| Worker | Responsibility |
|---|---|
| `finder` | Repository reconnaissance |
| `analyst` | Existing behavior, dependencies and constraints |
| `researcher` | External technical research |
| `architect` | Solution architecture |
| `planner` | Atomic implementation plan |
| `coder` | New implementation |
| `editor` | Safe existing-code modification |
| `fixer` | Narrow known bug correction |
| `refactorer` | Structural refactoring |
| `reviewer` | Code review |
| `tester` | Tests and verification |
| `debugger` | Root-cause investigation |
| `security` | Segurança audit |
| `documenter` | Technical documentation |
| `devops` | Infrastructure and release |
| `optimizer` | Evidence-based performance work |

Workers are first-class and can be invoked directly. Native orchestration is optional.

## 9. Skills

Canonical skills live under `.agents/skills/`.

v2.3 includes:

```text
mission-control
feature-development
code-review
test-and-verify
security-review
context-management
ship
```

Skills are reusable playbooks and should remain harness-agnostic.

## 10. Contrato de Adapter

The contract is documented in `docs/adapter-contract.md`.

Conceptually:

```text
discover()
install()
sync()
invoke(worker)
capabilities()
```

Capabilities may include:

```yaml
skills: true
subagents: true
parallel_agents: true
human_approval: true
persistent_context: true
```

Capabilities describe the harness; they do not redefine the Juicer workflow.

If native subagents are unavailable, an adapter should fall back to direct worker execution rather than breaking the core.

## 11. Adapters atuais

### Codex

Uses `AGENTS.md` and `.agents/skills/`, with native agent/subagent capabilities where available.

### OpenCode

Can use native agents and skills. They are execution mechanisms, not the source of truth.

### Claude Code

Can use native subagents and skills. Persistent Juicer state remains in `.juicer/`.

### Cursor

Can consume portable skills and use native agent mechanisms.

### Zed

Can use its native agent environment or an external ACP agent. Juicer state remains independent of Zed.

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

The CLI does not call an LLM. It manages deterministic state while the active harness executes AI work. Gate commands validate the workflow state first and exit 1 on an illegal transition; `juicer status` lists the commands available in the current state.

## 13. Workflows principais

### Feature

```text
finder → analyst → architect → planner
                 ↓
          HUMAN APPROVAL
                 ↓
        coder/editor → reviewer → tester → documenter
                 ↓
        HUMAN SHIP APPROVAL
                 ↓
             devops
```

Not every feature needs every worker.

### Bug fix

```text
finder → debugger → fixer → reviewer → tester
```

### Refactor

```text
finder → analyst → refactorer → reviewer → tester
```

### Release

```text
reviewer → tester → security (when applicable) → HUMAN APPROVAL → devops
```

Workflows are control structures, not mandatory autonomous swarms.

## 14. Múltiplos harnesses

A mission can start in OpenCode:

```text
finder → architect → planner
```

and continue in Codex later.

The new session reads:

```text
AGENTS.md
.juicer/
.agents/skills/
```

The invariant is:

```text
mesma mission
mesmo plano
mesmos critérios de aceitação
mesmos contratos de workers
mesmo estado
```

Harness e modelo são camadas de execução substituíveis.

## 15. Contexto e otimização de tokens

Prefer:

```text
mission
+
active unit
+
relevant code
+
relevant skill
+
verification
```

Avoid entire repository dumps, unrelated documentation, repeated explanations, loading every worker, or executing every available agent.

Before ending a long session, update `.juicer/handoff.md` with what changed, what was verified, what remains, blockers, and next action.

Put reusable discoveries in `.juicer/learnings.md`.

## 16. Segurança

Use `security` for authentication, authorization, payments, personal data, secrets, public APIs, external integrations, infrastructure, and permission changes.

A useful security report contains:

```text
Finding
Severity
Evidence
Impact
Remediation
```

Never commit API keys, private keys, passwords, tokens or production credentials.

Destructive and production-impacting actions remain behind explicit human approval.

Adapters de projeto são Python executável e não confiados por padrão
(veja a seção 19); carregue-os apenas em repositórios confiáveis.

## 17. Troubleshooting

### Worker not found

```bash
ls agents/
./bin/juicer worker reviewer
```

### Skills not discovered

```bash
ls .agents/skills/
```

Then inspect the relevant `SKILL.md` and sync the appropriate adapter.

### Harness delegation breaks

Do not move workflow state into the harness. Check `.juicer/`, `agents/`, and `.agents/skills/`, then inspect the adapter.

### Agent has no context

Read:

```text
.juicer/mission.md
.juicer/plan.md
.juicer/handoff.md
```

### Mission is blocked

```bash
./bin/juicer status
```

Inspect `.juicer/plan.md` and resolve the gate. Do not force a status change.

### Tests pass but the task is incomplete

Tests are evidence, not the definition of completion. Compare the implementation with the unit's acceptance criteria.

## 18. Exemplos práticos

### New feature

```bash
./bin/juicer mission "Add Stripe subscriptions"
```

Use `finder`, `analyst`, `architect`, and `planner`. Review `.juicer/plan.md`, approve it, and execute units with the appropriate workers.

### Direct worker

> Run the `reviewer` worker against the current diff. Do not modify files.

No orchestrator is required.

### Switch harness

Start in OpenCode, then open the same repository in Codex. Read `AGENTS.md` and `.juicer/`; continue from persisted state.

### Performance

Use `optimizer`:

```text
baseline → profile → bottleneck → change → benchmark → compare
```

Never optimize only from intuition.

## 19. Estendendo o Juicer Kit

### Add a worker

Create `agents/my-worker.md` with objective, operating contract, scope and output.

### Add a skill

Create `.agents/skills/my-skill/SKILL.md`. Keep it portable.

### Add an adapter

Create:

```text
adapters/my-harness/
├── adapter.py
├── adapter.yaml
└── README.md
```

Implement the adapter contract.

Adapters de projeto são Python executável e **não são carregados por
padrão**. Use `--trust-project-adapters` (ou defina
`JUICER_TRUST_PROJECT_ADAPTERS=1`) em `juicer sync`/`adapters`/etc. para
carregá-los — veja a seção `Trust` de `docs/adapter-contract.md`.

### Add a workflow

Create `.juicer/workflows/my-workflow.md`. Workflows should describe process, not vendor-specific commands.

Preferred dependency direction:

```text
core → adapter contract → adapter → harness
```

not:

```text
core → OpenCode
core → Claude
core → Cursor
```

## 20. Migração da v1

v2 replaces the previous OpenCode-centered architecture.

1. Back up the project.
2. Install v2.3.
3. Convert active backlog items into `.juicer/plan.md`.
4. Move durable decisions into `.juicer/decisions.md`.
5. Move reusable knowledge into `.juicer/learnings.md`.
6. Run `./bin/juicer init`.
7. Sync the current harness.
8. Test one direct worker.
9. Test one complete workflow.
10. Test resuming from a fresh session.
11. Remove v1 only after verification.

The v1 backlog is not the new source of truth. `.juicer/` is.

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

## Final mental model

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
