# Contrato Mínimo de Papel de Participação em Eventos (`AD-010`)

> [!WARNING]
> **Contrato misto: M1 implementado; M2/M3 em proposta, não implementados.**
> A ampliação M1 está em `technical-production.md` (AD-012). Esta reconciliação altera somente documentação; extrator, matcher e revisão humana ainda não foram implementados.
> A análise da gramática está registrada em `m1-parser/grammar-analysis.md`. AD-011 usa XSD do Extrator como referência principal e DTD comunitária como comparação histórica, sem comprovar equivalência UI nem encerrar o requisito DTD do professor.

**Última atualização:** 2026-11-13
**Base consultada:** `AGENTS.md`, `.specs/project/STATE.md` (`AD-010`), `.specs/features/m1-parser/spec.md`, `.specs/features/m1-parser/xml-mapping.md`, `.specs/features/m2-matcher/proposal.md`, `comprova-lattes-api/src/comprova_lattes/schemas/lattes.py`, `comprova-lattes-api/src/comprova_lattes/parser/mappings.py`, `comprova-lattes-api/src/comprova_lattes/parser/xml_parser.py`, `comprova-lattes-api/tests/test_parser.py`, legado Python (`references/legacy-drive/sharing/lattes_validator/`), legado TypeScript (`references/legacy-drive/sharing/src/`) e arquivos brutos locais `references/xml-grammars/cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd` e `references/xml-grammars/community-dtd/LMPLCurriculo.DTD`.

---

## 1. Mapeamento Local Observado (Tags, Atributos e Lacunas)

### 1.1 Diagnóstico anterior à ampliação AD-012 no Código M1 (`comprova-lattes-api/`)

| Artefato | Comportamento observado | Lacuna frente à `AD-010` |
| :--- | :--- | :--- |
| `schemas/lattes.py:76-81,106-128` | `LattesCategory` cobre estritamente `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`. `LattesRecord` (`extra="forbid"`) possui `subtype`, `title`, `event_name`, `city`, `location`, `status`, `provenance`. | Não possui campos dedicados para papel de participação (`TIPO-PARTICIPACAO`), forma (`FORMA-PARTICIPACAO`) nem `NATUREZA`. |
| `parser/mappings.py:36-46` | `EVENT_TAG_SUBTYPES` mapeia 9 tags de evento para `subtype` (`CONGRESSO`, `SEMINARIO`, `SIMPOSIO`, `OFICINA`, `ENCONTRO`, `EXPOSICAO`, `FEIRA`, `OUTRAS_PARTICIPACOES`). | `subtype` representa o **tipo do evento pela tag**, não o papel da pessoa. `PARTICIPACAO-EM-OLIMPIADA` (presente no XSD) não consta no mapa. |
| `parser/xml_parser.py:545-663` | `_extract_event_records` lê `DADOS-BASICOS-*/@TITULO` → `title`, `DETALHAMENTO-*/@NOME-DO-EVENTO` → `event_name`, define `status=None` e preserva todos os atributos em `provenance.raw_attributes` (`test_parser.py:555-582`). | `TIPO-PARTICIPACAO`, `FORMA-PARTICIPACAO` e `NATUREZA` existem apenas dentro de `provenance.raw_attributes`, sem campo tipado nem normalização. |

**Estado atual:** cinco categorias e quatro campos opcionais de papel/natureza implementados; olimpíada mapeada. `technical-production.md` é a fonte do mapeamento técnico. Os campos brutos canônicos removem espaços externos; `provenance.raw_attributes` preserva os atributos originais. `ORGANIZADOR` derivado da tag é contexto estrutural, não prova de equivalência entre organização, curadoria, montagem e museologia no M2.

### 1.2 Referências Legadas (Python e TypeScript)

