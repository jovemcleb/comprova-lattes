# Mapeamento XML Lattes → Schemas Pydantic (Alinhado ao XSD Oficial do Extrator CNPq)

**Status:** Alinhado ao XSD oficial do **Extrator Lattes** CNPq (`AD-011`, análise em [grammar-analysis.md](grammar-analysis.md)); **M1 não está completo** (confirmação do orientador para o XSD como alternativa à DTD permanece pendente; ampliação técnica implementada em AD-012).

> [!WARNING]
> **Escopo de comprovação estrutural (sem equivalência implícita com a UI):**
> - A fonte primária deste documento é o **XSD oficial do Extrator Lattes CNPq** (`xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd`, atualizado em 12/09/2022, SHA-256 `06b3976943f73b4e66f4ece70c5d9358d244fc080704c518a8d533d84eea6214`).
> - A **DTD comunitária** (`LMPLCurriculo.DTD`, último commit `a295d38…` em 2010-10-18) é usada apenas como referência histórica de comparação.
> - **Não se afirma equivalência integral entre o XML do Extrator e o XML exportado pela interface web (UI) do Lattes.** Nenhum XML real de usuário foi analisado; itens ausentes de ambas as gramáticas são classificados como **fallback legado** ou **desconhecido na UI / não comprovado**.

---

## 1. Convenções e Classificação de Fontes

### 1.1 Legenda de classificação de origem

| Classificação | Significado | Política neste marco |
| :--- | :--- | :--- |
| **Oficial Extrator (XSD)** | Elemento, caminho, ordem ou atributo declarado no XSD oficial CNPq (2022-09-12). Subdivide-se em `XSD + DTD` (presente em ambas) ou `XSD-only` (presente apenas no XSD). | Referência estrutural primária (`AD-011`). |
| **Fallback legado** | Construção observada apenas nos protótipos legados (`parser_lattes.py` / `lattesXmlParser.ts`), ausente tanto do XSD quanto da DTD comunitária. | Tolerância mantida no parser atual sem alteração nesta entrega; remoção/diagnóstico depende da decisão D4. |
| **Desconhecido na UI / não comprovado** | Atributo ou uso indevido em contexto não declarado no XSD nem na DTD (sem evidência de exportação real na UI). | Não usar em fixtures conformes; tratar como indevido na referência oficial até eventual verificação em XML real autorizado. |

### 1.2 Invariantes de mapeamento

- **Ausência = `None`:** Atributos ausentes ou compostos apenas por espaços resultam em `None`, sem strings sentinelas inventadas.
- **Proveniência obrigatória:** Cada `LattesRecord` preserva `provenance.parent_tag`, `provenance.section_tag`, `provenance.record_tag`, `provenance.sequence_attribute` e `provenance.raw_attributes`.
- **Separação geográfica/institucional:** `institution` recebe apenas `@NOME-INSTITUICAO`; `@CIDADE-DO-EVENTO` e `@LOCAL-DO-EVENTO` vão para `city` e `location`.
- **Integridade numérica:** Anos usam `int` estrito; `workload_hours` usa `Decimal` finito. Nenhuma das duas gramáticas tipa anos ou `CARGA-HORARIA` numericamente (`anySimpleType` / `CDATA`).

---

## 2. Cabeçalho do Currículo (`LattesCurriculum`)

Ordem obrigatória dos filhos da raiz `CURRICULO-VITAE` no XSD (`xs:sequence`):
`DADOS-GERAIS` (`1..1`), `PRODUCAO-BIBLIOGRAFICA?`, `PRODUCAO-TECNICA?`, `OUTRA-PRODUCAO?`, `DADOS-COMPLEMENTARES?`.

Atributos obrigatórios no XSD:
- `CURRICULO-VITAE/@SISTEMA-ORIGEM-XML` (obrigatório em XSD e DTD).
- `DADOS-GERAIS/@NOME-COMPLETO`, `@NOME-EM-CITACOES-BIBLIOGRAFICAS`, `@NACIONALIDADE`, `@PERMISSAO-DE-DIVULGACAO` (`ENUM(SIM|NAO)`) — obrigatórios em XSD e DTD.
- `DADOS-GERAIS/@SEXO` (`ENUM(MASCULINO|FEMININO)`): **opcional no XSD** (`DTD-only` obrigatório).

