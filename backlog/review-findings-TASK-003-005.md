# Achados de revisão — TASK-003 / TASK-004 / TASK-005 (working tree)

**Revisão**: @reviewer, 2026-10-26
**Veredito**: Changes requested — resolver CR-1 e CR-2 antes de merge; M-1 a M-4 e G-1 endereçar ou adiar com justificativa.
**Contexto**: mudanças não commitadas em `release/4.0.0` (HEAD fccb188). Suíte no momento da revisão: 120 passed, 1 skipped.
**Status (2026-10-29)**: todos os achados CR/M/G resolvidos; re-revisão @reviewer: **Approved with minor suggestions**; pendências da TASK-005 resolvidas e incremento revisado/aprovado; suíte final 193 passed, 1 skipped. Aguardando aprovação humana para merge.

## Críticos (bloqueiam merge)

- **CR-1 (TASK-003)** — ✅ RESOLVIDO (2026-10-29). `_V2_RE` substituída por `_VERSION_MAJOR_RE` com parse explícito de major (`juicer/harness/opencode.py`); `_version_is_v2` exige major ≥ 2. Testes: `1.2.4`, `v1.2.0`, `1.2.34`, `0.2.9` → False; `v2.0.0`, `10.2.3`, `12.0.1` → True; `dev-build` → False.
- **CR-2 (TASK-004)** — ✅ RESOLVIDO (2026-10-29, TDD). `integrate` captura `GateBlockedError` com `gate_status == "FAIL"` no loop de gates pré-merge e move a tarefa `completed → blocked` com `blocked_reason` explícito + evento `integration_gate_failed`. Rotas legais: `blocked → ready` via `retry_task` → re-run → `completed → done`. BLOCKED/NOT RUN continuam em `completed` de propósito (evidência/aprovação podem ser fornecidas e `integrate` re-executado sem re-run). Testes: `test_completed_gate_fail_has_legal_recovery_route`, `test_review_fail_verdict_also_blocks_completed_task` (retry incluído); `test_review_critical_finding_is_fail` atualizado para o novo invariante.

## Maiores

- **M-1 (TASK-004)** — ✅ RESOLVIDO (2026-10-29, TDD). `resume` copia `exec_doc["result"]` (commit/branch) para a tarefa ao alinhar `in_progress → completed/failed`; `integrate` lança `GateBlockedError` limpo (gate_status BLOCKED) quando `commit`/`branch` faltam no `result`, em vez de `AttributeError`/`TypeError`. Testes: `test_resume_aligning_completed_copies_execution_result` (resume → integrate → done), `test_integrate_without_commit_fails_cleanly`.
- **M-2 (TASK-005)** — ✅ RESOLVIDO (2026-10-29). Semântica única alinhada à spec: artefato **ausente/malformado → BLOCKED**; artefato **stale (commit/tree diferentes) → NOT RUN**. `evidence.py` (evaluate_review/security), docstrings do orchestrator e testes atualizados (`test_missing_artifact_is_blocked` × 2).
- **M-3 (TASK-004/007)** — ✅ RESOLVIDO (2026-10-29, TDD). `_check_scope` com fronteira de caminho: igualdade ou prefixo seguido de `/`; `src/` não casa mais `srcx/evil.py`. Testes: `test_scope_prefix_requires_path_boundary`, `test_scope_allows_files_inside_declared_directory`; `test_scope_violation_fails_task` (glob `docs/**`) permanece verde.
- **M-4 (TASK-005)** — ✅ RESOLVIDO (2026-10-29, TDD). `_guard_fail_overwrite` em `evidence.py`: PASS nunca sobrescreve FAIL sem `force=True`; FAIL→FAIL e PASS→PASS seguem permitidos. Exposto em `record_review`/`record_security` (orchestrator) e via flag `--force` nos subcomandos CLI `review`/`security`; evento registra `forced`. `EvidenceError` agora herda de `JuicerError` (CLI retorna exit 2 limpo, sem traceback). Testes: 5 em `tests/test_evidence.py` + `test_cli_review_pass_overwriting_fail_requires_force`.
- **G-1 (cobertura)** — ✅ RESOLVIDO (2026-10-29). Adicionados: `TestFindBinary` (7 testes: prioridade de explícito/ENV, preferência V2 entre candidatos, fallback sem V2, skip de candidato com probe falho, none quando sem candidatos); subcomandos CLI (`review` com findings, `security`, `retry` com status ilegal, `integrate` com não-completed, sobrescrita FAIL→PASS com/sem `--force`); falso positivo de versão (CR-1); resume → integração (M-1); recuperação pós-falha de gate (CR-2).

