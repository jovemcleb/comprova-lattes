# Ampliação AD-012 — Produção Técnica, Mapeamentos XSD Ausentes e Papéis de Participação

**Status:** Implementado no escopo M1 (schemas, parser, fixtures sintéticas e testes). **Marco M1 permanece em aberto** até confirmação do orientador sobre o XSD oficial do Extrator como referência estrutural alternativa à DTD comunitária (`AD-011`) e validação em XML real autorizado da interface web (UI).
**Data:** 2026-11-13
**Decisões e referências:** `AD-010`, `AD-011`, `AD-012` ([STATE.md](../../project/STATE.md)), [xml-mapping.md](xml-mapping.md), [grammar-analysis.md](grammar-analysis.md), [event-role-contract.md](../m2-matcher/event-role-contract.md) e XSD oficial do Extrator Lattes CNPq (`references/xml-grammars/cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd`).

> [!WARNING]
> **Escopo e limites de comprovação:**
> - A referência estrutural primária é o **XSD oficial do Extrator Lattes CNPq (2022-09-12)**; **não se afirma equivalência integral** com o XML exportado pela interface web (UI) do Lattes.
> - A ampliação para `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO` decorre da decisão do usuário (`AD-012`) e **não inclui** artigos nem trabalhos publicados em anais (`PRODUCAO-BIBLIOGRAFICA`).
> - Os registros de motor (`matcher/`) e extração (`extractor/`) estão fora desta entrega.

---

## 1. Novas Categorias e Campos em `schemas/lattes.py`

### 1.1 `LattesCategory`
Adicionadas duas categorias ao enum canônico `LattesCategory`:
- `APRESENTACAO_TRABALHO = "APRESENTACAO_TRABALHO"`
- `ORGANIZACAO_EVENTO = "ORGANIZACAO_EVENTO"`

> **Nota sobre `tests/test_schemas.py`:** Por decisão explícita do usuário durante a execução, a asserção de contagem de membros em `test_lattes_category_enum_has_only_three_target_categories` (`tests/test_schemas.py:31-37`) foi atualizada de 3 para 5 categorias. Nenhuma outra asserção de teste existente foi alterada.

### 1.2 Novos campos opcionais em `LattesRecord`
Todos os campos abaixo possuem valor padrão `None` (`OptionalCleanStr`), convertendo strings vazias ou apenas espaços para `None`:

| Campo | Tipo | Origem XML / Regra |
| :--- | :--- | :--- |
| `nature_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@NATUREZA` (em `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`). Texto bruto preservado sem inferir papel. |
| `participation_type_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@TIPO-PARTICIPACAO` (em `PARTICIPACAO_EVENTO`, com fallback legado no nó pai). Texto bruto preservado. |
| `participation_form_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@FORMA-PARTICIPACAO` (em `PARTICIPACAO_EVENTO`, com fallback legado no nó pai). Texto bruto preservado. |
| `participation_role` | `OptionalCleanStr = None` | Papel normalizado por equivalência inequívoca (`PARTICIPATION_ROLE_MAP`) ou derivado estruturalmente da tag `ORGANIZACAO-DE-EVENTO`. Nunca inferido por `NATUREZA`. |

---

## 2. Mapeamentos XSD Adicionados e Atualizados (`parser/mappings.py` e `parser/xml_parser.py`)

### 2.1 Tags oficiais do XSD anteriormente ausentes
- `ACADEMIC_TAG_SUBTYPES`: adicionada `"ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU": "ENSINO_FUNDAMENTAL"` (XSD linhas 272 e 306–324; também presente na DTD comunitária).
- `EVENT_TAG_SUBTYPES`: adicionada `"PARTICIPACAO-EM-OLIMPIADA": "OLIMPIADA"` (XSD linhas 5570 e 6067–6135; `XSD-only`, ausente na DTD comunitária de 2010).

### 2.2 Atualização de mensagens em `UNVERIFIED_VARIANT_TAGS` e `xml_parser.py`
As notas legadas `"pendente DTD"` foram substituídas por mensagens precisas sem alegar conformidade com a UI:
- **11 tags confirmadas no XSD e na DTD** (`MESTRADO-PROFISSIONALIZANTE`, `POS-DOUTORADO`, `LIVRE-DOCENCIA`, `RESIDENCIA-MEDICA`, `ENSINO-MEDIO-SEGUNDO-GRAU`, `MBA`, `OUTROS`, `PARTICIPACAO-EM-SEMINARIO`, `PARTICIPACAO-EM-OFICINA`, `PARTICIPACAO-EM-ENCONTRO`, `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`): mantidas em `UNVERIFIED_VARIANT_TAGS` para rastreabilidade de auditoria com mensagem informando confirmação no XSD do Extrator e na DTD comunitária e não verificação de conformidade com a exportação da UI.
- **Tags `XSD-only`** (`PARTICIPACAO-EM-EXPOSICAO`, `PARTICIPACAO-EM-FEIRA`, `PARTICIPACAO-EM-OLIMPIADA`): informam confirmação no XSD oficial do Extrator (ausente da DTD comunitária) e não verificação de conformidade com a UI.
- **Fallbacks apenas legados** (`ENSINO-MEDIO`, `FORMACAO-COMPLEMENTAR-CURTA-DURACAO`, `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR`, `OUTRAS-PARTICIPACOES-EM-EVENTOS`, `@IDENTIFICADOR-CNPQ`, contêineres sob `DADOS-GERAIS` e `@SEQUENCIA-FORMACAO` em eventos): informam ausência tanto do XSD quanto da DTD comunitária e não verificação na UI.
- **Atributos em inglês** (`@NOME-CURSO-INGLES`, `@NOME-DO-EVENTO-INGLES`, `@TITULO-INGLES`): informam confirmação no XSD e na DTD do Extrator e não verificação na UI.

