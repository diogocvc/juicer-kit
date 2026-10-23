# STATUS — Juicer Kit 4.0.0

Estado real da implementação, capacidades validadas e limitações. Este
documento descreve apenas o que foi implementado e executado; não contém
promessas de recursos futuros.

## Versão

- Kit: **4.0.0** (core Python + kit Markdown 3.x preservado)
- Harness alvo único: **OpenCode** — versão validada no ambiente: **1.19.4**
- Data desta avaliação: 2026-10-23

## Diferença entre referência e ambiente

O documento estrutural v2.0 define "OpenCode 2.0 / documentação V2" como alvo.
O binário efetivamente instalado é o **1.19.4** (linha V1), localizado no
registry do Zed, fora do `PATH`. Conforme a regra acordada, apenas a camada de
integração foi adaptada; o modelo conceitual (missões, tarefas, gates,
evidência) não depende da versão.

| Capacidade | Status | Como foi validado |
| --- | --- | --- |
| Detecção de binário (`OPENCODE_BIN` → PATH → registry Zed) | **supported** | `juicer discover` retornou 1.19.4 |
| Execução `opencode run --format json --agent <x>` | **supported** | smoke real: 3 tarefas executadas |
| Captura de session id + exit code + eventos JSON | **supported** | smoke real + testes com fake binário |
| Isolamento por branch/worktree git | **supported** | smoke real: 3 worktrees, diff isolado |
| Paralelismo local real (2 tarefas independentes) | **supported** | smoke real `--jobs 2` + teste de wall-clock |
| Checks determinísticos PASS/FAIL/BLOCKED/NOT RUN | **supported** | 64 testes + smoke real (FAIL bloqueou integração) |
| Gate técnico bloqueia NOT RUN/FAIL/BLOCKED | **supported** | testes `test_gates.py` |
| Merge explícito + conflito detectado (sem sobrescrita) | **supported** | testes `test_preservation.py` |
| Checks pós-integração no commit mergeado | **supported** | smoke real + teste `test_integrate.py` |
| Retomada após reinício (checkpoint/resume) | **supported** | teste `test_state.py` + smoke real (`resume`) |
| Proteção de mudanças pré-existentes (árvore suja) | **supported** | teste `test_preservation.py` |
| Aprovação humana separada do gate técnico | **supported** | teste `test_integrate.py` |
| `--dir` obrigatório para worktrees | **limitação conhecida** | o OpenCode 1.19.4 sobe a árvore até o checkout principal sem `--dir`; o adapter sempre passa `--dir` |
| Permissões headless | **experimental** | o config global do usuário tem `allow *`; sem permissões restritivas validadas em headless |
| Worktrees nativos do OpenCode V2 | **unsupported (1.19.4)** | usado fallback git CLI (declarado no adapter) |
| Preview/URL de preview (A15) | **unsupported** | fora do fluxo vertical MVP |
| Deploy/release (A16–A18) | **fora do MVP** | conforme escopo aprovado |
| Segundo harness, coordenação distribuída, event sourcing | **fora do MVP** | conforme escopo aprovado |

## Limitações ambientais

1. **OpenCode fora do PATH**: o binário descoberto está em
   `~/Library/Application Support/Zed/external_agents/registry/opencode/*/opencode`.
   Em outros ambientes, defina `OPENCODE_BIN` ou instale no PATH.
2. **Custo de modelo**: cada `juicer run` faz uma chamada real de modelo via
   `opencode run`. O tempo e o custo dependem do provider configurado.
3. **Escopo local**: locks `flock` + fence de revisão cobrem concorrência
   multi-processo **local**. Não há coordenação entre máquinas (fora do MVP,
   conforme decisão aprovada).
4. **Python**: o core usa apenas a biblioteca padrão (validado com Python
   3.8.5); os testes usam pytest via `uv tool run pytest`.
5. **`completed` ≠ `done`**: uma tarefa só fica `done` após gates técnicos
   PASS, integração explícita e checks pós-merge PASS (invariante B.12/B.13).

## Comandos de verificação executados

```
python3 -m compileall juicer bin/juicer          # OK
uv tool run pytest -q tests/                     # 64 passed
# smoke real (repo temporário):
python3 bin/juicer init
python3 bin/juicer mission --title ... --objective ...
python3 bin/juicer decompose tasks.json
python3 bin/juicer run TASK-001                  # opencode 1.19.4, session ses_..., check PASS
python3 bin/juicer run --jobs 2                  # 2 tarefas paralelas, worktrees isolados
python3 bin/juicer integrate TASK-001            # merge + pós-merge PASS
python3 bin/juicer resume                        # recuperou task interrompida
```

## Pendências de validação

- Permissões restritivas em headless (hoje depende do config do usuário).
- Execução com múltiplos workers/processos coordenadores no mesmo projeto.
- Preview de build/URL (A15) — não implementado no MVP.
