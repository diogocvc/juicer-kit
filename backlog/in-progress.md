# In Progress

## Current Tasks

### Task: [TASK-010] Alinhar agentes, comandos e documentação ao alvo V2

**Started At**: 2026-11-12

**Assigned To**: @documenter

**Current Step**: Alinhamento de `AGENTS.md`, `@orchestrator`, `@reviewer`, `@security`, `@tester`, comandos e documentação (README/STATUS/HARNESS_CONTRACT) à ordem canônica do core e ao alvo OpenCode 2.x/V2.

**Blockers**: Nenhum.

**Progress**:
- [x] `AGENTS.md` declara 4.0, ordem canônica e separação backlog/`.juicer`
- [x] `@orchestrator` alinhado aos gates reais do core
- [x] `@reviewer` read-only, acionado após checks e antes do merge
- [x] `@security` acionado por risco, sem substituir revisão
- [x] README/STATUS apontam plano, medida × lacuna e alvo V2
- [x] `HARNESS_CONTRACT.md` e adaptador sem referências V1 não marcadas
- [x] `/review` e `/test` compatíveis com o fluxo
- [x] Permissões V2 não apresentadas como substitutas dos gates do core

**Notes**: Baseline: TASK-009 integrada em `073839a`; suíte **337 passed**.
`tests/test_docs_alignment.py` (18 testes) cobre frontmatter/permissões dos
agentes, ordem canônica em AGENTS/orchestrator/README/GUIDE, comandos, template
do backlog, README/STATUS, contrato V2, JSON de evidência e marcação histórica
de V1. Revisão `@reviewer`: **Approved** após correções (gates condicionais,
ordem tester→reviewer, permissões documentais, alto risco sem gate implícito
de segurança, `agent: security` no `/security-audit`).
