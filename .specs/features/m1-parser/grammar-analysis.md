# Análise Comparativa de Gramáticas XML Lattes (DTD comunitária × XSD oficial CNPq)

**Status:** análise histórica concluída; M1 permanece aberto pela exigência DTD e compatibilidade UI não comprovada. Artefatos de terceiros disponíveis somente localmente, excluídos da publicação por licença pendente.
**Contexto histórico:** análise anterior à ampliação AD-012. Os achados sobre gramáticas/fixtures originais permanecem válidos; afirmações de código não mapeado e recomendações de criação de fixtures abaixo descrevem aquele momento. Hoje ensino fundamental/olimpíada e produção técnica estão mapeados, e há conjuntos conformes/técnicos separados. Estado atual em [technical-production.md](technical-production.md) e [spec.md](spec.md).

**Data:** 2026-11-13 · **Proveniência, URLs, revisão, hashes e licença:** [references/xml-grammars/README.md](../../../references/xml-grammars/README.md)
**Escopo:** somente leitura sobre parser, testes, specs e fixtures (hashes SHA-256 das 5 fixtures e do `manifest.json` idênticos antes e depois). Nenhum XML pessoal, Drive ou conteúdo de `Downloads` foi acessado.

> [!IMPORTANT]
> **O que as duas fontes são (e não são).**
> - `LMPLCurriculo.DTD` é uma revisão **comunitária**, não oficial, de uma DTD histórica do CNPq; o próprio README upstream a descreve como "trabalho em andamento". Último commit: `a295d38…` (2010-10-18). Sem licença declarada.
> - O XSD é **oficial do CNPq**, mas rotulado na página oficial como "Definições do XML do **Extrator Lattes**" (acesso institucional via webservice), atualizado em 12/09/2022. **Não foi observada** nenhuma declaração de que o XML exportado pela interface web do Lattes (o que o usuário final baixa) siga esse XSD. Portanto, não afirmo equivalência entre as duas gramáticas, nem conformidade da exportação de UI com qualquer uma delas.

---

## 1. Estrutura geral

| Aspecto | DTD comunitária | XSD oficial (Extrator) |
| :--- | :--- | :--- |
| Formato / bytes | Texto ISO-8859-1, 2 448 linhas | Arquivo XML único (**não é zip**), ISO-8859-1, 6 616 linhas |
| Elementos declarados | 284 `ELEMENT`; 242 `ATTLIST` | 324 elementos globais (sem `xs:import/include/redefine`) |
| Raiz | `CURRICULO-VITAE` (único elemento não referenciado) | `CURRICULO-VITAE` (idem) |
| Filhos da raiz | `DADOS-GERAIS, PRODUCAO-BIBLIOGRAFICA?, PRODUCAO-TECNICA?, OUTRA-PRODUCAO?, DADOS-COMPLEMENTARES?` | Mesma sequência, com as mesmas cardinalidades |
| Atributo obrigatório na raiz | `SISTEMA-ORIGEM-XML` | `SISTEMA-ORIGEM-XML` |
| Obrigatórios em `DADOS-GERAIS` | `NACIONALIDADE, NOME-COMPLETO, NOME-EM-CITACOES-BIBLIOGRAFICAS, PERMISSAO-DE-DIVULGACAO, SEXO` | Os mesmos, **exceto `SEXO`** (opcional no XSD). XSD-only: `ORCID-ID, PAIS-DE-NACIONALIDADE, RACA-OU-COR, SIGLA-PAIS-NACIONALIDADE` |
| Modelos de conteúdo | Sequências **ordenadas** | Sequências (`xs:sequence`) **ordenadas** |
| Tipagem de atributos | `CDATA`; enums em `STATUS-DO-CURSO` etc. | Atributos sem tipo (`anySimpleType`), exceto enums (`STATUS-DO-CURSO` etc.) — **anos e `CARGA-HORARIA` não são validados numericamente por nenhuma das duas** |
| Defaults | DTD declara defaults de atributo (ex.: `MEIO-DE-DIVULGACAO="NAO_INFORMADO"`, `FLAG-RELEVANCIA="NAO"`) e `#FIXED` de formato de data | XSD tem `default` em alguns atributos; sem `fixed` nos elementos inspecionados (raiz, `DADOS-GERAIS` e as três seções) |