| Fonte local | Como tratava papel, natureza e título | Problema identificado |
| :--- | :--- | :--- |
| `references/legacy-drive/sharing/lattes_validator/parser_lattes.py:194-217` | Usava `attrs_dados.get("NATUREZA", "Congresso")` como `subtipo`; concatenava/substituía `titulo_atividade` por `TITULO` ou `NOME-DO-EVENTO`; forçava `situacao=PARTICIPOU`; não lia `TIPO-PARTICIPACAO` nem `FORMA-PARTICIPACAO`. | Confundia `NATUREZA` com subtipo, misturava título do trabalho e nome do evento e descartava papel explícito. |
| `references/legacy-drive/sharing/lattes_validator/modelos.py:74-86` e `esquema_documento.py` | `EntidadesDocumentoComprobatorio` não tinha `nome_evento` nem campo de papel de participação. | Impossível separar evento, título de palestra/trabalho e papel na extração. |
| `references/legacy-drive/sharing/src/parser/lattesXmlParser.ts:469-525` | Lia `@NATUREZA`, `@TIPO-PARTICIPACAO` e `@FORMA-PARTICIPACAO` para `metadadosOriginais`, mas colapsava `tituloAtividade = nomeDoEvento \|\| tituloTrabalho`. | Não expunha papel em contrato principal e misturava nome do evento com título do trabalho. |
| `references/legacy-drive/sharing/src/matching/levenshtein.ts:282` | Regex `PREFIXOS_RUIDO_CERTIFICADO` removia `^participacao como (ouvinte\|palestrante\|participante\|congressista\|autor\|apresentador) ...` como ruído. | Descartava justamente a evidência explícita de papel do certificado antes da comparação. |

### 1.3 Inspeção Bruta do XSD Oficial (2022) e DTD Comunitária

> [!IMPORTANT]
> **Escopo das três seções vs. Produção Técnica/Bibliográfica:** Os arquivos brutos locais mostram que **organização de eventos e apresentação de trabalhos vivem em tags dedicadas fora das três seções iniciais; incluídas no M1 por AD-012**. AD-012 acrescentou duas categorias próprias; artigos e trabalhos em anais permanecem fora do escopo.

| Elemento / Caminho XML | Fonte local verificada | Atributos relevantes observados | O que comprova |
| :--- | :--- | :--- | :--- |
| `DADOS-COMPLEMENTARES/PARTICIPACAO-EM-EVENTOS-CONGRESSOS/*` (`CONGRESSO`, `FEIRA`, `SEMINARIO`, `SIMPOSIO`, `OFICINA`, `ENCONTRO`, `EXPOSICAO`, `OLIMPIADA`, `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`) | XSD (`lines 5560-6204`); DTD (`lines 2033-2209`, sem `FEIRA`/`EXPOSICAO`/`OLIMPIADA`) | Em `DADOS-BASICOS-*`: `@NATUREZA`, `@TITULO`, `@ANO`, `@TIPO-PARTICIPACAO`, `@FORMA-PARTICIPACAO` (todos sem enumeração fechada no XSD/DTD). Em `DETALHAMENTO-*`: `@NOME-DO-EVENTO`, `@NOME-INSTITUICAO`, `@LOCAL-DO-EVENTO`, `@CIDADE-DO-EVENTO`. | `@TIPO-PARTICIPACAO` e `@FORMA-PARTICIPACAO` existem nas tags de participação em eventos, mas **sem lista fechada de valores** na gramática. `@NATUREZA` também é texto livre nesta seção. |
| `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA/APRESENTACAO-DE-TRABALHO` | XSD (`lines 2916, 2931-2992`); DTD (`lines 1052-1075`) | `DADOS-BASICOS-*`: `@NATUREZA` (enum XSD: `COMUNICACAO`, `CONFERENCIA`, `CONGRESSO`, `SEMINARIO`, `SIMPOSIO`, `OUTRA`, `NAO_INFORMADO`), `@TITULO`, `@ANO`. `DETALHAMENTO-*`: `@NOME-DO-EVENTO`, `@INSTITUICAO-PROMOTORA`, `@LOCAL-DA-APRESENTACAO`, `@CIDADE-DA-APRESENTACAO`. | Palestras/conferências e comunicações possuem seção própria em `PRODUCAO-TECNICA` (incluindo `NATUREZA="CONFERENCIA"`), fora das três seções iniciais e agora incluídas por AD-012. |
| `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA/ORGANIZACAO-DE-EVENTO` | XSD (`lines 2923, 3415-3506`); DTD (`lines 1052, 1220-1246`) | `DADOS-BASICOS-*`: `@TIPO` (`CONCERTO`, `CONCURSO`, `CONGRESSO`, `EXPOSICAO`, `FESTIVAL`, `FEIRA`, `OLIMPIADA`, `OUTRO`, `NAO_INFORMADO`), `@NATUREZA` (`CURADORIA`, `MONTAGEM`, `MUSEOLOGIA`, `ORGANIZACAO`, `NAO_INFORMADO`), `@TITULO`, `@ANO`. `DETALHAMENTO-*`: `@INSTITUICAO-PROMOTORA`, `@LOCAL`, `@CIDADE`. | Organização de eventos vive explicitamente em `PRODUCAO-TECNICA`, fora das três seções iniciais e agora incluídas por AD-012. |
| `PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS` | XSD (`lines 1398-1490`); DTD (`lines 644-660`) | `@NATUREZA` (`COMPLETO`, `RESUMO`, `RESUMO_EXPANDIDO`, `NAO_INFORMADO`), `@TITULO-DO-TRABALHO`, `@ANO-DO-TRABALHO`, `DETALHAMENTO-DO-TRABALHO/@NOME-DO-EVENTO`. | Trabalhos publicados em anais de eventos também vivem fora das 3 seções atuais. |