| Campo `LattesCurriculum` | Caminho / Atributo | Classificação de origem | Observações XSD × DTD × Parser atual |
| :--- | :--- | :--- | :--- |
| `lattes_id` | `/CURRICULO-VITAE/@NUMERO-IDENTIFICADOR` | **Oficial Extrator (XSD + DTD)** | Opcional em ambas as gramáticas. |
| `lattes_id` (fallback) | `/CURRICULO-VITAE/@IDENTIFICADOR-CNPQ` | **Fallback legado** (`parser_lattes.py`) | Inexistente no XSD e na DTD. Ainda tolerado pelo parser atual com registro em `unverified_variants`. |
| `updated_at` | `/CURRICULO-VITAE/@DATA-ATUALIZACAO` | **Oficial Extrator (XSD + DTD)** | Opcional; preservado bruto (`DDMMAAAA`, sem substituir por `HORA-ATUALIZACAO`). XSD define `FORMATO-DATA-ATUALIZACAO` com default `DDMMAAAA`. |
| `full_name` | `DADOS-GERAIS/@NOME-COMPLETO` | **Oficial Extrator (XSD + DTD)** | Obrigatório nas duas gramáticas. |
| `citation_names` | `DADOS-GERAIS/@NOME-EM-CITACOES-BIBLIOGRAFICAS` | **Oficial Extrator (XSD + DTD)** | Obrigatório nas duas gramáticas; parser divide por `;`. |
| `summary` | `DADOS-GERAIS/RESUMO-CV/@TEXTO-RESUMO-CV-RH` | **Oficial Extrator (XSD + DTD)** | `RESUMO-CV` é o primeiro filho opcional (`0..1`) de `DADOS-GERAIS`. |
| `summary` (alternativa XSD) | `DADOS-GERAIS/@TEXTO-RESUMO-CV-RH` | **Oficial Extrator (XSD + DTD)** | Declarado opcionalmente também como atributo direto de `DADOS-GERAIS` no XSD/DTD; **pendência:** `xml_parser.py` lê apenas `RESUMO-CV/@TEXTO-RESUMO-CV-RH`. |

---

## 3. Contêineres das Três Seções

| Seção / Categoria | Caminho no XML | Classificação de origem | Observação |
| :--- | :--- | :--- | :--- |
| Seção 1 (`FORMACAO_ACADEMICA`) | `/CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO` | **Oficial Extrator (XSD + DTD)** | Filho único (`0..1`) de `DADOS-GERAIS`, após `RESUMO-CV?`, `OUTRAS-INFORMACOES-RELEVANTES?`, `ENDERECO?`. |
| Seção 2 (`FORMACAO_COMPLEMENTAR`) | `/CURRICULO-VITAE/DADOS-COMPLEMENTARES/FORMACAO-COMPLEMENTAR` | **Oficial Extrator (XSD + DTD)** | Primeiro filho de `DADOS-COMPLEMENTARES` (`0..unbounded` no XSD / `0..1` na DTD). |
| Seção 2 (fallback legado) | `/CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-COMPLEMENTAR` | **Fallback legado** (`lattesXmlParser.ts`) | Inexistente no XSD e na DTD; tolerado pelo parser atual com registro em `unverified_variants`. |
| Seção 3 (`PARTICIPACAO_EVENTO`) | `/CURRICULO-VITAE/DADOS-COMPLEMENTARES/PARTICIPACAO-EM-EVENTOS-CONGRESSOS` | **Oficial Extrator (XSD + DTD)** | Filho (`0..1`) de `DADOS-COMPLEMENTARES` após `FORMACAO-COMPLEMENTAR`, `PARTICIPACAO-EM-BANCA-*`. |
| Seção 3 (fallback legado) | `/CURRICULO-VITAE/DADOS-GERAIS/PARTICIPACAO-EM-EVENTOS-CONGRESSOS` | **Fallback legado** (`lattesXmlParser.ts`) | Inexistente no XSD e na DTD; tolerado pelo parser atual com registro em `unverified_variants`. |