### Inclusões externas e dependências

- **DTD:** nenhuma `<!ENTITY`, `<!NOTATION`, seção condicional, `SYSTEM`/`PUBLIC` de entidade. Única dependência é o próprio arquivo (declara `xmlns:lattes` como `CDATA #IMPLIED` na raiz; não referencia o namespace).
- **XSD:** nenhum `include/import/redefine`; sem `DOCTYPE` ou `ENTITY`; sem `targetNamespace` (elementos sem namespace, `elementFormDefault="qualified"`).
- **Bloqueios por dependência faltante:** nenhum.
- **Fixtures:** nenhuma das 5 contém `DOCTYPE` nem declaração de entidade.

---

## 2. As três seções (caminho, tags, atributos)

Caminhos confirmados **idênticos nas duas gramáticas**:

| Seção | Caminho no XML | Observação |
| :--- | :--- | :--- |
| 1 — Formação acadêmica | `/CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO` | pai único: `DADOS-GERAIS` |
| 2 — Formação complementar | `/CURRICULO-VITAE/DADOS-COMPLEMENTARES/FORMACAO-COMPLEMENTAR` | pai único: `DADOS-COMPLEMENTARES`. **`DADOS-GERAIS/FORMACAO-COMPLEMENTAR` não existe em nenhuma das duas** |
| 3 — Eventos | `/CURRICULO-VITAE/DADOS-COMPLEMENTARES/PARTICIPACAO-EM-EVENTOS-CONGRESSOS` | pai único: `DADOS-COMPLEMENTARES`. **`DADOS-GERAIS/PARTICIPACAO-EM-EVENTOS-CONGRESSOS` não existe em nenhuma das duas** |

As 5 fixtures colocam as seções nos contêineres corretos (verificado por XPath nas fixtures).

### 2.1 Seção 1 — tags de registro (idênticas nas duas gramáticas)

`GRADUACAO, ESPECIALIZACAO, MESTRADO, DOUTORADO, POS-DOUTORADO, LIVRE-DOCENCIA, CURSO-TECNICO-PROFISSIONALIZANTE, MESTRADO-PROFISSIONALIZANTE, ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU, ENSINO-MEDIO-SEGUNDO-GRAU, RESIDENCIA-MEDICA, APERFEICOAMENTO` (todas `*`, nesta ordem).

- `ENSINO-MEDIO` (mapeado em [mappings.py](../../../comprova-lattes-api/src/comprova_lattes/parser/mappings.py)) **não existe em nenhuma das duas**; a tag oficial/comunitária é `ENSINO-MEDIO-SEGUNDO-GRAU`.
- `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU` existe nas duas e **não está** em `mappings.py`.
- Atributos do registro: DTD ⊆ XSD no recorte da seção. XSD-only: em `GRADUACAO` (`TIPO-GRADUACAO`, `*-INSTITUICAO-GRAD`, `*-OUTRA-GRAD`, `NOME-ORIENTADOR-GRAD`, e um atributo literalmente chamado `FORMACAO-ACADEMICA-TITULACAO`), `MESTRADO` (`TIPO-MESTRADO`, `*-DOUT`, `NOME-DO-CO-ORIENTADOR`), `DOUTORADO` (co-tutela/sanduíche), `MESTRADO-PROFISSIONALIZANTE`, `CURSO-TECNICO-PROFISSIONALIZANTE`, `RESIDENCIA-MEDICA`. DTD-only no recorte: nenhum.
- Presentes nas duas: `SEQUENCIA-FORMACAO, NOME-INSTITUICAO, NOME-CURSO(-INGLES), ANO-DE-INICIO, ANO-DE-CONCLUSAO, STATUS-DO-CURSO (EM_ANDAMENTO|CONCLUIDO|INCOMPLETO), CODIGO-CURSO-CAPES, TITULO-DA-DISSERTACAO-TESE` (mestrado/doutorado), `ANO-DE-OBTENCAO-DO-TITULO` (mestrado/doutorado/pós-doc/MBA), `TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO` (graduação).
- **`CARGA-HORARIA` só existe em `ESPECIALIZACAO` e `APERFEICOAMENTO`** (ambas gramáticas); **não existe** em `GRADUACAO`, `MESTRADO`, `DOUTORADO`, `POS-DOUTORADO`, etc.
- **`SIGLA-INSTITUICAO` não existe em nenhum registro das três seções** (só em `INFORMACAO-ADICIONAL-INSTITUICAO`, fora do escopo).

