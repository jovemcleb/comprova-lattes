# Especificação M1 (P0-A) — Schemas Canônicos e Parser XML Lattes

**Status do Marco M1:** Em andamento (schemas e parser seguro implementados; expectativa de código CAPES corrigida com aprovação do usuário; conformidade DTD ainda pendente)
**Última atualização:** 2026-11-13

---

## 1. Objetivo do Marco M1

Extrair deterministicamente as cinco categorias aprovadas (AD-012): `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`, com modelos Pydantic v2 e leitura segura (`defusedxml`). AD-011 adota XSD oficial do Extrator como referência principal e DTD comunitária como comparação histórica; o requisito DTD do professor (#25) continua pendente de confirmação, sem pressupor equivalência com a exportação da interface. A ampliação é descrita em [technical-production.md](technical-production.md).

---

## 2. Escopo Desta Entrega (Entrega 1 — Schemas e Mapeamento Preliminar)

### Incluído nesta entrega
1. **Schemas Pydantic v2 mínimos** em `comprova-lattes-api/src/comprova_lattes/schemas/`:
   - `LattesCurriculum`: metadados do currículo (`lattes_id`, `updated_at`, `full_name`, `citation_names`, `summary`) e lista de `records`.
   - `LattesRecord`: registro curricular auditável em `snake_case`, com `None` para campos ausentes (sem sentinelas inventadas), `institution` estritamente separado de `city` e `location`, e representação numérica fiel (`int` estrito para anos e `Decimal` finito para `workload_hours`, sem truncamento silencioso nem limites arbitrários de domínio).
   - `XmlProvenance`: proveniência estruturada do registro no XML (`parent_tag`, `section_tag`, `record_tag`, `sequence_attribute`, `raw_attributes`).
   - Enums de domínio: `LattesCategory` (3 categorias na entrega inicial; 5 após AD-012) e `ActivityStatus`.
2. **Testes unitários** em `comprova-lattes-api/tests/test_schemas.py` cobrindo campos ausentes, válidos, inválidos, proveniência, separação instituição/cidade/local e não truncamento numérico.
3. **Proposta preliminar de mapeamento XML** em `.specs/features/m1-parser/xml-mapping.md`, distinguindo o que veio dos protótipos legados do que ainda não foi verificado contra a DTD oficial do CNPq.

### Explicitamente fora desta entrega
- Implementação do parser XML (`comprova_lattes/parser/`), detecção de codificação (`UTF-8` / `ISO-8859-1`) e integração com `defusedxml`.
- Obtenção ou validação offline da DTD oficial do CNPq.
- Modelos do extrator multimodal (`extractor/`), do motor determinístico (`matcher/`), API FastAPI, Celery ou banco de dados.

---

## 2.1 Escopo Desta Entrega (Entrega 2 — Hardening do Parser XML e Integração com Manifesto)

### Incluído nesta entrega
1. **Descarte parcial de `workload_hours` inválida com rastreabilidade** (`comprova_lattes/parser/`):
   - Valores negativos, não numéricos ou não finitos em `CARGA-HORARIA` não abortam o currículo: `workload_hours` é definido como `None`, o restante do registro e `provenance.raw_attributes` são preservados e um `LattesParseDiagnostic` (`code="INVALID_WORKLOAD_HOURS"`, `record_path`, `attribute`, `original_value`, `reason`, `record_index`) é retornado em `LattesParseResult.diagnostics`.
   - Ausência ou string vazia/em branco resulta em `workload_hours=None` sem diagnóstico nem aviso. Valores `Decimal` não negativos (incluindo fracionários) são preservados sem teto arbitrário.
   - `parse_lattes_xml(...)` emite `LattesParserWarning` (`UserWarning`) para cada diagnóstico para não silenciar descartes; `parse_lattes_xml_with_report(...)` retorna os diagnósticos estruturados.
   - Anos inválidos mantêm a política atual (`LattesNumericValueError`).
2. **Limites operacionais de recursos XML configuráveis** (`comprova_lattes/parser/`):
   - Parâmetros `max_bytes` (padrão técnico `DEFAULT_MAX_XML_BYTES = 10 MiB`, validado antes da decodificação) e `max_depth` (padrão técnico `DEFAULT_MAX_XML_DEPTH = 64`, validado durante o parsing seguro via `_BoundedTreeBuilder` sem recursão ilimitada), ambos validados como inteiros positivos (`ValueError` caso contrário) e levantando `LattesResourceLimitError` quando excedidos.
   - Proteções `defusedxml` (`forbid_dtd=True`, `forbid_entities=True`, `forbid_external=True`) mantidas sem acesso de rede.
3. **Testes unitários e de integração com manifesto**:
   - `tests/test_parser.py`: cobertura para descarte de carga horária inválida com diagnósticos/warnings, ausência sem aviso, preservação de `Decimal`, fronteiras de `max_bytes`/`max_depth` e payloads profundos.
   - `tests/test_parser_fixtures.py`: validação integral das fixtures sintéticas contra `tests/fixtures/m1/manifest.json` (cabeçalho, contagens, todos os campos dos registros) e equivalência estrita em `ISO-8859-1` com declaração explícita.

---

## 3. Invariantes e Decisões Aplicadas

- **Ausência explícita (`None`):** Nenhum campo ausente no XML pode ser preenchido com strings sentinelas inventadas (ex.: `"NAO_IDENTIFICADO"`, `"Instituição não informada"`, `"Curso Complementar"` ou contadores artificiais de `sequence`).
- **Separação de `institution`, `city` e `location`:** O campo `institution` representa exclusivamente o nome da instituição (`NOME-INSTITUICAO`), nunca devendo receber fallback de `LOCAL-DO-EVENTO` ou `CIDADE-DO-EVENTO`.
- **Proveniência obrigatória:** Todo `LattesRecord` exige `category` (uma das 5 categorias de AD-012) e `provenance` com `section_tag` e `record_tag` não vazios.
- **Integridade numérica:** `start_year` e `end_year` rejeitam booleanos, `float` e strings decimais (evitando truncamento silencioso como `int(float(s))`); `workload_hours` usa `Decimal` finito para preservar valores fracionários sem perda de precisão. Nenhuma faixa arbitrária (ex.: `1950..2100` ou `1..15000`) é imposta nesta camada.

---

## 4. Decisões em Aberto (Pendentes de Alinhamento)

1. **[M1-OPEN-01] DTD oficial do CNPq:** A fonte oficial da DTD do Currículo Lattes ainda não foi obtida no repositório. A lista exata de tags/atributos e a estratégia de validação DTD offline (verificação de estrutura e entidades sem acesso de rede) dependem dessa obtenção.
2. **[M1-OPEN-02] Resolvida em AD-009:** `Decimal | None`, sem truncamento e com igualdade numérica exata (`40 == 40.0`); diferença factual gera conflito por campo em par associado. Agregação final por categoria continua pendente no M2.
3. **[M1-OPEN-03] Política de formato de `updated_at` e `citation_names`:** Confirmar na implementação do parser se `DATA-ATUALIZACAO` será preservada no formato bruto do XML (`DDMMAAAA`) ou normalizada, e como tratar separadores em `NOME-EM-CITACOES-BIBLIOGRAFICAS`.
4. **[M1-OPEN-04] Separação resolvida em AD-010:** `title`, `event_name` e papel ficam distintos, sem concatenação. Ausência do título no comprovante não é conflito; agregação final por categoria ainda pendente no M2.

---

## 5. Pendências e Tarefas Futuras do M1

- [ ] **T-M1-01:** Obter e versionar a DTD oficial do CNPq (ou artefato equivalente autorizado) e definir validação DTD offline sem resolução de entidades externas.
- [ ] **T-M1-02:** Fechar mapeamento XML → Pydantic contra fonte oficial. Divergência CAPES resolvida: manifesto e documentação mantêm `validation_code=None`, com código de curso somente na proveniência.
- [ ] **T-M1-03:** Concluir validação contra DTD oficial no módulo `comprova_lattes/parser/` (leitura segura `defusedxml`, `UTF-8`/`ISO-8859-1`, descarte rastreável de `workload_hours` inválida e limites operacionais `max_bytes`/`max_depth` já implementados).
- [ ] **T-M1-04:** Fechar suíte M1 após validação DTD oficial. Fixtures e manifesto já integrados; expectativa incorreta de `validation_code` corrigida em 13/11/2026.
- [x] **T-M1-05:** Gate local independente: 130 testes e Ruff aprovados. Hydrogen relatou também 130 testes e Ruff em Python 3.12/Linux; distinguir o relato da execução independente. Seis fixtures conformes/técnicas revalidadas independentemente contra XSD offline. Evidências consolidadas em `docs/m1-linux-verification.md`. Conformidade DTD permanece pendente.
