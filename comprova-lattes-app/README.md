# Comprova Lattes — interface React/Vite

Base frontend em React, TypeScript e Tailwind, com npm e lockfile existentes. As telas científicas de upload, associação, resultados e revisão humana ainda não estão implementadas. Escopo e prioridade em [ROADMAP](../.specs/project/ROADMAP.md).

## Desenvolvimento

Na pasta `comprova-lattes-app/`, com Node/npm e dependências instaladas:

```powershell
npm ci
npm run dev
```

## Verificação

```powershell
npm run lint
npm run build
```

Build inclui TypeScript. Resultados históricos em [quality.md](../docs/quality.md); comandos acima são instruções, não alegação de nova execução.

Revisão humana aprovada em AD-013, ainda planejada: encaminhar inconclusivos e permitir revisão das demais classes por solicitação, preservando resultado automático. Contratos em [M2](../.specs/features/m2-matcher/proposal.md).
