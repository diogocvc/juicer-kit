# Task: [TASK-003] Definir contrato do harness e validar OpenCode V2

**Description**: Definir o contrato interno mínimo do harness (`discover` e `run`), normalizar o resultado e registrar capabilities comprovadas do OpenCode 2.0/V2.

**Priority**: P0-Critical

**Status**: Done

**Completed At**: 2026-10-29 15:15

**Assigned To**: @coder

**Implementation Summary**:
- `juicer/harness/contract.py`: `ExecutionRequest`/`ExecutionResult` normalizados e validados.
- `juicer/harness/opencode.py`: adaptador V2-first (workspace via CWD + `--standalone`, sem `--dir`), `discover` com capabilities medidas, parse de NDJSON (`part.text`), detecção de versão V2 por major ≥ 2 e `find_binary` multi-candidato (OPENCODE_BIN → PATH → `~/.opencode/bin` → Zed).
- `docs/HARNESS_CONTRACT.md`: contrato, semântica de status e modelo de confiança.
- `STATUS.md`: matriz medida × documental × bloqueado.
- Smoke real: `opencode v2.1.4`, `SMOKE-OK-7Q2`; `review-run` real validado em 2026-10-29.

**Test Coverage**:
- [x] Unit tests (`tests/test_harness_contract.py`, `tests/test_opencode_adapter.py`)
- [x] Integração com binário falso V2 (descoberta, comando, parsing, timeout, falha)
- [x] Smoke real opt-in (`JUICER_OPENCODE_SMOKE=1`)

**Security Review**:
- [x] Revisado por @reviewer (CR-1 resolvido)
- [x] Sem achados críticos na re-revisão

**Documentation**:
- [x] README atualizado
- [x] `HARNESS_CONTRACT.md` e `STATUS.md` atualizados

**Notes**: V1 permanece degradado e fora do alvo do MVP. Pendências registradas no `STATUS.md`: retomada real via `--session`, política de permissões V2 headless e smoke ao vivo de `security-run`. Ver `backlog/review-findings-TASK-003-005.md`.