---

## 3. Extração de Produção Técnica (`PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA`)

Caminho XSD: `/CURRICULO-VITAE/PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA` (XSD linhas 2195–2211 e 2913–2929).
Tags irmãs válidas no XSD fora do escopo AD-012 (ex.: `OUTRA-PRODUCAO-TECNICA`, `CURSO-DE-CURTA-DURACAO-MINISTRADO`, etc.) são ignoradas sem poluir `unrecognized_elements`; tags desconhecidas sob `DEMAIS-TIPOS-DE-PRODUCAO-TECNICA` continuam sendo registradas em `unrecognized_elements`.

### 3.1 `APRESENTACAO-DE-TRABALHO` → `LattesCategory.APRESENTACAO_TRABALHO`
Fonte XSD: linhas 2931–2992.

| Campo `LattesRecord` | Origem XML no XSD | Regra / Invariante |
| :--- | :--- | :--- |
| `subtype` | Tag `APRESENTACAO-DE-TRABALHO` | `"APRESENTACAO_DE_TRABALHO"` |
| `sequence` | `@SEQUENCIA-PRODUCAO` | `None` se ausente ou branco |
| `title` | `DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO/@TITULO` (fallback `@TITULO-INGLES`) | Separado de `event_name` |
| `event_name` | `DETALHAMENTO-DA-APRESENTACAO-DE-TRABALHO/@NOME-DO-EVENTO` (fallback `@NOME-DO-EVENTO-INGLES`) | Separado de `title` |
| `institution` | `DETALHAMENTO-DA-APRESENTACAO-DE-TRABALHO/@INSTITUICAO-PROMOTORA` | Nunca preenchido com cidade/local |
| `city` / `location` | `@CIDADE-DA-APRESENTACAO` / `@LOCAL-DA-APRESENTACAO` | `None` se ausentes |
| `start_year` / `end_year` | `DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO/@ANO` | `int` estrito (`LattesNumericValueError` se inválido) |
| `nature_raw` | `DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO/@NATUREZA` | Preserva bruto (`CONFERENCIA`, `COMUNICACAO`, etc.) |
| `participation_role` | — | **Sempre `None`:** nunca inferir `"PALESTRANTE"` a partir de `NATUREZA="CONFERENCIA"` |
| `workload_hours` / `status` / `validation_code` | — | **Sempre `None`** (XSD não declara carga horária, status ou código de autenticação) |
| `provenance.raw_attributes` | Todos os atributos do nó e subnós | Preserva `@PAIS`, `@IDIOMA`, `@DOI`, `@FLAG-*`, `@TITULO-INGLES`, etc. |

### 3.2 `ORGANIZACAO-DE-EVENTO` → `LattesCategory.ORGANIZACAO_EVENTO`
Fonte XSD: linhas 3415–3506.

| Campo `LattesRecord` | Origem XML no XSD | Regra / Invariante |
| :--- | :--- | :--- |
| `subtype` | Tag `ORGANIZACAO-DE-EVENTO` | `"ORGANIZACAO_DE_EVENTO"` |
| `sequence` | `@SEQUENCIA-PRODUCAO` | `None` se ausente ou branco |
| `title` | `DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@TITULO` (fallback `@TITULO-INGLES`) | Preserva o título declarado no XML |
| `event_name` | — | `None` (`DETALHAMENTO-DA-ORGANIZACAO-DE-EVENTO` não declara `@NOME-DO-EVENTO` no XSD) |
| `institution` | `DETALHAMENTO-DA-ORGANIZACAO-DE-EVENTO/@INSTITUICAO-PROMOTORA` | `None` se ausente |
| `city` / `location` | `DETALHAMENTO-DA-ORGANIZACAO-DE-EVENTO/@CIDADE` / `@LOCAL` | `None` se ausentes |
| `start_year` / `end_year` | `DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@ANO` | `int` estrito (`LattesNumericValueError` se inválido) |
| `nature_raw` | `DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@NATUREZA` | Preserva bruto (`ORGANIZACAO`, `CURADORIA`, `MONTAGEM`, `MUSEOLOGIA`, `NAO_INFORMADO`) |
| `participation_role` | Derivação estrutural da tag `ORGANIZACAO-DE-EVENTO` | `"ORGANIZADOR"` com evidência documentada pela tag de seção (`provenance.record_tag == "ORGANIZACAO-DE-EVENTO"`), preservando `nature_raw` |
| `workload_hours` / `status` / `validation_code` | — | **Sempre `None`** (XSD não declara `CARGA-HORARIA`; `@DURACAO-EM-SEMANAS` permanece em `provenance.raw_attributes`) |
| `provenance.raw_attributes` | Todos os atributos do nó e subnós | Preserva `@TIPO`, `@PAIS`, `@IDIOMA`, `@MEIO-DE-DIVULGACAO`, `@DURACAO-EM-SEMANAS`, `@FLAG-*`, etc. |