---

## 2. Distinção Conceitual Obrigatória (`AD-010`)

| Conceito | Significado | Origem no XML (M1) | Origem no Documento (M3) | Regra de não confusão |
| :--- | :--- | :--- | :--- | :--- |
| **Tipo de evento** (`subtype`) | Modalidade/categoria do evento em si (`CONGRESSO`, `SIMPOSIO`, `SEMINARIO`, etc.). | Nome da tag XML (ex.: `PARTICIPACAO-EM-CONGRESSO` → `CONGRESSO`). | Contexto/título do evento (informativo; `categoria_sugerida` não decide). | Não indica o papel da pessoa no evento. |
| **Natureza** (`nature_raw`) | Atributo XML `@NATUREZA` descrevendo natureza do registro/evento (ex.: `"Congresso"` em `DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO`). | `@NATUREZA` em `DADOS-BASICOS-*`. | Não é papel de participação. | **Nunca** inferir `PALESTRANTE` ou `OUVINTE` a partir de `NATUREZA="Congresso"`. |
| **Nome do evento** (`event_name`) | Nome oficial do congresso, simpósio, oficina ou encontro. | `DETALHAMENTO-*/@NOME-DO-EVENTO` (ou `@NOME-DO-EVENTO-INGLES` / pai). | `event_name` extraído somente quando explícito. | Nunca concatenar com `title` nem preencher com cidade/local. |
| **Título específico** (`title` / `activity_title`) | Título da palestra, conferência, comunicação ou trabalho específico apresentado. | `DADOS-BASICOS-*/@TITULO` (ou pai `@TITULO`). | `activity_title` extraído somente quando explícito. | Ausência (`None`) no documento não invalida automaticamente participação/palestra. |
| **Papel de participação** (`participation_role`) | Função explícita exercida pela pessoa no evento (`Ouvinte`, `Palestrante`, `Apresentador`, `Organizador`, `Participante`, etc.). | **XML comprovado:** `@TIPO-PARTICIPACAO` e `@FORMA-PARTICIPACAO` (quando presentes; sem dedução). | **Papel extraído do documento:** `participation_role_raw` explícito no texto do certificado. | Distinguir sempre **dado XML comprovado** de **papel extraído do documento**; nunca presumir apresentação a partir de participação genérica. |

---

## 3. Contrato Mínimo Proposto (Sem Enum Fechado que Perca Dados)

Na seção de participação em eventos, XSD e DTD não trazem enumeração fechada para `@TIPO-PARTICIPACAO`, `@FORMA-PARTICIPACAO` ou `@NATUREZA` (a produção técnica possui enums próprios de natureza). Portanto, **não criar `Enum` definitivo obrigatório** que rejeite ou descarte valores desconhecidos. Adotar o par **(valor bruto preservado + valor normalizado opcional com `None` quando não mapeado)**.

