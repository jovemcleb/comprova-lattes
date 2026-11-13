# Catálogo de Fixtures Sintéticas Conformes ao XSD Oficial (M1-Conformant)

**Referência estrutural:** XSD oficial do **Extrator Lattes CNPq** (`references/xml-grammars/cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd`, atualizado em 12/09/2022, SHA-256 `06b3976943f73b4e66f4ece70c5d9358d244fc080704c518a8d533d84eea6214`), conforme [AD-011](../../project/STATE.md) e [grammar-analysis.md](grammar-analysis.md).

> [!IMPORTANT]
> **Separação entre conformidade e robustez:**
> - Este conjunto (`comprova-lattes-api/tests/fixtures/m1-conformant/`) é **totalmente independente** das 5 fixtures de robustez/tolerância em `comprova-lattes-api/tests/fixtures/m1/` (descritas em [fixture-catalog.md](fixture-catalog.md)), que permanecem intactas para testar fallbacks legados e ausência de cabeçalho sem fingir conformidade gramatical.
> - Todas as fixtures abaixo são **100% sintéticas e fictícias**, sem uso de currículos reais nem arquivos do Drive, e **não afirmam equivalência integral com o XML exportado pela interface web do Lattes**.
> - **M1 permanece em aberto** até confirmação do orientador sobre o XSD como alternativa à DTD e fechamento das pendências de suporte do parser.

---

## 1. Visão Geral e Validação Offline

- **Localização:** `comprova-lattes-api/tests/fixtures/m1-conformant/`
- **Manifesto:** [`manifest.json`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1-conformant/manifest.json)
- **Suíte de testes:** [`test_parser_conformant.py`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/test_parser_conformant.py)
- **Validação estrutural offline:** Executada em contêiner descartável (`grammar-lxml-scratch:tmp`, `lxml 6.1.3` / `libxml2 2.14.6`) a partir de `references/xml-grammars/tools/validate_fixtures.py`, com `--network none --read-only`, montagens `:ro` e `XMLParser(resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False, attribute_defaults=False)`. Nenhuma dependência `lxml` foi instalada no host.

| Arquivo XML | SHA-256 | Bytes | XSD (CNPq 2022) | DTD (2010) | Acad. | Compl. | Ev. | Total |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| [`curriculo_conformante_completo.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1-conformant/curriculo_conformante_completo.xml) | `098e737c12a0295d9f0fb22dadb6819c33421cfea7b6aae507f5ab192aed01de` | 2997 | **Válido (0 erros)** | Válido (0 erros) | 3 | 2 | 1 | **6** |
| [`curriculo_conformante_carga_fracionaria.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1-conformant/curriculo_conformante_carga_fracionaria.xml) | `9dc430d21f2ba915562883b54f7f316d39f1135ab34cb8c18c7debd26300ada5` | 2662 | **Válido (0 erros)** | Válido (0 erros) | 1 | 4 | 1 | **6** |
| [`curriculo_conformante_eventos_subnos.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1-conformant/curriculo_conformante_eventos_subnos.xml) | `4ec13e23f9e37c6c6a86919c05314940d27b7513ae258683a2c8aa480858a889` | 2310 | **Válido (0 erros)** | Inválido (15 erros: `SEXO` opcional no XSD e tag `PARTICIPACAO-EM-FEIRA` / atributos `XSD-only`) | 0 | 0 | 4 | **4** |
| [`curriculo_conformante_acentuacao_campos_opcionais.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1-conformant/curriculo_conformante_acentuacao_campos_opcionais.xml) | `a2787066701cec7ad8c49443b7722aed7fea2965c72dc7e7a8c364391d9aeb1b` | 1428 | **Válido (0 erros)** | Válido (0 erros) | 1 | 1 | 1 | **3** |

---

## 2. Invariantes Aplicados às Fixtures Conformes

1. **Cabeçalhos obrigatórios do XSD:** `CURRICULO-VITAE/@SISTEMA-ORIGEM-XML` e `DADOS-GERAIS/@NOME-COMPLETO`, `@NOME-EM-CITACOES-BIBLIOGRAFICAS`, `@NACIONALIDADE`, `@PERMISSAO-DE-DIVULGACAO`.
2. **Ordem estrita (`xs:sequence`):**
   - Raiz: `DADOS-GERAIS` antes de `DADOS-COMPLEMENTARES`.
   - `DADOS-GERAIS`: `RESUMO-CV` antes de `FORMACAO-ACADEMICA-TITULACAO`.
   - `FORMACAO-ACADEMICA-TITULACAO`: `GRADUACAO` → `ESPECIALIZACAO` → `MESTRADO` (e `APERFEICOAMENTO` isolado na fixture 2).
   - `FORMACAO-COMPLEMENTAR`: `FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA` → `MBA` → `FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO` → `OUTROS`.
   - `PARTICIPACAO-EM-EVENTOS-CONGRESSOS`: `PARTICIPACAO-EM-FEIRA` → `PARTICIPACAO-EM-SEMINARIO` → `PARTICIPACAO-EM-OFICINA` → `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`.