### 2.2 Seção 2 — tags de registro (idênticas; ordem obrigatória)

`FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA*, MBA*, FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO*, OUTROS*`.

- **Ordem importa** nas duas gramáticas: extensão → MBA → curta duração → outros.
- Não existem nas gramáticas: `FORMACAO-COMPLEMENTAR-CURTA-DURACAO` e `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR` (variantes legadas ainda aceitas em `mappings.py`).
- Atributos idênticos entre DTD e XSD; `CARGA-HORARIA` presente nas quatro tags; sem `SIGLA-INSTITUICAO`.

### 2.3 Seção 3 — eventos

| Tag filha de `PARTICIPACAO-EM-EVENTOS-CONGRESSOS` | DTD | XSD |
| :--- | :---: | :---: |
| `PARTICIPACAO-EM-CONGRESSO`, `-SEMINARIO`, `-SIMPOSIO`, `-OFICINA`, `-ENCONTRO`, `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` | Sim | Sim |
| `PARTICIPACAO-EM-FEIRA`, `PARTICIPACAO-EM-EXPOSICAO`, `PARTICIPACAO-EM-OLIMPIADA` | **Não** | **Sim** |
| `OUTRAS-PARTICIPACOES-EM-EVENTOS` (legado Python) | Não | Não |

- Estrutura de cada evento: `PARTICIPACAO-EM-X` (atributo único `SEQUENCIA-PRODUCAO`) com filhos `DADOS-BASICOS-DA-PARTICIPACAO-EM-X?`, `DETALHAMENTO-DA-PARTICIPACAO-EM-X?`, `PARTICIPANTE-DE-EVENTOS-CONGRESSOS*`, `PALAVRAS-CHAVE?`, `AREAS-DO-CONHECIMENTO?`, `SETORES-DE-ATIVIDADE?`, `INFORMACOES-ADICIONAIS?`.
- `DADOS-BASICOS-*`: `NATUREZA, TITULO, TITULO-INGLES, ANO, PAIS, IDIOMA, MEIO-DE-DIVULGACAO, HOME-PAGE-DO-TRABALHO, FLAG-RELEVANCIA, TIPO-PARTICIPACAO, FORMA-PARTICIPACAO, DOI` (+ XSD: `FLAG-DIVULGACAO-CIENTIFICA`; enum `MEIO-DE-DIVULGACAO` do XSD acrescenta `WEB`).
- `DETALHAMENTO-*`: `NOME-DO-EVENTO(-INGLES), CODIGO-INSTITUICAO, NOME-INSTITUICAO, LOCAL-DO-EVENTO, CIDADE-DO-EVENTO`.
- `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` tem **apenas** `SEQUENCIA-PRODUCAO` como atributo; os dados ficam nos filhos `DADOS-BASICOS-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` e `DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS`. O "fallback de atributos no nó pai" do xml-mapping não corresponde a nenhuma gramática.
- **Nenhum atributo `CARGA-HORARIA` em qualquer elemento de evento; nenhum atributo de status.** `NOME-INSTITUICAO` está só em `DETALHAMENTO-*`, nunca em `DADOS-BASICOS-*`.
- `SEQUENCIA-FORMACAO` não existe em eventos (só `SEQUENCIA-PRODUCAO`).

### 2.4 Resumo das divergências DTD × XSD no recorte das três seções

| Divergência | Direção |
| :--- | :--- |
| 3 tipos de evento (`FEIRA`, `EXPOSICAO`, `OLIMPIADA`) com `DADOS-BASICOS`/`DETALHAMENTO` | só XSD |
| `FLAG-DIVULGACAO-CIENTIFICA` e valor `WEB` em `MEIO-DE-DIVULGACAO` | só XSD |
| Atributos extras de graduação/mestrado/doutorado/outros (lista em 2.1) | só XSD |
| `SEXO` obrigatório em `DADOS-GERAIS` | só DTD (obrigatório); opcional no XSD |
| `ORCID-ID`, `RACA-OU-COR`, `LICENCAS` etc. em `DADOS-GERAIS` | só XSD |
| Tags, caminhos, ordem e atributos centrais das seções 1–2 e dos eventos comuns | iguais |