### 3.1 Camada M1 implementada (`LattesRecord` e `parser/mappings.py`)

Campos opcionais implementados em `LattesRecord` (todos com default `None`, `OptionalCleanStr`, preenchidos em `PARTICIPACAO_EVENTO` ou quando o atributo existir):

| Campo proposto | Tipo | Origem XML | Regra de ausência / valor desconhecido |
| :--- | :--- | :--- | :--- |
| `nature_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@NATUREZA` (fallback nó pai) | Ausente ou só espaços → `None`. Preserva texto com remoção de espaços externos; atributo original na proveniência. |
| `participation_type_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@TIPO-PARTICIPACAO` (fallback nó pai) | Ausente ou só espaços → `None`. Remove espaços externos; preserva valor original na proveniência. |
| `participation_form_raw` | `OptionalCleanStr = None` | `DADOS-BASICOS-*/@FORMA-PARTICIPACAO` (fallback nó pai) | Ausente ou só espaços → `None`. Remove espaços externos; preserva valor original na proveniência. |
| `participation_role` | `OptionalCleanStr = None` | Mapeamento determinístico explícito a partir de `participation_type_raw` / `participation_form_raw` (tabela fechada apenas de sinônimos canônicos conhecidos) | Se ambos ausentes → `None`. Se valor bruto existir, mas **não** estiver na tabela explícita (ex.: `"Debatedor"`), `participation_role` permanece `None` (nunca inventa papel), mantendo o bruto em `participation_type_raw` / `participation_form_raw` e registrando aviso em `unverified_variants` para auditoria. |

> **Nota:** `provenance.raw_attributes` continua preservando integralmente todos os atributos XML originais.

### 3.2 Camada M3 (`ExtractedDocumentRecord` / Schema do Extrator)

Manter extração estritamente factual (`AD-002`) sem `Enum` fechado para papel no `response_schema`:

| Campo proposto | Tipo | Regra de extração e ausência |
| :--- | :--- | :--- |
| `event_name` | `str \| None = None` | Nome do evento/congresso quando distinto do título do trabalho/palestra; `None` se ausente ou só espaços. |
| `activity_title` | `str \| None = None` | Título específico do trabalho, palestra, mesa ou curso; `None` se o certificado citar apenas o evento. |
| `participation_role_raw` | `str \| None = None` | Papel explícito declarado no documento (ex.: `"Palestrante"`, `"Ouvinte"`, `"Apresentador"`, `"Organizador"`, `"Participante"`); `None` se não explícito. **Proibido** inferir ou usar `categoria_sugerida`/`confianca_extracao` na decisão. |

### 3.3 Camada M2 (`Matcher` — Regras Determinísticas e `FieldEvidence`)

1. **Normalização de papel (`normalize_role(raw)`):** função pura que remove acentos/pontuação, aplica `casefold()` e consulta uma tabela explícita pequena (ex.: `ouvinte` → `"OUVINTE"`; `palestrante`, `conferencista` → `"PALESTRANTE"`; `apresentador`, `apresentacao de trabalho` → `"APRESENTADOR"`; `organizador`, `comissao organizadora` → `"ORGANIZADOR"`; `participante`, `congressista` → `"PARTICIPANTE"`). Valor não mapeado retorna `None`, preservando `raw`.
2. **Separação `event_name` × `activity_title` × `participation_role`:**
   - Comparar `event_name` com `event_name` e `title` com `activity_title` **separadamente** (nunca concatenar).
   - Se o documento comprovar `participation_role` (`"PALESTRANTE"`) e `event_name` compatíveis, mas `doc.activity_title is None`: **não invalidar automaticamente** a atividade; comparar `event_name`, `participation_role`, `institution` e `ano`.
   - Se `xml.title` for não nulo e `doc.activity_title is None`: registrar `FieldEvidence` de `titulo` como `MISSING_DOCUMENT` (`detalhe não comprovado`), **nunca** como `CONFLICT` (`Divergente`).