---

## 4. Tabela Explícita de Papéis em Eventos (`PARTICIPATION_ROLE_MAP`)

Normalização pura (`normalize_role_token`: remoção de acentos via NFKD, `casefold()`, troca de `-`/`_` por espaço e colapso de espaços) consultada em `PARTICIPATION_ROLE_MAP`:

| Tokens normalizados inequívocos | `participation_role` |
| :--- | :--- |
| `ouvinte` | `"OUVINTE"` |
| `palestrante`, `conferencista` | `"PALESTRANTE"` |
| `apresentador`, `apresentadora`, `apresentacao de trabalho` | `"APRESENTADOR"` |
| `organizador`, `organizadora`, `comissao organizadora` | `"ORGANIZADOR"` |
| `participante`, `congressista` | `"PARTICIPANTE"` |

**Regras de segurança semântica:**
- Valores desconhecidos (ex.: `"Debatedor de Mesa"`, `"Presencial"` isolado) mantêm `participation_role = None`, preservam os valores brutos em `participation_type_raw` / `participation_form_raw` e registram aviso em `unverified_variants`.
- Conflito quando `@TIPO-PARTICIPACAO` e `@FORMA-PARTICIPACAO` mapeiam para papéis canônicos distintos mantém `participation_role = None` e registra aviso em `unverified_variants`.

---

## 5. Fixtures Sintéticas (`tests/fixtures/m1-technical/`) e Validação Offline XSD

Validadas em contêiner descartável `grammar-lxml-scratch:tmp` (`lxml 6.1.3` / `libxml2 2.14.6`) com `--network none --read-only` e `XMLParser(resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False, attribute_defaults=False)`:

| Arquivo | Bytes | SHA-256 | XSD CNPq (2022) | DTD (2010) |
| :--- | :---: | :--- | :---: | :---: |
| `curriculo_tecnico_producao_completa.xml` | 5128 | `9653f6df970ee0bebf571f85a8b77da5969791ec1d904eaa3272bb2054127795` | **Válido (0 erros)** | Inválido (25 erros esperados: `SEXO` opcional, `WEB`, `FLAG-DIVULGACAO-CIENTIFICA`, `PARTICIPACAO-EM-OLIMPIADA` `XSD-only`) |
| `curriculo_tecnico_ausencias_e_acentuacao.xml` | 2141 | `674d3cd5fdef395dd1810f7ead41708b42ffabb754426079fefff4b0628f6a44` | **Válido (0 erros)** | Inválido (6 erros esperados: `SEXO` opcional e `PARTICIPACAO-EM-OLIMPIADA` `XSD-only`) |
| `manifest.json` | 15979 | `21f1df3cb5dccb71e8ad7ccf83a968299ec51bd810ac7bb908450933d8aa2cbd` | — | — |

---

## 6. Testes Implementados

- [`tests/test_parser_technical.py`](../../../comprova-lattes-api/tests/test_parser_technical.py): manifesto `m1-technical/`, invariantes XSD/segurança, transcodificação estrita `UTF-8` ↔ `ISO-8859-1`, extração de `APRESENTACAO-DE-TRABALHO` (incluindo `NATUREZA="CONFERENCIA"` sem inferir `PALESTRANTE`), `ORGANIZACAO-DE-EVENTO` (`ORGANIZADOR` via tag com `nature_raw` preservado), `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, `PARTICIPACAO-EM-OLIMPIADA`, tabela de papéis/desconhecidos/conflitos/ausências, preservação de `PAIS`/`IDIOMA` na proveniência, ausência de `CARGA-HORARIA` e limites `defusedxml`/`max_depth`/`LattesNumericValueError`.
- [`tests/test_parser_xsd_mapping.py`](../../../comprova-lattes-api/tests/test_parser_xsd_mapping.py): verificação dos mapas XSD (`ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, `PARTICIPACAO-EM-OLIMPIADA`, `APRESENTACAO-DE-TRABALHO`, `ORGANIZACAO-DE-EVENTO`, `PARTICIPATION_ROLE_MAP`), ausência de avisos `"pendente DTD"` e de alegação de conformidade UI nas variantes confirmadas, e tratamento de tags irmãs fora do escopo AD-012 vs tags desconhecidas sob `DEMAIS-TIPOS-DE-PRODUCAO-TECNICA`.