3. **Ausência de atributos indevidos:** nenhum elemento possui `SIGLA-INSTITUICAO`; `CARGA-HORARIA` aparece **somente** em `ESPECIALIZACAO`, `APERFEICOAMENTO` e nos elementos de `FORMACAO-COMPLEMENTAR`, nunca em `GRADUACAO`, `MESTRADO` ou eventos.
4. **Eventos exclusivamente por subnós:** dados de eventos ficam apenas em `DADOS-BASICOS-*` e `DETALHAMENTO-*` (incluindo `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`), com `SEQUENCIA-PRODUCAO` como único atributo do nó pai.
5. **Segurança e codificação:** nenhum `<!DOCTYPE>` ou `<!ENTITY>` nos arquivos XML; arquivos gravados em UTF-8 e validados também via transcodificação estrita para `ISO-8859-1` em `test_parser_conformant.py`.

---

## 3. Detalhamento por Fixture

### 3.1 `curriculo_conformante_completo.xml`
- **Cobertura:** As três seções em ordem válida, acentuação portuguesa e `&amp;`, código CAPES preservado apenas em `provenance.raw_attributes` (`validation_code=None`), `CARGA-HORARIA` apenas em `ESPECIALIZACAO` (`360`) e `FORMACAO-COMPLEMENTAR` (`40`, `20`), e `workload_hours=None` em `GRADUACAO`, `MESTRADO` e `PARTICIPACAO-EM-CONGRESSO`.
- **Registros esperados (6):**
  1. `FORMACAO_ACADEMICA` / `GRADUACAO` (`seq="1"`, `start_year=2015`, `end_year=2019`, `workload_hours=None`, `status=CONCLUIDO`)
  2. `FORMACAO_ACADEMICA` / `ESPECIALIZACAO` (`seq="2"`, `start_year=2020`, `end_year=2021`, `workload_hours=Decimal("360")`, `status=CONCLUIDO`)
  3. `FORMACAO_ACADEMICA` / `MESTRADO` (`seq="3"`, `start_year=2022`, `end_year=2024`, `workload_hours=None`, `status=CONCLUIDO`)
  4. `FORMACAO_COMPLEMENTAR` / `EXTENSAO_UNIVERSITARIA` (`seq="1"`, `workload_hours=Decimal("40")`)
  5. `FORMACAO_COMPLEMENTAR` / `CURTA_DURACAO` (`seq="2"`, `workload_hours=Decimal("20")`)
  6. `PARTICIPACAO_EVENTO` / `CONGRESSO` (`seq="1"`, `title="Rastreabilidade em Auditoria Curricular"`, `event_name="Congresso Norte de Computação & Informação"`, `institution="Sociedade Regional de Tecnologia"`, `city="Santarém"`, `location="Auditório Tapajós"`, `workload_hours=None`, `status=None`)

### 3.2 `curriculo_conformante_carga_fracionaria.xml`
- **Cobertura:** Horas fracionárias (`Decimal`) estritamente onde declaradas no XSD (`APERFEICOAMENTO` = `180.5`, `EXTENSAO_UNIVERSITARIA` = `40.75`, `MBA` = `360`, `CURTA_DURACAO` = `1.5`, `OUTROS` = `12.25`), respeitando a ordem obrigatória dos 4 tipos de `FORMACAO-COMPLEMENTAR`, mais `PARTICIPACAO-EM-SIMPOSIO` com `workload_hours=None`.

### 3.3 `curriculo_conformante_eventos_subnos.xml`
- **Cobertura:** Recursos `XSD-only` (`DADOS-GERAIS` sem `SEXO`, `PARTICIPACAO-EM-FEIRA`, `MEIO-DE-DIVULGACAO="WEB"`, `FLAG-DIVULGACAO-CIENTIFICA="SIM"`), omissão de `NUMERO-IDENTIFICADOR`/`DATA-ATUALIZACAO`/`RESUMO-CV` (`None`), separação `institution=None` vs `city`/`location` em `PARTICIPACAO-EM-SEMINARIO`, `title=None` em `PARTICIPACAO-EM-OFICINA` e leitura de `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` via `DADOS-BASICOS-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` e `DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`.

### 3.4 `curriculo_conformante_acentuacao_campos_opcionais.xml`
- **Cobertura:** Estresse de diacríticos compatíveis com UTF-8 e ISO-8859-1 (`á é í ó ú, à è ì ò ù, â ê î ô û, ã õ, ç Ç, ü Ü, ñ Ñ`) e entidades `&amp;` nas três seções, combinado com omissão de atributos opcionais (`sequence=None`, `institution=None`, `title=None`, `start_year=None`, `end_year=None`, `status=None`) mantendo os atributos obrigatórios do cabeçalho no XSD.

---

## 4. Limites Cobertos e Pendências Fora Deste Conjunto

- As tags `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU` e `PARTICIPACAO-EM-OLIMPIADA` agora estão mapeadas e cobertas pelo conjunto separado `m1-technical/` (AD-012); as fixtures deste conjunto foram preservadas.
- Os resultados esperados não exigem `unverified_variants == ()`: variantes podem ter notas de proveniência/compatibilidade UI. As mensagens desatualizadas de gramática foram corrigidas na ampliação técnica; nenhuma nota comprova equivalência com a UI.