3. **Proposta de `FieldEvidence` para `papel_participacao` (eventos e produção técnica; aplicabilidade/essencialidade final pendente por categoria):**
   - `xml_role_norm is None` e `doc_role_norm is None`:
     - Se ambos os brutos forem `None` → `MISSING_BOTH` (neutro para papel; decisão segue evento/título/instituição/ano).
     - Se algum bruto existir sem mapeamento → comparar igualdade normalizada dos brutos; se igual → `MATCH`, senão `INCONCLUSIVE_BORDERLINE` (papel bruto não mapeado).
   - Ambos mapeados e compatíveis (ex.: `PALESTRANTE` vs `PALESTRANTE`) → `MATCH`.
   - Papéis distintos não geram `CONFLICT` automaticamente: ouvinte, palestrante e organizador podem coexistir no mesmo evento. A definição de contradição factual e agregação por categoria permanece pendente em `m2-matcher/proposal.md` (`D-M2-07`).
   - Um lado explícito e outro `None`:
     - Papel só no XML (`doc_role_norm is None`) → `MISSING_DOCUMENT` (detalhe não comprovado, sem `CONFLICT`).
     - Papel só no documento (`xml_role_norm is None`, ex.: certificado diz `"Palestrante"` mas XML em `PARTICIPACAO-EM-EVENTOS-CONGRESSOS` omitiu `@TIPO-PARTICIPACAO`) → `MISSING_LATTES` (papel extraído do documento sem lastro explícito no XML; não gera `CONFLICT` nem `MATCH` fabricado; aguarda política da tabela de categoria).

---

## 4. Rollout Mínimo Proposto (Sem Abstração Excessiva)

1. **Gate M2/M3:** fechar agregação e essencialidade por categoria. Escopo técnico M1 já aprovado em AD-012 e implementado.
2. **Etapa M1 implementada:** quatro campos opcionais, tabela explícita, duas categorias técnicas e fixtures/testes. Ver `technical-production.md`; gate local de 130 testes e Ruff aprovado.
3. **Etapa M3 (Extração):** incluir `event_name` e `participation_role_raw` (`str | None`) no schema e prompt de extração multimodal, atualizando eventual heurística offline/baselines para não descartar prefixos de papel como ruído.
4. **Etapa M2 (Motor):** aplicar comparação separada de `event_name`, `title` e `papel_participacao` nas categorias de eventos/produção técnica conforme tabela ainda a aprovar, emitindo `FieldEvidence` por campo sem afetar `FORMACAO_ACADEMICA` e `FORMACAO_COMPLEMENTAR`.

---

## 5. Casos de Teste Relevantes Propostos (100% Sintéticos, Sem Implementação)

