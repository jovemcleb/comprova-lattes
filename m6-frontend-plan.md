# Plano M6 Frontend: Interface React/TypeScript/Tailwind e Auditoria Humana (`AD-013`)

## 1. Objetivo e Contratos da API

Integrar a SPA em `comprova-lattes-app/src/` aos endpoints reais implementados em `comprova-lattes-api/src/comprova_lattes/api/`:

- `GET /health` → `{ status, version, environment, gemini_model }`
- `GET /validations?offset=0&limit=50` → `[{ id, created_at, status, error_code }]`
- `POST /validations` (JSON) → submete `xml_content` (UTF-8) ou `xml_base64` (preserva bytes originais, incluindo `ISO-8859-1` do Lattes), `documents` (`[{ document_id, filename, mime_type, content_base64 }]` para `application/pdf`, `image/png`, `image/jpeg`, `image/webp`) e `matcher_config` (`MatcherConfig` completo com limiares explícitos).
- `GET /validations/{validation_id}` → retorna detalhe completo: `id`, `created_at`, `status`, `error_code`, `input`, `parsed` (`curriculum`, `diagnostics`, `declared_encoding`, `unverified_variants`, `unrecognized_elements`), `extractions`, `automatic_result` (`mode`, `record_verdicts`, `orphan_documents`, `association_pairs`), `records` (`[{ record_index, automatic, human_review, review_required }]`), `reviews`, `automatic_summary`, `reviewed_summary`.
- `POST /validations/{validation_id}/records/{record_index}/review` → submete `HumanReviewRequest` (`{ reviewer, status, justification, matched_document_id, rejected_document_ids }`), preservando integralmente o resultado automático original (`AD-013`).

---

## 2. Arquitetura de Camadas (`comprova-lattes-app/src/`)

Seguindo `@frontend-architecture` e `@tailwind-patterns` (Tailwind CSS v4):

| Caminho | Responsabilidade |
| --- | --- |
| `src/types/validation.ts` | Tipos e union types estritos espelhando os schemas Pydantic (`api/schemas.py`, `api/service.py`, `matcher/models.py`, `schemas/lattes.py`). Zero `enum` TS (`erasableSyntaxOnly: true`). |
| `src/lib/validation.api.ts` | Cliente HTTP `fetch` com base configurável via `import.meta.env.VITE_API_BASE_URL \|\| 'http://localhost:8000'`, leitura de erros FastAPI/HTTP, helpers browser-safe de conversão `File` → Base64 (`ArrayBuffer`) e leitura de `matcher_config` padrão editável para sessão. |
| `src/hooks/useValidations.ts` | Hooks TanStack Query (`useHealth`, `useValidationsList`, `useValidationDetail` com polling automático enquanto `PENDING`/`PROCESSING`, `useCreateValidation`, `useSubmitHumanReview`). |
| `src/components/AppShell.tsx` | Layout compartilhado, navegação (`/`, `/validacoes/nova`) e badge de conectividade/saúde com `/health`. |
| `src/components/StatusBadge.tsx` | Badges semânticos para status de lote (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `DISPATCH_FAILED`), classes (`VALIDADO`, `DIVERGENTE`, `INCONCLUSIVO`) e desfechos de campo (`FieldOutcome`). |
| `src/components/SummaryComparison.tsx` | Exibição separada de `automatic_summary` (pré-revisão) e `reviewed_summary` (pós-revisão), deixando explícito que são contagens operacionais e que a decisão automática permanece preservada (`AD-013`). |
| `src/components/FieldEvidenceTable.tsx` | Comparação campo a campo (`titular`, `titulo`, `evento`, `papel_participacao`, `instituicao`, `ano`, `carga`) entre Lattes e documento, exibindo brutos, normalizados, `similarity_score`, `numeric_difference`, `rule_applied` e `justification_pt`. |
| `src/components/HumanReviewForm.tsx` | Fluxo completo `AD-013`: obrigatório destacar `INCONCLUSIVO` (`review_required`), habilitar revisão por solicitação para `VALIDADO`/`DIVERGENTE`, selecionar/confirmar/corrigir `matched_document_id` (entre candidatos ou qualquer documento do lote, incluindo órfãos), marcar `rejected_document_ids` sem contradição, exigir `reviewer` e `justification`, e exibir histórico `reviews` append-only. |
| `src/components/RecordAuditCard.tsx` | Card expansível por registro combinando dados parsed `M1`, veredito automático `M2`, candidatos de ambiguidade, extração `M3` e `HumanReviewForm`. |
| `src/components/OrphanDocumentsPanel.tsx` | Painel separado para `orphan_documents` (`DOCUMENTO_NAO_ASSOCIADO`) com melhor candidato e escore, destacando que não entram na matriz de confusão dos registros (`AD-006`). |
| `src/components/ParserDiagnosticsPanel.tsx` | Diagnósticos `M1`, `declared_encoding`, variantes não verificadas e elementos não reconhecidos. |
| `src/pages/DashboardPage.tsx` | Rota `/`: visão geral, status `/health`, histórico paginado de validações (`GET /validations`) ordenado do mais recente ao mais antigo, atalho para criação e consulta por ID. |
| `src/pages/NewValidationPage.tsx` | Rota `/validacoes/nova`: upload de XML (arquivo binário em `xml_base64` ou XML UTF-8 colado em `xml_content`), múltiplos comprovantes (`application/pdf`, `image/png`, `image/jpeg`, `image/webp`) em `content_base64`, editor completo de `MatcherConfig` com parâmetros explícitos da sessão e redirecionamento para `/validacoes/:validationId`. |
| `src/pages/ValidationDetailPage.tsx` | Rota `/validacoes/:validationId`: acompanhamento em tempo real (`PENDING`/`PROCESSING`), filtros de registros (todos, pendentes de revisão, por status), comparação `automatic_summary` vs `reviewed_summary`, auditoria por registro/campo, órfãos e diagnósticos M1. |
| `src/App.tsx` | Definição das rotas `/`, `/validacoes/nova` e `/validacoes/:validationId` dentro de `AppShell`. |

---

## 3. Restrições Obrigatórias de Build e Qualidade

- **`tsconfig.app.json`:** `verbatimModuleSyntax: true` (`import type` obrigatório para tipos), `erasableSyntaxOnly: true` (proibido `enum` ou `namespace` TS), `noUnusedLocals: true`, `noUnusedParameters: true`, `noFallthroughCasesInSwitch: true`.
- **`eslint.config.js`:** respeitar `eslint-plugin-react-hooks` v7 e `babel-plugin-react-compiler`.
- **Escopo estrito:** editar apenas `comprova-lattes-app/src/`, `comprova-lattes-app/README.md`, `.specs/project/STATE.md`, `.specs/project/ROADMAP.md` e `.specs/HANDOFF.md`. Proibido instalar pacotes, editar `package.json`/`package-lock.json` ou editar `comprova-lattes-api/`.
- **Sem `git commit` ou `git push`.**

---

## 4. Verificação (Phase X)

- `comprova-lattes-app/`: `npm run lint` e `npm run build` com código de saída `0`.
- `comprova-lattes-api/`: `.\.venv\Scripts\python.exe -m pytest -q` e `.\.venv\Scripts\python.exe -m ruff check .` aprovados para confirmar integridade contínua do backend.