Leitura: no recorte, o XSD de 2022 contém construções ausentes da DTD comunitária; **não se observou nenhuma construção presente só na DTD** nas três seções. Isso é compatível com a DTD estar defasada, mas não prova defasagem em geral nem em outras áreas do documento.

---

## 3. Validação offline das 5 fixtures

**Método.** Contêiner descartável `python:3.12-slim` + `lxml 6.1.3` (libxml2 2.14.6); imagem construída com rede apenas para `pip install lxml`, **execução com `--network none --read-only`**, gramáticas e fixtures montadas `:ro`. Parser XML `resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False, attribute_defaults=False`. As fixtures não foram alteradas (SHA-256 igual antes/depois). `lxml` **não foi instalado no host**. Validação DTD usou a DTD local confiável via `etree.DTD(file)` — nenhum DOCTYPE de entrada foi processado. Logs: [analysis-output/](../../../references/xml-grammars/analysis-output/).

**Controle positivo.** Documento sintético mínimo em memória (cabeçalho com atributos obrigatórios + as três seções com tags/atributos presentes nas gramáticas) **valida nas duas gramáticas**, confirmando que as ferramentas e os arquivos funcionam e que os erros abaixo vêm das fixtures.

**Resultado: as 5 fixtures são inválidas contra a DTD comunitária e contra o XSD** (esperado, pois o catálogo de fixtures já declarava não afirmar conformidade).

| Categoria de erro | `completo_valido` | `carga_fracionaria` | `campos_ausentes` | `eventos_separacao` | `caracteres_acentuados` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| A. Atributos obrigatórios de cabeçalho ausentes (XSD: `SISTEMA-ORIGEM-XML`, `NACIONALIDADE`, `PERMISSAO-DE-DIVULGACAO`; DTD: + `SEXO`) | ✗ | ✗ | ✗ | ✗ | ✗ |
| B. `SIGLA-INSTITUICAO` não declarado | ✗ (3 XSD / 4 DTD) | ✗ | — | — | ✗ (2) |
| C. `CARGA-HORARIA` não declarado (graduação, mestrado, `DETALHAMENTO-*`, `OUTRAS-…`) | ✗ (3) | ✗ (1) | — | ✗ (4) | ✗ (1) |
| D. Ordem de filhos de `FORMACAO-COMPLEMENTAR` (curta duração antes de extensão) | ✗ | ✗ | — | — | — |
| E. Tag inexistente `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR` | — | — | ✗ | — | — |
| F. `OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS` com dados em atributos do nó pai | — | — | — | ✗ (6 atributos; `CARGA-HORARIA` do mesmo nó contado em C) | — |

Contagem total de mensagens (XSD / DTD): `completo_valido` 10 / 12; `carga_fracionaria` 6 / 8; `campos_ausentes` 4 / 7; `eventos_separacao` 13 / 14; `caracteres_acentuados` 6 / 7. **Todas as mensagens se encaixam nas categorias A–F; nenhuma ficou sem classificação.** Detalhe: [fixture_validation.json](../../../references/xml-grammars/analysis-output/fixture_validation.json).

**Ressalvas da validação.**
- Contagens do XSD podem estar subestimadas: após erro de modelo de conteúdo (categoria D), o libxml2 não valida os atributos do elemento fora de ordem (ex.: `carga_fracionaria` mostra 1 ocorrência de B no XSD e 2 na DTD).
- Como os atributos de ano e `CARGA-HORARIA` não têm tipo em nenhuma gramática, **a validação não cobre formato numérico** (aspas, fração, negativos).
- As mensagens de erro de A são consequência de fixtures mínimas (sem cabeçalho de identificação completo); isso não indica erro na estrutura das seções.

### 3.1 Erro de fixture × gramática possivelmente desatualizada

