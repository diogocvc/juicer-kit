# Changelog

## 3.0.0 — 2026-10-06

Retorno à estrutura simples do kit (linha v1), adaptada ao OpenCode 1.18.34:

- Kit somente Markdown: `.opencode/` (agents, commands e skills) +
  `backlog/` próprio de cada projeto.
- Instalação conforme o README: cópia de `.opencode/` e `backlog/`,
  git submodule ou symlink.
- README e `docs/GUIDE.md` alinhados ao kit e ao OpenCode 1.18.34.
- `VERSION` na raiz como fonte de versão do kit.

### Linha 2.x arquivada

A arquitetura harness-agnostic (adapters, `bin/juicer` em Python,
suíte de testes, `kit.yaml`, CI) permanece no histórico e está
arquivada na tag `v2.5.0`. O pacote npm `@juicer-kit/cli` pertence a
essa linha arquivada — o canal de instalação suportado é o Git
(conforme o README).