| ID | Camada | Cenário testado | Entrada sintética resumida | Resultado esperado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-ROLE-01** | M1 | Distinção `subtype` vs `nature_raw` vs `participation_type_raw` | `<PARTICIPACAO-EM-CONGRESSO>` com `NATUREZA="Congresso"`, `TIPO-PARTICIPACAO="Ouvinte"`, `TITULO=None`, `NOME-DO-EVENTO="Congresso X"` | `subtype="CONGRESSO"`, `nature_raw="Congresso"`, `participation_type_raw="Ouvinte"`, `participation_role="OUVINTE"`, `title=None`, `event_name="Congresso X"`. |
| **TC-ROLE-02** | M1 | Não confundir `NATUREZA="Congresso"` com `PALESTRANTE` | `NATUREZA="Congresso"` sem `@TIPO-PARTICIPACAO` nem `@FORMA-PARTICIPACAO` | `nature_raw="Congresso"`, `participation_type_raw=None`, `participation_role=None`. |
| **TC-ROLE-03** | M1 | Valor bruto desconhecido preservado sem perda | `TIPO-PARTICIPACAO="Debatedor de Mesa"` e `FORMA-PARTICIPACAO="Presencial"` | `participation_type_raw="Debatedor de Mesa"`, `participation_form_raw="Presencial"`, `participation_role=None` + registro em `unverified_variants`. |
| **TC-ROLE-04** | M1 | Ausência e espaços viram `None` | `TIPO-PARTICIPACAO="   "`, `FORMA-PARTICIPACAO=""`, `NATUREZA` ausente | Todos os campos brutos e `participation_role` iguais a `None`. |
| **TC-ROLE-05** | M2 | Palestrante com certificado sem título da palestra (`AD-010`) | XML: `event_name="Simpósio Y"`, `title=None`, `participation_role="PALESTRANTE"`; Doc: `event_name="Simpósio Y"`, `activity_title=None`, `participation_role_raw="Palestrante"` (+ titular/inst/ano compatíveis) | Não invalida por ausência de `title`; `papel_participacao=MATCH`, `titulo=MISSING_DOCUMENT/MISSING_BOTH`, `Validado` conforme tabela. |
| **TC-ROLE-06** | M2 | XML com `title` específico omitido no certificado (`AD-010`) | XML: `event_name="Congresso Z"`, `title="Palestra Alpha"`, `participation_role="PALESTRANTE"`; Doc: `event_name="Congresso Z"`, `activity_title=None`, `participation_role_raw="Palestrante"` | `titulo` marcado como `MISSING_DOCUMENT` (detalhe não comprovado), **nunca** `CONFLICT` (`Divergente`); veredito final segue `D-ROLE-03`. |
| **TC-ROLE-07** | M2 | Papéis distintos no mesmo evento | XML ouvinte; documento palestrante/organizador | Não presumir exclusividade dos papéis nem `CONFLICT` automático; essencialidade e agregação pendentes (`D-M2-07`). |
| **TC-ROLE-08** | M2 | Papel presente só no documento, ausente no XML | XML (`PARTICIPACAO_EVENTO`): `event_name="Congresso Z"`, `participation_role=None`; Doc: `event_name="Congresso Z"`, `participation_role_raw="Palestrante"` | `papel_participacao=MISSING_LATTES` (papel não comprovado no XML; não fabrica `CONFLICT` nem `MATCH`). |
| **TC-ROLE-09** | M1 | Produção técnica AD-012 | XML sintético com `ORGANIZACAO-DE-EVENTO` e `APRESENTACAO-DE-TRABALHO` | Extraídas em categorias próprias, sem colapsar em `PARTICIPACAO_EVENTO`; cobertura implementada em `test_parser_technical.py`. |

---

## 6. Decisões Pendentes Antes de Implementar

| ID | Pendência | Motivo / Evidência local | Opções a decidir |
| :--- | :--- | :--- | :--- |
| **D-ROLE-01** | Escopo técnico | Resolvido em AD-012 | Duas categorias adicionais implementadas no M1; distribuição experimental ainda pendente. |
| **D-ROLE-02** | Gramática | Referência estrutural resolvida em AD-011; olimpíada mapeada | Semântica de valores livres não é comprovada pelo XSD. Equivalência UI e requisito DTD do professor continuam pendentes. |
| **D-ROLE-03** | **Veredito final quando `title` do XML não consta no certificado (`AD-010`)** | `AD-010` proíbe converter ausência de `title` no comprovante em conflito factual, mas deixa aberta a agregação final por categoria (`STATE.md:50`). | **(A)** `Inconclusivo` (detalhe essencial/declarado não comprovado); **ou (B)** `Validado` quando `event_name`, `participation_role`, `institution` e `ano` forem compatíveis, mantendo ressalva em `field_evidences`. |
| **D-ROLE-04** | Evidência de papel | Proposta M2 já prevê `evento` e `papel_participacao` separados | Essencialidade e agregação por categoria ainda pendentes; não limitar a eventos de participação. |

## 7. Revisão humana aprovada (AD-013)

Todos os inconclusivos seguem à revisão; validados/divergentes podem ser revisados por solicitação. Expor documentos, candidatos, evidências e motivos. Permitir confirmar/corrigir associação, rejeitar candidatos e emitir parecer manual, inclusive manter inconclusivo. Registrar revisor, data e justificativa de alteração. Resultado automático original e métricas permanecem separados do parecer humano. Contrato completo em `m2-matcher/proposal.md`; implementação futura na API/interface. A revisão de possíveis associações tem base no comentário #38; a ampliação é decisão do usuário.
