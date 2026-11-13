# In Progress

## Current Tasks

### [TASK-011] Validar fluxo E2E V2 e aceitação do MVP

**Status**: In Progress (implementação concluída; aguardando review/merge)

**Evidence**:
- `tests/test_e2e_v2.py` (8 testes): fluxo completo missão → import → run →
  review → security → approval → merge → pós-merge com o core real e o
  adaptador V2 real contra um binário V2 scriptado; bloqueios para gate,
  review, security e aprovação ausentes; fora de escopo, commit do agente e
  path protegido; falha pós-merge nunca deixa `completed`/`done`; retry e
  `resume` preservam evidência.
- `tests/test_opencode_smoke.py`: probe opt-in de capabilities V2 mediu
  `opencode v2.2.7` (`v2=true`, `run_json=true`, `standalone_flag=true`,
  `dir_flag=false`, `events=jsonl-stream`).
- Execução real de `run` + checks + `integrate` + pós-merge passou com modelo
  free; a validação expôs que a V2 resolve o projeto por `PWD`, não apenas pelo
  `cwd` do subprocesso. O adaptador agora fixa `cwd` e `PWD`; regressão coberta
  por teste e pelo binário scriptado do E2E.
- `review-run`/`security-run` ao vivo ficaram bloqueados por quota/limite do
  provider (HTTP 402/429). O caminho é coberto pelo E2E determinístico; a
  limitação está registrada em STATUS sem ser declarada como PASS real.

**Next**: revisão (`@reviewer`), correções, suíte completa, commit da feature,
merge e checks pós-merge. TASK-011 não vai para `done` antes disso.
