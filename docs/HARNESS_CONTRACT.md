# Harness Contract — Juicer Kit 4.0

Contrato interno mínimo entre o core do Juicer e qualquer adaptador de harness.
O core é dono de estado, escopo, evidências, gates e integração. O harness
apenas descobre capacidades, executa uma solicitação e devolve um resultado
normalizado.

## Protocolo

```text
discover(explicit=None, timeout=20) -> capability report
run(ExecutionRequest, binary=None) -> ExecutionResult
```

Implementação de referência: `juicer/harness/contract.py` e
`juicer/harness/opencode.py` (alvo MVP: OpenCode 2.x/V2).

## Descoberta

`discover` retorna um objeto com:

- `harness`: nome do adaptador.
- `binary`: caminho do binário ou `None`.
- `version`: versão detectada ou `None`.
- `status`: `supported`, `degraded` ou `unsupported`.
- `detail`: explicação legível do probe.
- `capabilities`: mapa de capacidades comprovadas.

O adaptador usa `--version` para provar a existência do binário e se ele é V2
(`v2: true` a partir de `2.x`). `run --help`/`serve --help` provam flags. Uma
flag detectada na ajuda não prova que o modelo ou provider estão disponíveis;
isso exige smoke separado.

Binário não-V2 pode ser detectado, mas é reportado como `degraded` (não é o
alvo do MVP).

### Capabilities

| Campo | Significado |
| --- | --- |
| `version_probe` | `--version` respondeu com sucesso. |
| `v2` | Versão detectada é 2.x (alvo do MVP). |
| `run` | `run --help` respondeu com sucesso. |
| `run_json` | `--format` com `json` detectado na ajuda. |
| `agent_flag` | `--agent` detectado na ajuda. |
| `dir_flag` | `--dir` detectado; **ausente na V2 medida**. Campo histórico, relevante apenas para diagnóstico de binários V1. |
| `session_flag` | `--session` detectado na ajuda. |
| `session_resume` | Retomada de sessão comprovada; ainda `false` até probe real. |
| `continue_flag` | `--continue` detectado na ajuda. |
| `standalone_flag` | `--standalone` detectado (V2); padrão do adaptador para isolar sessões. |
| `server` | `serve --help` respondeu com sucesso. |
| `auto_flag` | `--auto` existe, mas não é usado por padrão. |
| `permissions` | Política granular documental; medição pendente (`unknown`). |
| `cancel` | Forma de cancelamento; adapter usa timeout/processo. |
| `events` | Formato de saída; `jsonl-stream` (eventos V2 com `part`). |
| `worktree` | Isolamento; `git-cli` no core. |

### Capacidades medidas (OpenCode 2.2.7, 2026-11-12)

| Capacidade | Medida |
| --- | --- |
| `run` / `run_json` / `agent_flag` / `session_flag` / `continue_flag` / `auto_flag` | presentes |
| `standalone_flag` | presente |
| `dir_flag` | **ausente** — workspace fixado pelo `cwd` e pelo `PWD` do processo |
| Eventos | NDJSON com `sessionID` e `part.type=text` |
| Resolução de projeto | **`PWD`**; em 2.2.7 o `cwd` do subprocesso sozinho não reposiciona o agente. O adaptador fixa ambos |
| Chamada de modelo | **parcialmente medida**: `run` + checks + `integrate` + pós-merge passaram com modelo free em 2026-11-12; `review-run`/`security-run` ao vivo não foram reexecutados após o fix de `PWD` e ficaram bloqueados por quota/limite do provider (HTTP 402/429) |

Medição anterior, mantida como histórico: OpenCode 2.1.4 (2026-10-26) com a
mesma superfície de flags e eventos acima.

## Execução

`ExecutionRequest` contém:

- `prompt`: texto não vazio.
- `cwd`: diretório de trabalho (worktree); no V2 é a âncora de projeto, junto
  com `PWD` (ver abaixo).
- `agent`: agente opcional.
- `timeout`: segundos positivos.
- `session_id`: sessão opcional, quando suportada.
- `extra_args`: argumentos adicionais explícitos.

