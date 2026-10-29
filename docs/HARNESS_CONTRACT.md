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
| `dir_flag` | `--dir` detectado (V1); **ausente na V2 medida**. |
| `session_flag` | `--session` detectado na ajuda. |
| `session_resume` | Retomada de sessão comprovada; ainda `false` até probe real. |
| `continue_flag` | `--continue` detectado na ajuda. |
| `standalone_flag` | `--standalone` detectado (V2); padrão do adaptador para isolar sessões. |
| `server` | `serve --help` respondeu com sucesso. |
| `auto_flag` | `--auto` existe, mas não é usado por padrão. |
| `permissions` | Política granular medida; por enquanto `unknown` (config V2 documental). |
| `cancel` | Forma de cancelamento; adapter usa timeout/processo. |
| `events` | Formato de saída; `jsonl-stream` (eventos V2 com `part`). |
| `worktree` | Isolamento; `git-cli` no core. |

### Capacidades medidas (OpenCode 2.1.4, 2026-10-26)

| Capacidade | Medida |
| --- | --- |
| `run` / `run_json` / `agent_flag` / `session_flag` / `continue_flag` / `auto_flag` | presentes |
| `standalone_flag` | presente |
| `dir_flag` | **ausente** — workspace fixado pelo CWD do processo |
| Eventos | NDJSON com `sessionID` e `part.type=text` |

## Execução

`ExecutionRequest` contém:

- `prompt`: texto não vazio.
- `cwd`: diretório de trabalho (worktree); no V2 é a única âncora de projeto.
- `agent`: agente opcional.
- `timeout`: segundos positivos.
- `session_id`: sessão opcional, quando suportada.
- `extra_args`: argumentos adicionais explícitos.

O adaptador V2 monta o comando com `run`, `--format json`, `--agent`,
`--standalone` (quando a flag existe) e, quando solicitado, `--session`. Não
passa `--dir` na V2. `--auto` não é adicionado por padrão. O subprocesso roda
com `cwd=request.cwd`.

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

## V1 e V2

O MVP usa OpenCode 2.x/V2. O adaptador é único e V2-first; um binário V1 ainda
pode ser apontado via `OPENCODE_BIN` para diagnóstico, mas é `degraded` e não é
alvo de suporte. O contrato é pequeno para permitir evolução sem mudar o core;
isso não constitui promessa de compatibilidade V1.

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