## Sugestões (registradas; decisão de tratamento abaixo)

- Autenticidade de evidência: processo com acesso ao repo (inclusive o agente no worktree) pode gravar artefato PASS; documentar premissa de confiança local single-user. — ✅ ENDEREÇADA (2026-10-29): nota "Modelo de confiança" em `docs/HARNESS_CONTRACT.md`.
- Validar findings/severidade em `record_*` (fail fast); normalizar severidade do parser CLI. — ✅ RESOLVIDO (2026-10-29): `validate_findings` valida severidade/descrição/linha e normaliza `severity` em `record_review`/`record_security` e no parser dos agentes.
- Cache de `discover()` por binário em `run()`. — ⏸️ ADIADA (otimização).
- `find_binary(explicit=...)` deve resolver via `shutil.which`. — ⏸️ ADIADA (comportamento explícito é intencional: caminho literal).
- `resume` não recupera execução órfã `running` (crash entre updates); unificar `attempt_history`. — ⏸️ ADIADA (resume cancela `running` órfão e reconcilia; unificação de histórico é melhoria).
- Conflito de merge define `blocked` sem `blocked_reason`; falha de gate pré-merge não emite evento. — ✅ PARCIALMENTE ENDEREÇADA (2026-10-29): falha de gate pré-merge FAIL agora emite `integration_gate_failed`; critérios emitem `criteria_evaluated`; conflito de merge sem `blocked_reason` ⏸️ adiado.
- Core poderia calcular `tree_hash` em vez de confiar no chamador. — ✅ PARCIALMENTE ENDEREÇADA (2026-10-29): `review-run`/`security-run` calculam commit/tree no core; `record_*` manual ainda aceita o hash do chamador ⏸️ (contrato externo).
- Timeout mata só o filho direto; com `--standalone`, servidor privado pode sobrevolver (considerar process-group kill). — ⏸️ ADIADA (risco operacional conhecido; requer probe).
- `_ZED_GLOB` macOS-only; sort lexicográfico reverso pode preferir binário errado. — ⏸️ ADIADA (Zed é fallback degradado, não alvo do MVP).

## Nits

- `tests/test_transitions.py:26-27`: construct `cond if False else expr` morto. — ✅ CORRIGIDO (2026-10-29).
- `juicer/cli.py`: `import json as _json` não usado. — ✅ CORRIGIDO (2026-10-29, nos dois subcomandos).
- `docs/HARNESS_CONTRACT.md`: capability `v2` listada duas vezes. — ✅ CORRIGIDO (2026-10-29).

## Sugestões da re-revisão (2026-10-29) — registradas para tratamento

Veredito da re-revisão: **Approved with minor suggestions** (nada crítico). Sugestões 🟡/🟢:

- **Guard M-4 não cobre FAIL derivado** (🟡): artefato gravado como PASS mas com achado crítico avalia como gate-FAIL; regravar PASS limpo por cima exigiria `--force`. — ✅ RESOLVIDO (2026-10-29): `_guard_fail_overwrite` agora trata `verdict == "FAIL"` **ou** presença de achado `critical` como FAIL; teste `test_pass_cannot_overwrite_derived_fail_from_critical_finding`.
- Regex de versão com boundary de major (`1.2.34` vs `12.0.1` — comportamento atual correto; sugestão de teste extra). — ⏸️ ADIADA (cobertura atual já inclui os casos de fronteira; melhoria cosmética de teste).
- Eventos de gate `BLOCKED`/`NOT RUN` no `integrate` (hoje só FAIL emite `integration_gate_failed`). — ⏸️ ADIADA (melhoria de observabilidade; FAIL cobre o caminho crítico).
- Fail-fast ao validar severidade dos findings em `record_*`. — ✅ RESOLVIDO (2026-10-29, junto com TASK-005): `validate_findings` aplicado em `record_*` e no parser dos agentes.
- Mover `import fnmatch` para o topo do módulo. — ⏸️ ADIADA (import local é intencional e de baixo custo; consistente com outros imports do módulo).

## Revisão do incremento TASK-005 (2026-10-29)

Veredito inicial: **Changes requested** (2 🔴/🟡 + 4 🟡). Veredito após correções: **Approved** — pronto para merge após aprovação humana.

- 🔴 `_agent_workspace` caía silenciosamente para o checkout base quando o worktree sumia → artefato PASS para commit não revisado. Corrigido: exige worktree existente, `HEAD == commit` e ausência de mudanças rastreadas; recusa com `GateBlockedError(BLOCKED)` + evento `<kind>_agent_blocked`, sem chamar o agente.
- 🟡 Agente era passado ao harness com `@` (`--agent @reviewer`); agora usa o nome configurado (`agent.lstrip("@")`) e o artefato mantém `@reviewer`/`@security`.
- 🟡 Status corrompido em `checks.results.jsonl` podia causar `KeyError` → normalizado para `NOT RUN` (constante `CHECK_STATUSES` compartilhada com `gates.evaluate_gate`).
- 🟡 Rejeições (verdict inválido, findings inválidos, guard M-4) agora emitem `<kind>_agent_rejected` com motivo.
- 🟡 Cobertura: cwd do agente, worktree ausente/sujo/HEAD divergente, mutação durante o run, exceção do executor e unit tests de `extract_structured_evidence`.
- 🟢 `tree_hash` irresolúvel falha antes de qualquer run; nome do arquivo de saída sanitizado; critérios de missão/CLI usam forma válida (`human`); `line` rejeita bool/float não integral; pós-run revalida worktree (mudança rastreada pelo agente descarta a evidência).
- Pendência honesta mantida: smoke real de `review-run` executou o `@reviewer` no V2.1.4 e devolveu JSON estrito; o NDJSON real foi reproduzido no caminho de evidência até `done`. Nova chamada ao vivo bloqueada por quota do provider (HTTP 402); `security-run` ao vivo não executado (mesmo caminho de código, coberto por testes).

## Decisão de tratamento

- 2026-10-26: plano aprovado cobria correção das 5 falhas + verde + revisão. CR-1/CR-2 registrados como pendência de integração: merge bloqueado até resolução.
- 2026-10-29: CR-1, CR-2, M-1..M-4 e G-1 resolvidos (TDD onde aplicável); nits corrigidos; 1 sugestão endereçada via documentação, demais adiadas com justificativa. Suíte: 143 passed, 1 skipped.
- 2026-10-29: **re-revisão @reviewer: Approved with minor suggestions** — nenhum crítico; hardening 🟡 do guard M-4 aplicado (suíte: 144 passed, 1 skipped); demais sugestões 🟢 registradas acima com justificativa de adiamento.
- 2026-10-29: pendências da TASK-005 resolvidas (TDD): critérios com `verification` validado/avaliado + acionamento de `@reviewer`/`@security` pelo core (`review-run`/`security-run`, JSON estrito, core grava evidência). Suíte final: **193 passed, 1 skipped**. Smoke real: `@reviewer` executado no V2.1.4 e NDJSON real reproduzido até `done`; nova chamada ao vivo bloqueada por quota do provider (HTTP 402); `security-run` ao vivo não executado. **Pronto para merge após aprovação humana** (o fluxo exige aprovação explícita; aprovação não substitui testes/revisão).
