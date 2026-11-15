# Plano S2 — Validação Completa do Sistema, Correção de Lacunas e Reconciliação Documental

## 1. Diagnóstico Completo da Auditoria S2

Após inspeção integral de `comprova-lattes-api/`, `comprova-lattes-app/`, `docs/` e `.specs/`, os módulos principais (`M1 parser`, `M2 matcher`, `M3 extractor`, `M4/M5 experiments`, `M6 backend + frontend`) estão funcionais e verificados com 390 testes e `npm run lint`/`build` aprovados. Contudo, a validação ponta a ponta revelou **pendências importantes que passaram despercebidas**:

### A. Bug estrutural + lacuna metodológica em `comprova-lattes-api/src/comprova_lattes/experiments/synthetic.py`
1. **Estrutura XML incompleta em categorias de evento/produção técnica (`_xml`):**
   - Em `synthetic.py` (`category == 3` `APRESENTACAO-DE-TRABALHO` e `category == 4` `ORGANIZACAO-DE-EVENTO`), `_xml` colocava `TITULO`, `ANO`, `NOME-DO-EVENTO` e `NOME-INSTITUICAO` diretamente na tag pai em vez de usar os subnós oficiais `<DADOS-BASICOS-*>` e `<DETALHAMENTO-*>`.
   - Como `xml_parser.py` (linhas 743–789) lê produção técnica exclusivamente a partir de `DADOS-BASICOS-*` (`@TITULO`, `@ANO`, `@NATUREZA`) e `DETALHAMENTO-*` (`@NOME-DO-EVENTO`, `@INSTITUICAO-PROMOTORA`), os registros gerados para categorias 3 e 4 vinham com `title=None`, `event_name=None`, `institution=None` e `year=None`, impedindo associação na Fase 1 (`SEM_COMPROVANTE`).
   - Em `category == 2` (`PARTICIPACAO-EM-CONGRESSO`), embora haja fallback no `child`, o padrão conforme também deve usar `<DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO>` e `<DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO>`.
   - Em `category == 3` (`APRESENTACAO-DE-TRABALHO`), `r.participation_role` é `None` no parser e `rules.py` utiliza `"APRESENTADOR"` como papel estrutural na comparação; portanto `gold.participation_role_raw` no caso base deve ser `"APRESENTADOR"` (para o caso base ser `VALIDADO`, e `None` em `ORGANIZACAO-DE-EVENTO` usa `"ORGANIZADOR"` já extraído por `r.participation_role`).
2. **Operador `legitimate` trivial não diferenciava `PROPOSED` de `BASELINE_NORMALIZED`:**
   - Hoje `legitimate` apenas duplica espaço em `holder_name`, empatando `BASELINE_NORMALIZED` ("B") com `LEVENSHTEIN_NORM` (`PROPOSED`).
   - Deve aplicar variação legítima realista (mantendo compatibilidade ASCII com os glifos `_GLYPHS` de `render.py`: apenas `A-Z`, `0-9`, `:`, `.`, `_`, `-` e espaço), incluindo:
     - **Equivalência de sigla institucional** usando uma tabela explícita exportada por `synthetic.py` (`SYNTHETIC_ACRONYMS`, por exemplo mapeando siglas sintéticas `IF01`, `IF02`... ou uma sigla canônica no `issuer_institution`/`issuer_acronym`) e/ou **variação gráfica leve de 1 caractere** em campo longo (`title` ou `event_name` com >= 25 caracteres) + espaçamento/caixa em `holder_name`, de modo que `BASELINE_EXACT` e `BASELINE_NORMALIZED` falhem enquanto `PROPOSED` (`LEVENSHTEIN_NORM`) acerte `VALIDADO`.
     - **Atenção importante ao `test_experiments.py`:** Se `legitimate` usar sigla de `SYNTHETIC_ACRONYMS`, exportar helper/constante `SYNTHETIC_ACRONYMS` em `synthetic.py` (e usá-lo nas configurações de `test_experiments.py` e documentar em `experiments/README.md`) para provar que `PROPOSED` supera `"A"` (`BASELINE_EXACT`) e `"B"` (`BASELINE_NORMALIZED`) quando a tabela de siglas está configurada.
     - Também respeitar estritamente `_GLYPHS` de `render.py`: não usar acentos, vírgulas ou barras no texto rasterizado!