| Categoria | Interpretação apoiada pelos dados |
| :--- | :--- |
| A | Fixture sintética incompleta (omissão de atributos obrigatórios). Não é defasagem de gramática. |
| B, C, E, F | As **duas** gramáticas, de origens e datas diferentes (2010 e 2022), rejeitam igualmente. Portanto, as fixtures (e o `xml-mapping.md`/legado em que se basearam) usam atributos/tags que **não constam de nenhuma das gramáticas**. Não há evidência de que a DTD defasada seja a causa. Se o XML real da UI contém esses atributos, as gramáticas é que seriam insuficientes — **isso não foi observado** (sem XML real analisado). |
| D | Violação de ordem obrigatória nas duas; erro da fixture em relação às gramáticas. |

---

## 4. Compatibilidade com o mapeamento/parser atuais (somente leitura)

Comparação de [mappings.py](../../../comprova-lattes-api/src/comprova_lattes/parser/mappings.py) e [xml-mapping.md](xml-mapping.md) com as gramáticas:

| Item mapeado | DTD | XSD | Nota |
| :--- | :---: | :---: | :--- |
| `ENSINO-MEDIO` | — | — | Variante legada sem respaldo |
| `FORMACAO-COMPLEMENTAR-CURTA-DURACAO` | — | — | Variante legada sem respaldo |
| `OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR` | — | — | Variante legada sem respaldo |
| `OUTRAS-PARTICIPACOES-EM-EVENTOS` | — | — | Variante legada sem respaldo |
| `PARTICIPACAO-EM-FEIRA`, `-EXPOSICAO` | — | ✓ | Só XSD |
| `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, `PARTICIPACAO-EM-OLIMPIADA` | ✓ / — | ✓ / ✓ | Existem; **não mapeados** em `mappings.py` (olimpíada só no XSD) |
| Fallback `DADOS-GERAIS/FORMACAO-COMPLEMENTAR` e `DADOS-GERAIS/PARTICIPACAO-EM-EVENTOS-CONGRESSOS` | — | — | Caminho inexistente nas duas |
| `@SIGLA-INSTITUICAO` (→ `institution_acronym`) | — | — | Atributo inexistente nos registros das três seções |
| `@CARGA-HORARIA` em graduação/mestrado/doutorado e eventos | — | — | Inexistente; **sem carga horária de evento em nenhuma gramática** |
| `@SEQUENCIA-FORMACAO` em eventos | — | — | Eventos usam só `SEQUENCIA-PRODUCAO` |
| Atributos do nó pai em `OUTRAS-PARTICIPACOES-…` | — | — | Dados ficam em `DADOS-BASICOS-DE-OUTRAS-…` / `DETALHAMENTO-DE-OUTRAS-…`; não verifiquei se o parser atual lê esses filhos (verificar antes de decidir) |
| Status de evento | — | — | Nenhum atributo de status; `status=None` (como na fixture) é consistente com ambas |

> Observação: esta tabela não é uma auditoria do código do parser, apenas dos nomes listados nas tabelas de mapeamento e nas fixtures.

---

## 5. Recomendação de aproveitamento (proposta; nada foi implementado)

Para aproveitar ambas **sem exigir ambas em runtime**:

1. **Inventário de tags/atributos (referência):** usar o **XSD oficial como fonte primária** para fechar T-M1-02 (mais recente, origem CNPq) e a **DTD comunitária como verificação cruzada**. Registrar no `xml-mapping.md` as divergências da seção 2.4. Custo baixo; só documentação.
2. **Teste de conformidade (apenas teste):** um teste opcional (marker próprio, fora do núcleo obrigatório) que valide fixtures *conformantes* contra o XSD e, secundariamente, contra a DTD via `lxml` em ambiente isolado, sem rede e sem DOCTYPE de entrada. O núcleo e `pytest` padrão seguem sem `lxml`, PostgreSQL, Redis ou Gemini. Benefício: regressão estrutural objetiva; custo: dependência de teste (`lxml`) e manutenção de fixtures conformes.
3. **Runtime:** manter só `defusedxml` e o parser atual. Qualquer validação de gramática em runtime (XSD ou DTD) exige decisão explícita; se adotada, rodar **depois** do parsing seguro, com schema local fixo e `lxml` com entidades/rede desligadas. A DTD não autoriza desativar `defusedxml`; o Pydantic não valida a estrutura XML completa.
4. **Fixtures:** não alterar as existentes (o manifesto e os 92 testes dependem delas). Propor um segundo conjunto "conformante à gramática" (cabeçalho completo, ordem correta, sem atributos inexistentes) mantendo as atuais como testes de comportamento/robustez.

---

## 6. Decisões pendentes (para o Codex/usuário)

| # | Decisão | Recomendação | Impacto |
| :--- | :--- | :--- | :--- |
| D1 | **Licença/redistribuição** dos dois artefatos: DTD sem licença declarada; XSD CNPq sem termo de uso observado. | Manter em `references/` apenas localmente (hoje não versionado, `??` no git); citar URL+hash na monografia; não publicar sem esclarecer (ex.: contato com o autor/CNPq). | Define se `references/xml-grammars/` pode ir ao repositório público |
| D2 | **Qual XML é o alvo real**: exportação da UI do Lattes ou saída do Lattes Extrator? O XSD é do Extrator. | Validar **um** XML real de exportação da UI contra o XSD, mediante decisão explícita de uso de documento real (não feito aqui). Até lá, tratar conformidade como não comprovada. | Define se o XSD serve como oráculo do parser |
| D3 | **Fixtures × gramática** (categorias B–F). | Criar conjunto conformante adicional (ver 5.4) em vez de editar as atuais. | Evita quebrar manifesto/testes; deixa claro o que é robustez e o que é conformidade |
| D4 | **Alinhar `mappings.py`/`xml-mapping.md`**: remover variantes sem respaldo (`ENSINO-MEDIO`, `…CURTA-DURACAO`, `OUTROS-TIPOS…`, `OUTRAS-PARTICIPACOES-EM-EVENTOS`, fallbacks de `DADOS-GERAIS`), mapear `ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU`, tratar `FEIRA/EXPOSICAO/OLIMPIADA` e ler `DADOS-BASICOS-DE-OUTRAS-…`/`DETALHAMENTO-DE-OUTRAS-…`. | Decidir se variantes desconhecidas viram diagnóstico em vez de aceitação silenciosa. | Altera comportamento do parser (fora do escopo desta tarefa) |
| D5 | **Carga horária de evento e de graduação/mestrado/doutorado inexiste nas gramáticas**; `SIGLA-INSTITUICAO` idem. | Confirmar com M2 que `workload_hours` de eventos/graduação virá nulo do Lattes; reavaliar `institution_acronym`. | Afeta o motor de cruzamento (M2) e os campos do schema |
| D6 | **Adotar `lxml` (teste e/ou runtime)**. | Somente teste, em ambiente isolado (item 5.2). | Nova dependência; não instalada |
| D7 | Tratar **ordem** de elementos e **defaults** da DTD: o parser atual não depende da ordem; defaults não devem ser aplicados à proveniência `raw_attributes`. | Nunca habilitar atribuição de defaults de DTD no parsing de produção. | Preserva evidência por campo |

---

## 7. Evidências e arquivos

- Fontes e hashes: [references/xml-grammars/README.md](../../../references/xml-grammars/README.md)
- Gramáticas originais: [LMPLCurriculo.DTD](../../../references/xml-grammars/community-dtd/LMPLCurriculo.DTD), [XSD CNPq](../../../references/xml-grammars/cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd)
- Saídas brutas: [validation.txt](../../../references/xml-grammars/analysis-output/validation.txt), [closure.txt](../../../references/xml-grammars/analysis-output/closure.txt), [checks.txt](../../../references/xml-grammars/analysis-output/checks.txt)
- Ferramentas: [tools/](../../../references/xml-grammars/tools/)
- Hashes das fixtures (inalteradas): `completo_valido` 586144a6…, `carga_fracionaria` 7133d840…, `campos_ausentes` dd24216d…, `eventos_separacao` 74aed18c…, `caracteres_acentuados` 4226e8e7…, `manifest.json` cbbc4b36….

Não foram executados `pytest`/`ruff` (nenhum código do projeto mudou). Nenhum commit/push; nenhum arquivo fora de `references/xml-grammars/` e deste relatório foi escrito (além de arquivos temporários no diretório scratch da conversa).