---

## 4. Seção 1 — Formação Acadêmica / Titulação (`LattesCategory.FORMACAO_ACADEMICA`)

### 4.1 Tags de registro (ordem obrigatória do XSD em `FORMACAO-ACADEMICA-TITULACAO`)

No XSD (e na DTD), os filhos de `FORMACAO-ACADEMICA-TITULACAO` seguem sequência ordenada fixa (`0..unbounded` cada), exatamente na ordem da tabela abaixo:

| Ordem XSD | Tag XML | `subtype` | Classificação de origem | Suporte atual no parser (`mappings.py`) |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `GRADUACAO` | `GRADUACAO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 2 | `ESPECIALIZACAO` | `ESPECIALIZACAO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 3 | `MESTRADO` | `MESTRADO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 4 | `DOUTORADO` | `DOUTORADO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 5 | `POS-DOUTORADO` | `POS_DOUTORADO` | **Oficial Extrator (XSD + DTD)** | Mapeada; nota atual distingue comprovação no Extrator de compatibilidade UI não verificada. |
| 6 | `LIVRE-DOCENCIA` | `LIVRE_DOCENCIA` | **Oficial Extrator (XSD + DTD)** | Mapeada (idem `UNVERIFIED_VARIANT_TAGS`). |
| 7 | `CURSO-TECNICO-PROFISSIONALIZANTE` | `CURSO_TECNICO_PROFISSIONALIZANTE` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 8 | `MESTRADO-PROFISSIONALIZANTE` | `MESTRADO_PROFISSIONALIZANTE` | **Oficial Extrator (XSD + DTD)** | Mapeada (idem `UNVERIFIED_VARIANT_TAGS`). |
| 9 | `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU` | `ENSINO_FUNDAMENTAL` | **Oficial Extrator (XSD + DTD)** | Mapeada e testada na ampliação AD-012. |
| 10 | `ENSINO-MEDIO-SEGUNDO-GRAU` | `ENSINO_MEDIO` | **Oficial Extrator (XSD + DTD)** | Mapeada (idem `UNVERIFIED_VARIANT_TAGS`). |
| 11 | `RESIDENCIA-MEDICA` | `RESIDENCIA_MEDICA` | **Oficial Extrator (XSD + DTD)** | Mapeada (idem `UNVERIFIED_VARIANT_TAGS`). |
| 12 | `APERFEICOAMENTO` | `APERFEICOAMENTO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| — | `ENSINO-MEDIO` | `ENSINO_MEDIO` | **Fallback legado** (`parser_lattes.py`) | Tolerada em `mappings.py`, ausente do XSD e da DTD. |

### 4.2 Atributos da Seção 1

| Campo `LattesRecord` | Atributo XML | Classificação de origem e contexto válido no XSD | Observações / Pendências |
| :--- | :--- | :--- | :--- |
| `sequence` | `@SEQUENCIA-FORMACAO` | **Oficial Extrator (XSD + DTD)** em todas as 12 tags | `None` se ausente. |
| `institution` | `@NOME-INSTITUICAO` | **Oficial Extrator (XSD + DTD)** em todas as 12 tags | `None` se ausente. |
| `institution_acronym` | `@SIGLA-INSTITUICAO` | **Desconhecido na UI / não comprovado (indevido na Seção 1)** | **Não existe em nenhuma das 12 tags** (ocorre no XSD apenas em `INFORMACAO-ADICIONAL-INSTITUICAO`). Tolerado apenas por compatibilidade legada em `xml_parser.py`. |
| `title` | `@NOME-CURSO` | **Oficial Extrator (XSD + DTD)** em `GRADUACAO`, `ESPECIALIZACAO`, `MESTRADO`, `DOUTORADO`, `CURSO-TECNICO-PROFISSIONALIZANTE`, `MESTRADO-PROFISSIONALIZANTE`, `APERFEICOAMENTO` | Ausente em `POS-DOUTORADO`, `LIVRE-DOCENCIA`, `RESIDENCIA-MEDICA`, `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, `ENSINO-MEDIO-SEGUNDO-GRAU`. |
| `title` | `@NOME-CURSO-INGLES` | **Oficial Extrator (XSD + DTD)** nas mesmas tags acima + `POS-DOUTORADO` (em `CURSO-TECNICO-PROFISSIONALIZANTE` é `XSD-only`) | Comprovado no XSD; nota de referência atualizada na ampliação técnica. |
| `title` | `@TITULO-DA-DISSERTACAO-TESE` | **Oficial Extrator (XSD + DTD)** em `MESTRADO`, `DOUTORADO`, `MESTRADO-PROFISSIONALIZANTE` | Extraído pelo parser atual. |
| `title` | `@TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO` | **Oficial Extrator (XSD + DTD)** em `GRADUACAO` | Extraído pelo parser atual. |
| `title` (não extraído) | `@TITULO-DA-MONOGRAFIA` (`ESPECIALIZACAO`, `APERFEICOAMENTO`), `@TITULO-DO-TRABALHO` (`POS-DOUTORADO`, `LIVRE-DOCENCIA`), `@TITULO-DA-RESIDENCIA-MEDICA` (`RESIDENCIA-MEDICA`) | **Oficial Extrator (XSD + DTD)** | **Pendência de suporte:** `xml_parser.py` ainda não lê esses 3 atributos quando `@NOME-CURSO` está ausente. |
| `start_year` | `@ANO-DE-INICIO` | **Oficial Extrator (XSD + DTD)** em todas, **exceto `LIVRE-DOCENCIA`** | `int` estrito ou `None`. |
| `end_year` | `@ANO-DE-CONCLUSAO` / `@ANO-DE-OBTENCAO-DO-TITULO` | **Oficial Extrator (XSD + DTD)**: `ANO-DE-CONCLUSAO` em todas exceto `LIVRE-DOCENCIA`; `ANO-DE-OBTENCAO-DO-TITULO` em `MESTRADO`, `DOUTORADO`, `POS-DOUTORADO`, `LIVRE-DOCENCIA`, `MESTRADO-PROFISSIONALIZANTE` | `int` estrito ou `None`. |
| `workload_hours` | `@CARGA-HORARIA` | **Oficial Extrator (XSD + DTD) APENAS em `ESPECIALIZACAO` e `APERFEICOAMENTO`** | **Indevido nas demais 10 tags** (`GRADUACAO`, `MESTRADO`, `DOUTORADO`, `POS-DOUTORADO`, `LIVRE-DOCENCIA`, `CURSO-TECNICO-PROFISSIONALIZANTE`, `MESTRADO-PROFISSIONALIZANTE`, `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, `ENSINO-MEDIO-SEGUNDO-GRAU`, `RESIDENCIA-MEDICA`). Nessas 10 tags, `@CARGA-HORARIA` não existe no XSD nem na DTD (tratamento de legado/UI desconhecido). |
| `status` | `@STATUS-DO-CURSO` | **Oficial Extrator (XSD + DTD)** (`ENUM(EM_ANDAMENTO\|CONCLUIDO\|INCOMPLETO)` em 10 tags; sem enum no XSD em `POS-DOUTORADO`; ausente em `LIVRE-DOCENCIA`) | `POS-DOUTORADO` possui também `@STATUS-DO-ESTAGIO` no XSD (não mapeado). |
| `validation_code` | — (`CODIGO-CURSO-CAPES`) | **Sem atributo de autenticação no XSD** | `CODIGO-CURSO-CAPES` identifica curso, não autentica certificado; mantido `None` e preservado em `provenance.raw_attributes`. |

---

## 5. Seção 2 — Formação Complementar (`LattesCategory.FORMACAO_COMPLEMENTAR`)

### 5.1 Tags de registro (ordem obrigatória do XSD em `FORMACAO-COMPLEMENTAR`)

| Ordem XSD | Tag XML | `subtype` | Classificação de origem | Suporte atual no parser (`mappings.py`) |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA` | `EXTENSAO_UNIVERSITARIA` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 2 | `MBA` | `MBA` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| 3 | `FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO` | `CURTA_DURACAO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 4 | `OUTROS` | `OUTROS` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| — | `FORMACAO-COMPLEMENTAR-CURTA-DURACAO` | `CURTA_DURACAO` | **Fallback legado** (`lattesXmlParser.ts`) | Tolerada em `mappings.py`, ausente do XSD e da DTD. |
| — | `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR` | `OUTROS` | **Fallback legado** (`parser_lattes.py`) | Tolerada em `mappings.py`, ausente do XSD e da DTD. |

### 5.2 Atributos da Seção 2

| Campo `LattesRecord` | Atributo XML | Classificação de origem no XSD | Observações / Pendências |
| :--- | :--- | :--- | :--- |
| `sequence` | `@SEQUENCIA-FORMACAO` | **Oficial Extrator (XSD + DTD)** nas 4 tags | `None` se ausente. |
| `institution` | `@NOME-INSTITUICAO` | **Oficial Extrator (XSD + DTD)** nas 4 tags | `None` se ausente. |
| `institution_acronym` | `@SIGLA-INSTITUICAO` | **Desconhecido na UI / não comprovado (indevido na Seção 2)** | **Inexistente nas 4 tags** no XSD e na DTD. |
| `title` | `@NOME-CURSO`, `@NOME-CURSO-INGLES` | **Oficial Extrator (XSD + DTD)** nas 4 tags | `MBA` declara também `@TITULO-DA-MONOGRAFIA` (não extraído pelo parser atual — pendência). |
| `start_year` | `@ANO-DE-INICIO` | **Oficial Extrator (XSD + DTD)** nas 4 tags | `int` estrito ou `None`. |
| `end_year` | `@ANO-DE-CONCLUSAO` | **Oficial Extrator (XSD + DTD)** nas 4 tags | `MBA` declara também `@ANO-DE-OBTENCAO-DO-TITULO` (não extraído nesta seção — pendência). |
| `workload_hours` | `@CARGA-HORARIA` | **Oficial Extrator (XSD + DTD)** nas 4 tags | **Permitido pelo XSD em toda a Seção 2**; `Decimal` finito (preserva frações como `1.5` e `40.75`). |
| `status` | `@STATUS-DO-CURSO` | **Oficial Extrator (XSD + DTD)** (`ENUM(EM_ANDAMENTO\|CONCLUIDO\|INCOMPLETO)`) | `ActivityStatus` ou `None`. |

---

## 6. Seção 3 — Participação em Eventos (`LattesCategory.PARTICIPACAO_EVENTO`)

> [!NOTE]
> A modelagem semântica do papel/função de participação em eventos (`event_role`, AD-010) é tratada exclusivamente em [event-role-contract.md](../m2-matcher/event-role-contract.md) e não faz parte desta atualização de mapeamento estrutural.

### 6.1 Tags de registro (ordem obrigatória do XSD em `PARTICIPACAO-EM-EVENTOS-CONGRESSOS`)

| Ordem XSD | Tag XML | `subtype` | Classificação de origem | Suporte atual no parser (`mappings.py`) |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `PARTICIPACAO-EM-CONGRESSO` | `CONGRESSO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 2 | `PARTICIPACAO-EM-FEIRA` | `FEIRA` | **Oficial Extrator (XSD-only)** | Mapeada (ausente da DTD histórica de 2010). |
| 3 | `PARTICIPACAO-EM-SEMINARIO` | `SEMINARIO` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| 4 | `PARTICIPACAO-EM-SIMPOSIO` | `SIMPOSIO` | **Oficial Extrator (XSD + DTD)** | Mapeada. |
| 5 | `PARTICIPACAO-EM-OFICINA` | `OFICINA` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| 6 | `PARTICIPACAO-EM-ENCONTRO` | `ENCONTRO` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| 7 | `PARTICIPACAO-EM-EXPOSICAO` | `EXPOSICAO` | **Oficial Extrator (XSD-only)** | Mapeada (ausente da DTD histórica; ainda em `UNVERIFIED_VARIANT_TAGS`). |
| 8 | `PARTICIPACAO-EM-OLIMPIADA` | `OLIMPIADA` | **Oficial Extrator (XSD-only)** | Mapeada e testada na ampliação AD-012. |
| 9 | `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` | `OUTRAS_PARTICIPACOES` | **Oficial Extrator (XSD + DTD)** | Mapeada (ainda em `UNVERIFIED_VARIANT_TAGS`). |
| — | `OUTRAS-PARTICIPACOES-EM-EVENTOS` | `OUTRAS_PARTICIPACOES` | **Fallback legado** (`parser_lattes.py`) | Tolerada em `mappings.py`, ausente do XSD e da DTD. |

### 6.2 Subnós e atributos da Seção 3

No XSD, cada elemento de evento tem **apenas** o atributo `@SEQUENCIA-PRODUCAO` no nó pai e recebe seus dados nos subnós ordenados:
1. `DADOS-BASICOS-DA-PARTICIPACAO-EM-<X>` (ou `DADOS-BASICOS-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`) `[0..1]`
2. `DETALHAMENTO-DA-PARTICIPACAO-EM-<X>` (ou `DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`) `[0..1]`
3. `PARTICIPANTE-DE-EVENTOS-CONGRESSOS*`, `PALAVRAS-CHAVE?`, `AREAS-DO-CONHECIMENTO?`, `SETORES-DE-ATIVIDADE?`, `INFORMACOES-ADICIONAIS?`

| Campo `LattesRecord` | Localização / Atributo XML | Classificação de origem no XSD | Observações e regras |
| :--- | :--- | :--- | :--- |
| `sequence` | Nó pai `@SEQUENCIA-PRODUCAO` | **Oficial Extrator (XSD + DTD)** (XSD-only em `FEIRA`, `EXPOSICAO`, `OLIMPIADA`) | Único atributo do nó pai. |
| `sequence` (fallback) | Nó pai `@SEQUENCIA-FORMACAO` | **Fallback legado** (`lattesXmlParser.ts`) | Inexistente em eventos no XSD/DTD. |
| `institution` | `DETALHAMENTO-*/@NOME-INSTITUICAO` | **Oficial Extrator (XSD + DTD)** (XSD-only em `FEIRA`, `EXPOSICAO`, `OLIMPIADA`) | **Proibido preencher com `@LOCAL-DO-EVENTO` ou `@CIDADE-DO-EVENTO`.** |
| `institution` (fallbacks) | `DADOS-BASICOS-*/@NOME-INSTITUICAO` ou nó pai `@NOME-INSTITUICAO` | **Fallback legado** | Inexistentes em ambas as gramáticas. |
| `institution_acronym` | `@SIGLA-INSTITUICAO` | **Desconhecido na UI / não comprovado (indevido na Seção 3)** | Inexistente em todos os elementos de evento. |
| `city` | `DETALHAMENTO-*/@CIDADE-DO-EVENTO` | **Oficial Extrator (XSD + DTD)** | Fallback no nó pai é **fallback legado**. |
| `location` | `DETALHAMENTO-*/@LOCAL-DO-EVENTO` | **Oficial Extrator (XSD + DTD)** | Fallback no nó pai é **fallback legado**. |
| `event_name` | `DETALHAMENTO-*/@NOME-DO-EVENTO`, `@NOME-DO-EVENTO-INGLES` | **Oficial Extrator (XSD + DTD)** | Fallback no nó pai é **fallback legado**. Nota atual distingue gramática confirmada de compatibilidade UI não verificada. |
| `title` | `DADOS-BASICOS-*/@TITULO` | **Oficial Extrator (XSD + DTD)** | `DADOS-BASICOS-*` também declara `@TITULO-INGLES`, `@NATUREZA`, `@TIPO-PARTICIPACAO`, `@FORMA-PARTICIPACAO`, `@PAIS`, `@IDIOMA`, `@MEIO-DE-DIVULGACAO` (inclui `WEB` no XSD), `@FLAG-DIVULGACAO-CIENTIFICA` (`XSD-only`). Fallback no nó pai é **fallback legado**. |
| `start_year` / `end_year` | `DADOS-BASICOS-*/@ANO` | **Oficial Extrator (XSD + DTD)** | `int` estrito ou `None`. Fallback no nó pai é **fallback legado**. |
| `workload_hours` | `@CARGA-HORARIA` (qualquer subnó ou nó pai de evento) | **Desconhecido na UI / não comprovado (indevido na Seção 3)** | **Nenhum elemento de evento declara `CARGA-HORARIA` no XSD nem na DTD.** Fixtures conformes mantêm `workload_hours=None` em eventos; tolerância de leitura no parser atual é apenas para compatibilidade legada. |
| `status` | — | **Sem atributo de status no XSD/DTD** | Mantido `None` (não forçar `PARTICIPOU`). |

---

## 7. Pendências Identificadas para Próxima Entrega de Código

Esta revisão documental não altera código do parser nem remove tolerâncias existentes (`mappings.py` / `xml_parser.py`). Ficam registradas como pendências explícitas:

1. **Tags incorporadas em AD-012:** `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU` e `PARTICIPACAO-EM-OLIMPIADA` agora mapeadas e testadas em `m1-technical/`.
2. **Atributos de título/data/resumo declarados no XSD e não lidos por `xml_parser.py`:** `ESPECIALIZACAO/@TITULO-DA-MONOGRAFIA`, `APERFEICOAMENTO/@TITULO-DA-MONOGRAFIA`, `POS-DOUTORADO/@TITULO-DO-TRABALHO`, `LIVRE-DOCENCIA/@TITULO-DO-TRABALHO`, `RESIDENCIA-MEDICA/@TITULO-DA-RESIDENCIA-MEDICA`, `MBA/@TITULO-DA-MONOGRAFIA`, `MBA/@ANO-DE-OBTENCAO-DO-TITULO`, `DADOS-GERAIS/@TEXTO-RESUMO-CV-RH` (quando `RESUMO-CV` estiver ausente) e `POS-DOUTORADO/@STATUS-DO-ESTAGIO`.
3. **Mensagens reconciliadas em AD-012:** notas atuais distinguem XSD + DTD, XSD-only e fallbacks legados, sem alegar conformidade UI.
4. **Política para fallbacks legados e atributos indevidos (decisão D4/D5 em [grammar-analysis.md](grammar-analysis.md)):** decidir se `ENSINO-MEDIO`, `FORMACAO-COMPLEMENTAR-CURTA-DURACAO`, `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR`, `OUTRAS-PARTICIPACOES-EM-EVENTOS`, contêineres sob `DADOS-GERAIS`, `@IDENTIFICADOR-CNPQ`, `@SEQUENCIA-FORMACAO` em eventos, atributos diretos no nó pai em eventos, `@SIGLA-INSTITUICAO` e `@CARGA-HORARIA` fora de especialização/aperfeiçoamento/formação complementar passam a gerar diagnóstico explícito ou permanecem tolerados caso ocorram na exportação da UI.
5. **Validação em XML real de exportação UI e confirmação do orientador:** pendente para fechamento do marco M1.

## Ampliação técnica AD-012

O mapeamento detalhado de `APRESENTACAO-DE-TRABALHO` e `ORGANIZACAO-DE-EVENTO` pertence a [technical-production.md](technical-production.md). São categorias próprias, mantendo título, evento, natureza e proveniência separados. Não incluem artigos nem anais.