3. **Operador de mutação factual cobria apenas `activity_year += 7`:**
   - Distribuir deterministicamente entre as 5 categorias da família os tipos exigidos nos comentários #63 e #64 do orientador (mantendo 1 mutação por família×categoria, somando 5 `DIVERGENTE` por família):
     - `category == 0` (`ESPECIALIZACAO`, onde `carga` é aplicável): mutação moderada de carga horária (`40 -> 45`).
     - `category == 1` (`EXTENSAO_UNIVERSITARIA`, onde `carga` é aplicável): mutação extrema de carga horária (`40 -> 400`).
     - `category == 2` (`PARTICIPACAO_EVENTO`): mutação temporal (`activity_year += 7`, `start_year += 7`, `end_year += 7`).
     - `category == 3` (`APRESENTACAO_TRABALHO`): mutação de titular (`holder_name` trocado para `"OUTRA PESSOA SINTETICA"`, mantendo âncoras de título/evento para garantir associação prévia antes do `CONFLICT`).
     - `category == 4` (`ORGANIZACAO_EVENTO`): mutação de instituição (`issuer_institution` trocado para `"INSTITUICAO DIVERGENTE SINTETICA"`, mantendo `title`/`holder_name`/`ano` para garantir associação prévia antes do `CONFLICT`).
   - Manter compatibilidade com nomes dos operadores ou atualizar `experiments/README.md` e `test_experiments.py` de forma consistente (evitar quebrar referências existentes se desnecessário; é possível manter `operator="factual_mutation"` ou `"year_mutation"`? Preferível atualizar para nomes semânticos ou manter 5 operadores na família e documentar em `experiments/README.md` e testar todos em `test_experiments.py`, preservando `identity`, `legitimate`, `omission`, `no_document`).

### B. Refinamentos de Usabilidade no Frontend (`comprova-lattes-app/src/`)
1. **`src/lib/matcher.schema.ts` & `src/pages/NewValidationPage.tsx`:**
   - Manter `configTemplate` inicial com `thresholds: null` (sem limiares implícitos como calibrados).
   - Exportar `exampleConfigJson` (valores operacionais de teste + aviso em UI de que são parâmetros meramente ilustrativos de sessão, não calibração aprovada) e adicionar botões na tela `/validacoes/nova` para "Preencher exemplo operacional" e "Limpar limiares (null)".
   - Em `NewValidationPage.tsx`, ao selecionar documentos via `<input type="file" multiple>`, mesclar incrementalmente os arquivos novos aos já selecionados (evitando duplicata por `name + size`) e adicionar botão "Limpar comprovantes" além do botão "Remover" individual.
2. **`src/components/HumanReviewForm.tsx`:**
   - Ao abrir o formulário para nova revisão (`Solicitar ...`), sincronizar `status`, `matched` e `rejected` com o estado mais recente persistido em `record` (`latest ?? record.automatic`), e limpar mensagem `saved` anterior.

### C. Reconciliação Documental e Correção de Links Quebrados
1. **`README.md` (raiz):** remover todos os links quebrados `../../../../Caleb/dev/ufra-projects/tcc/...` substituindo pelos caminhos relativos reais (`.specs/...`, `docs/...`, `comprova-lattes-api/...`, `comprova-lattes-app/...`) e atualizar a seção de estado atual para refletir M1–M6 implementados e verificados offline (**390+ testes** + frontend build).
2. **`comprova-lattes-api/README.md`:** atualizar o estado atual de M1 para M1–M6 implementados/verificados offline e referenciar também CLI `python -m comprova_lattes.experiments --help`.
3. **`docs/quality.md`:** registrar nova seção no topo com a verificação consolidada atual (mantendo o histórico cronológico abaixo).
4. **`.specs/codebase/ARCHITECTURE.md`:** atualizar cabeçalho e descrições dos módulos que já estão implementados e testados offline (M1–M6, incluindo revisão humana `AD-013`), mantendo explícitos os limites (sem estudo experimental oficial, PostgreSQL/Redis/Gemini reais não exercitados em CI).
5. **`.specs/codebase/PROFESSOR-REQUIREMENTS.md`:** atualizar checkboxes para refletir exatamente o que está implementado em código (`[x]`) vs o que ainda depende de execução oficial/anotação/decisão do orientador (`[ ]` em DTD oficial #25, Kappa humano #47 e execução dos Experimentos 1–3 com Gemini/Tesseract reais e cronometragem #71).
6. **`.specs/project/STATE.md`, `.specs/project/ROADMAP.md`, `.specs/HANDOFF.md`:** atualizar com a entrega S2 e seus gates finais.

---

## 2. Verificação Obrigatória (Phase X)
- `comprova-lattes-api/`:
  - `pytest -q` (todos os testes passando, validando inclusive as 5 categorias do gerador sintético e a superioridade de `PROPOSED` sobre `A` e `B` no `experiment2` com tabela de siglas).
  - `ruff check .` -> `All checks passed!`.
- `comprova-lattes-app/`:
  - `npm run lint` -> exit code 0.
  - `npm run build` (`tsc -b && vite build`) -> exit code 0.
