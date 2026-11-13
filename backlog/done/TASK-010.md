# Task: [TASK-010] Alinhar agentes, comandos e documentação ao alvo V2

**Description**: Alinhar a ordem dos gates e os contratos de `@orchestrator`, `@reviewer`, `@security` e `@tester` com o core; corrigir `AGENTS.md`, README, STATUS e referências ao plano para o alvo OpenCode 2.0/V2, sem criar agentes e sem apagar histórico de medições já realizadas.

**Priority**: P1-High

**Status**: Done

**Completed At**: 2026-11-12

**Assigned To**: @documenter

**Implementation Summary**:
- Ordem canônica unificada em `AGENTS.md`, `@orchestrator`, README e GUIDE: `implementação → checks determinísticos → review → segurança (por risco) → aprovação humana (quando exigida) → merge/integrate → checks pós-merge → done`.
- `AGENTS.md` declara 4.0.0, alvo OpenCode 2.x/V2 (medido `v2.1.4`), separação backlog/`.juicer`, importação unidirecional e a regra de que agentes aconselham mas não dispensam gates do core.
- `@orchestrator` não promete gate inexistente: gates condicionais à política, `NOT RUN` nunca passa, achados críticos bloqueiam, aprovação humana não substitui testes/review, e conclusão só após integração explícita + pós-merge.
- `@reviewer` permanece read-only (`edit: deny`, `task: deny`, `bash: deny`), roda após checks e antes do merge; `@security` é acionado por risco, também read-only e não substitui revisão. Ambos documentam o bloco JSON único exigido por `review-run`/`security-run`.
- `/review`, `/test` e `/security-audit` declaram respectivamente `agent: reviewer`, `agent: tester` e `agent: security`. `/add-backlog` ganhou `Status: Pending` e a regra de que `.juicer/` é canônico após importação.
- README/STATUS apontam o plano, separam capacidade **medida** de lacuna planejada, registram 337 testes e não prometem compatibilidade V1. Gates de review/security são descritos como condicionais à `required_gates`; alto risco exige aprovação humana e não adiciona segurança implicitamente.
- `docs/HARNESS_CONTRACT.md` alinhado ao V2: permissões granulares são documentais/`unknown` (não medidas), `--dir` é histórico, e referências V1 remanescentes no contrato e nos comentários de `juicer/harness/opencode.py` estão marcadas como histórico/diagnóstico não suportado.
- Nenhum agente foi criado ou removido (18 agentes preservados). Histórico de medições em STATUS/contrato foi mantido.
- `docs/GUIDE.md` teve pipelines, papéis e diálogos corrigidos para testar antes de revisar e revisar antes de segurança.

**Test Coverage**:
- [x] `tests/test_docs_alignment.py` (18 testes): frontmatter/permissões read-only de reviewer/security, conjunto fixo de 18 agentes, ordem canônica em AGENTS/orchestrator/README/GUIDE, pipelines tester→reviewer, mapeamento de comandos, template `Status`, links ao plano, medida × lacuna, gates condicionais (incluindo ausência de segurança implícita em alto risco), contrato V2, JSON de evidência e marcação histórica de V1.
- [x] Suíte completa pós-merge: **337 passed** (`uv tool run pytest tests/ -q --ignore=tests/test_opencode_smoke.py`).
- [x] `python3 -m compileall juicer/ -q` OK.
- [x] `git diff --check` limpo.

**Review**:
- [x] Revisado por @reviewer em três rodadas — **Approved** na final.
- [x] Rodada 1 (Changes Requested): review/security apresentados como bloqueio incondicional, `@tester` após review no README, permissões descritas como medidas.
- [x] Rodada 2 (Changes Requested): “alto risco exige security” não era aplicado implicitamente pelo core; `/security-audit` sem `agent: security`.
- [x] Rodada 3 (Approved): sem findings bloqueantes; itens não bloqueantes restantes são reforço de testes/regressão.

**Security Review**:
- [x] Não aplicável como auditoria de código novo: mudanças são documentação, frontmatter, comentários e testes. O contrato reforça que permissões V2 são barreira adicional, não evidência, e que reviewer/security não editam nem delegam edição.

**Documentation**:
- [x] `AGENTS.md`, README, STATUS, `docs/GUIDE.md` e `docs/HARNESS_CONTRACT.md` alinhados.
- [x] Backlog e `backlog/in-progress.md` sincronizados; TASK-011 é a próxima elegível.

**Notes**: Ver seção 12 do plano. Commit da feature `aca7637` (`docs: align agents, commands and docs with V2 gate order (plan §12)`). Baseline anterior `c18ac9b`. Follow-ups não bloqueantes: adicionar teste de core para alto risco com apenas `verification` + aprovação, ampliar varredura de ordem no `assert_canonical_order` e cobrir inversão não adjacente nos pipelines do GUIDE.