O adaptador V2 monta o comando com `run`, `--format json`, `--agent`,
`--standalone` (quando a flag existe) e, quando solicitado, `--session`. Não
passa `--dir` na V2. `--auto` não é adicionado por padrão. O subprocesso roda
com `cwd=request.cwd` **e** `PWD=request.cwd`: OpenCode resolve o projeto por
`PWD`, e um `cwd` de subprocesso sem atualizar `PWD` pode executar o agente no
repositório chamador em vez do worktree.

A descoberta de configuração/agentes da V2 sobe a partir do `PWD`. Os worktrees
do core ficam em `.juicer/worktrees/<task>`, dentro do projeto, então
`.opencode/` no topo continua visível. Medição: `--agent reviewer` resolveu em
um subdiretório do projeto e falhou com `Agent not found` em um diretório fora
dele. Se os worktrees forem movidos para fora do projeto, o `.opencode/`
precisa existir no worktree ou via configuração global.

`.opencode/`, `opencode.json(c)` e `AGENTS.md` não são paths protegidos por
padrão. Uma tarefa com escopo que os permita pode alterar o agente que produz
evidência de review/security; o core detecta a mudança no diff, mas não valida
a definição do agente. Mantenha esses paths fora do escopo ou protegidos.

## Resultado normalizado

`ExecutionResult` contém:

- `ok`: verdadeiro exatamente quando `status == "PASS"`.
- `status`: `PASS`, `FAIL` ou `BLOCKED`.
- `exit_code`: código de saída ou `None`.
- `session_id`: sessão capturada ou `None`.
- `output`: stdout e stderr combinados.
- `agent_output` (campo adicional exposto pelo executor do core): texto
  assistente extraído do stream de eventos V2 (`part.text`). `output` continua
  sendo o stream bruto para auditoria; `agent_output` é usado apenas para
  parsear evidências estruturadas.
- `detail`: explicação do resultado.
- `command`: comando executado, quando disponível.
- `agent` e `cwd`: contexto da execução.

Não existe status `PASS` inferido de texto do agente. Sucesso exige exit code
zero; a conclusão de uma tarefa ainda depende de checks, evidências e gates do
core.

## Timeout e falhas

- Timeout: `ok=false`, `status=FAIL`, `detail` contém o timeout.
- Binário ausente ou erro de sistema: `ok=false`, `status=BLOCKED`.
- Exit code diferente de zero: `ok=false`, `status=FAIL`.
- Saída JSON inválida não derruba a execução; o parse é tolerante e o exit code
  continua sendo a fonte de sucesso do processo.

## Alvo V2 e histórico V1

O MVP usa OpenCode 2.x/V2. O adaptador é único e V2-first. Referências a V1
neste contrato e nos comentários do adaptador são **históricas**: documentam
medições e caminhos de diagnóstico já realizados, não um alvo de suporte nem
uma promessa de compatibilidade.

Um binário V1 ainda pode ser detectado para diagnóstico; ele é reportado como
`degraded`. Se expuser `--dir`, o adaptador mantém um caminho legado de execução
para esse diagnóstico, mas V1 não é alvo suportado nem validado. O contrato é
pequeno para permitir evolução sem mudar o core.

Permissões do OpenCode V2 (`permissions[]` allow/ask/deny) são barreira
adicional de execução; não substituem gates, evidências nem aprovação do core.

## Modelo de confiança

O core valida a *estrutura* e o *vínculo* (commit/tree) dos artefatos de
evidência, mas não prove autenticidade: qualquer processo com acesso ao
repositório (inclusive um agente rodando no worktree) pode gravar um artefato
PASS. A premissa é um ambiente local single-user confiável — mesma premissa do
git sem assinatura de commit. Assinatura de artefatos e atores remotos ficam
fora do MVP.

Evidências de revisão/segurança podem ser produzidas pelo core acionando os
agentes existentes (`juicer review-run` / `security-run`): o agente responde com
um bloco JSON estruturado, o core valida forma e severidade e grava o artefato
com commit/tree calculados por ele. Texto fora do bloco é ignorado e nunca vira
evidência.

## Testes

- `tests/test_harness_contract.py`: contrato, capabilities V2, timeout, falha,
  sessão e protocolo.
- `tests/test_opencode_adapter.py`: compatibilidade do adaptador e parsing.
- `tests/test_opencode_smoke.py`: smoke real V2 opt-in com
  `JUICER_OPENCODE_SMOKE=1`.
