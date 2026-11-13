# Catálogo de Fixtures Sintéticas XML do Marco M1 (P0-A)

> [!WARNING]
> **Base Preliminar e Ausência de DTD Oficial**
> A estrutura destas fixtures baseia-se exclusivamente no levantamento de protótipos legados (`references/legacy-drive/sharing/lattes_validator/parser_lattes.py`, `references/legacy-drive/sharing/src/parser/lattesXmlParser.ts`) e na proposta descrita em [xml-mapping.md](xml-mapping.md).
> **Estas fixtures não afirmam conformidade com a DTD oficial do CNPq nem autenticidade oficial**.
> Nenhuma DTD inventada foi criada ou vinculada via `DOCTYPE`. Todos os dados contidos nestes arquivos são **100% sintéticos e fictícios**, sem qualquer cópia ou derivação de currículos reais ou arquivos pessoais/Drive.

---

## 1. Visão Geral do Conjunto de Fixtures

As fixtures estão localizadas em `comprova-lattes-api/tests/fixtures/m1/` e acompanhadas do arquivo estruturado `manifest.json`. Todos os arquivos em disco estão codificados estritamente em **UTF-8**.

| Arquivo XML | Propósito Primário | Acadêmica | Complementar | Eventos | Total Registros |
| :--- | :--- | :---: | :---: | :---: | :---: |
| [`curriculo_completo_valido.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_completo_valido.xml) | Abrange as três seções com múltiplos registros válidos, acentuação e metadados completos de cabeçalho. | 2 | 2 | 1 | **5** |
| [`curriculo_carga_fracionaria.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_carga_fracionaria.xml) | Validação de carga horária fracionária (`1.5` e `40.75` horas) sem truncamento silencioso para inteiros. | 0 | 2 | 1 | **3** |
| [`curriculo_campos_ausentes.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_campos_ausentes.xml) | Validação de atributos ausentes e strings em branco que devem resultar estritamente em `None` (sem sentinelas). | 1 | 1 | 1 | **3** |
| [`curriculo_eventos_separacao.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_eventos_separacao.xml) | Separação estrita de `title` vs `event_name` e `institution` vs `city` e `location`, incluindo ausência de instituição. | 0 | 0 | 4 | **4** |
| [`curriculo_caracteres_acentuados.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_caracteres_acentuados.xml) | Estresse de caracteres acentuados da língua portuguesa (á, é, í, ó, ú, â, ê, ô, ã, õ, ç, etc.) em todas as seções. | 1 | 1 | 1 | **3** |

---

## 2. Detalhamento Arquivo por Arquivo

### 2.1 `curriculo_completo_valido.xml`
- **Arquivo:** [`curriculo_completo_valido.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_completo_valido.xml)
- **Codificação:** UTF-8
- **Objetivo:** Fornecer uma massa canônica com preenchimento íntegro de dados nas 3 seções do currículo para testes de parsing/robustez do parser implementado. Não representa conformidade estrutural; conjuntos conformes separados estão em `m1-conformant/` e `m1-technical/`.
- **Cabeçalho Esperado (`LattesCurriculum`):**
  - `lattes_id`: `"1111222233334444"`
  - `updated_at`: `"15032025"`
  - `full_name`: `"Helena de Souza Castanho"`
  - `citation_names`: `["CASTANHO, H. S.", "CASTANHO, Helena de Souza"]`
  - `summary`: `"Pesquisadora fictícia em Engenharia de Software e Sistemas Distribuídos."`
- **Registros Esperados (`LattesRecord`):**
  1. **Seção 1 (Acadêmica):** `category="FORMACAO_ACADEMICA"`, `subtype="GRADUACAO"`, `sequence="1"`, `institution="Universidade Federal Fluminense dos Rios"`, `institution_acronym="UFFR"`, `title="Engenharia de Computação"`, `start_year=2016`, `end_year=2020`, `workload_hours=Decimal(3600)`, `status="CONCLUIDO"`, `validation_code=None`. Código CAPES `98765432` preservado apenas na proveniência; não é autenticação documental.
  2. **Seção 1 (Acadêmica):** `category="FORMACAO_ACADEMICA"`, `subtype="MESTRADO"`, `sequence="2"`, `institution="Instituto Tecnológico do Cerrado"`, `institution_acronym="ITC"`, `title="Ciência da Computação"`, `start_year=2021`, `end_year=2023`, `workload_hours=Decimal(1200)`, `status="CONCLUIDO"`, `validation_code=None`.
  3. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="CURTA_DURACAO"`, `sequence="1"`, `institution="Fundação de Apoio à Tecnologia Educacional"`, `institution_acronym="FATE"`, `title="Mineração de Dados e Qualidade de Software"`, `start_year=2022`, `end_year=2022`, `workload_hours=Decimal(60)`, `status="CONCLUIDO"`.
  4. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="EXTENSAO_UNIVERSITARIA"`, `sequence="2"`, `institution="Universidade Federal Fluminense dos Rios"`, `institution_acronym="UFFR"`, `title="Desenvolvimento Seguro em Aplicações Web"`, `start_year=2023`, `end_year=2023`, `workload_hours=Decimal(120)`, `status="CONCLUIDO"`.
  5. **Seção 3 (Evento):** `category="PARTICIPACAO_EVENTO"`, `subtype="CONGRESSO"`, `sequence="1"`, `title="Avaliação de Precisão em Parsing Estruturado"`, `event_name="Congresso Brasileiro de Engenharia de Software"`, `institution="Sociedade Brasileira de Computação"`, `city="Curitiba"`, `location="Centro de Exposições ExpoParaná"`, `start_year=2024`, `end_year=2024`, `workload_hours=Decimal(30)`, `status=None`.

---

### 2.2 `curriculo_carga_fracionaria.xml`
- **Arquivo:** [`curriculo_carga_fracionaria.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_carga_fracionaria.xml)
- **Codificação:** UTF-8
- **Objetivo:** Exercitar expressamente o tratamento de valores decimais em `CARGA-HORARIA`, em particular o valor `1.5` horas e frações como `40.75`, prevenindo a falha histórica de truncamento com `int(float(s))`.
- **Cabeçalho Esperado (`LattesCurriculum`):**
  - `lattes_id`: `"2222333344445555"`
  - `updated_at`: `"10012025"`
  - `full_name`: `"Lucas Gabriel Paixão"`
  - `citation_names`: `["PAIXÃO, L. G.", "PAIXAO, Lucas Gabriel"]`
  - `summary`: `"Pesquisador fictício com foco em experimentos de cargas horárias fracionárias."`
- **Registros Esperados (`LattesRecord`):**
  1. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="CURTA_DURACAO"`, `sequence="1"`, `institution="Escola Técnica de Simulação Digital"`, `title="Workshop de Introdução à Sintaxe XML"`, `workload_hours=Decimal("1.5")`, `start_year=2024`, `end_year=2024`, `status="CONCLUIDO"`.
  2. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="EXTENSAO_UNIVERSITARIA"`, `sequence="2"`, `institution="Faculdade Integrada do Sertão"`, `title="Práticas Avançadas de Testes Automatizados"`, `workload_hours=Decimal("40.75")`, `start_year=2024`, `end_year=2024`, `status="CONCLUIDO"`.
  3. **Seção 3 (Evento):** `category="PARTICIPACAO_EVENTO"`, `subtype="SIMPOSIO"`, `sequence="1"`, `title="Painel Rápido sobre Representação Numérica de Horas"`, `event_name="Simpósio Regional de Informática Teórica"`, `institution="Associação de Pesquisa em Computação Aplicada"`, `city="Recife"`, `location="Auditório do Centro Tecnológico"`, `workload_hours=Decimal("1.5")`, `start_year=2024`, `end_year=2024`.

---

### 2.3 `curriculo_campos_ausentes.xml`
- **Arquivo:** [`curriculo_campos_ausentes.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_campos_ausentes.xml)
- **Codificação:** UTF-8
- **Objetivo:** Validar que atributos omitidos no XML ou contendo apenas espaços em branco (`"   "`) sejam normalizados deterministicamente para `None`, sem injeção de valores sentinelas legados como `"NAO_IDENTIFICADO"`, `"Instituição não informada"` ou `"Sem título"`.
- **Cabeçalho Esperado (`LattesCurriculum`):**
  - `lattes_id`: `None` (atributo não fornecido na raiz)
  - `updated_at`: `None` (atributo não fornecido na raiz)
  - `full_name`: `None` (preenchido como `"   "` no XML, normalizado para `None`)
  - `citation_names`: `[]` (preenchido como `""` no XML, lista vazia)
  - `summary`: `None` (nó `RESUMO-CV` ausente)
- **Registros Esperados (`LattesRecord`):**
  1. **Seção 1 (Acadêmica):** `category="FORMACAO_ACADEMICA"`, `subtype="GRADUACAO"`, `sequence=None`, `institution=None`, `institution_acronym=None`, `title="Bacharelado em Matemática Fictícia"`, `start_year=None`, `end_year=None`, `workload_hours=None`, `status=None`, `validation_code=None`.
  2. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="OUTROS"`, `sequence=None`, `institution="Escola Aberta Virtual"`, `title=None`, `start_year=None`, `end_year=None`, `workload_hours=None`, `status=None`.
  3. **Seção 3 (Evento):** `category="PARTICIPACAO_EVENTO"`, `subtype="ENCONTRO"`, `sequence=None`, `institution=None`, `title=None`, `event_name="Encontro Estadual de Inovação Aberta"`, `city="Manaus"`, `location=None`, `start_year=2023`, `end_year=2023`, `workload_hours=None`, `status=None`.

---

### 2.4 `curriculo_eventos_separacao.xml`
- **Arquivo:** [`curriculo_eventos_separacao.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_eventos_separacao.xml)
- **Codificação:** UTF-8
- **Objetivo:** Exercitar e auditar a separação categórica entre:
  - `title` (`DADOS-BASICOS-*/@TITULO` ou `@TITULO`): título do trabalho/apresentação.
  - `event_name` (`DETALHAMENTO-*/@NOME-DO-EVENTO` ou `@NOME-DO-EVENTO`): nome da conferência/simpósio.
  - `institution` (`DETALHAMENTO-*/@NOME-INSTITUICAO` ou `@NOME-INSTITUICAO`): entidade promotora.
  - `city` (`DETALHAMENTO-*/@CIDADE-DO-EVENTO`): cidade de realização.
  - `location` (`DETALHAMENTO-*/@LOCAL-DO-EVENTO`): local físico/auditório do evento.
- **Invariante Crítico:** Quando `institution` estiver ausente, `city` e `location` **nunca** devem ser copiadas como fallback para `institution`.
- **Cabeçalho Esperado (`LattesCurriculum`):**
  - `lattes_id`: `"3333444455556666"`
  - `updated_at`: `"20022025"`
  - `full_name`: `"Beatriz Vasconcelos Ribeiro"`
  - `citation_names`: `["RIBEIRO, B. V.", "VASCONCELOS, Beatriz"]`
  - `summary`: `"Pesquisadora fictícia focada em validação de granularidade de eventos e metadados institucionais."`
- **Registros Esperados (`LattesRecord`):**
  1. **Evento 1 (Completo):** `category="PARTICIPACAO_EVENTO"`, `subtype="CONGRESSO"`, `sequence="1"`, `title="Arquitetura Hexagonal em Aplicações Educacionais"`, `event_name="Congresso Internacional de Tecnologia da Educação"`, `institution="Fundação Educacional Metropolitana"`, `city="Belo Horizonte"`, `location="Palácio das Artes"`, `start_year=2024`, `end_year=2024`, `workload_hours=Decimal(24)`.
  2. **Evento 2 (Sem Instituição):** `category="PARTICIPACAO_EVENTO"`, `subtype="SIMPOSIO"`, `sequence="2"`, `title="Extração Multimodal de Certificados Acadêmicos"`, `event_name="Simpósio Brasileiro de Processamento de Linguagem"`, `institution=None` *(permanece estritamente None)*, `city="Belém"`, `location="Auditório Central do Campus Universitário"`, `start_year=2024`, `end_year=2024`, `workload_hours=Decimal(16)`.
  3. **Evento 3 (Sem Título do Trabalho):** `category="PARTICIPACAO_EVENTO"`, `subtype="OFICINA"`, `sequence="3"`, `title=None` *(não inventa sentinela)*, `event_name="Oficina de Escrita Científica para Graduandos"`, `institution="Sociedade Brasileira para o Progresso da Ciência"`, `city="São Paulo"`, `location="Espaço de Inovação Tecnológica"`, `start_year=2023`, `end_year=2023`, `workload_hours=Decimal(8)`.
  4. **Evento 4 (Atributos no Nó Pai - Fallback):** `category="PARTICIPACAO_EVENTO"`, `subtype="OUTRAS_PARTICIPACOES"`, `sequence="4"`, `title="Mesa Redonda sobre Curricularização da Extensão"`, `event_name="Jornada de Ensino Superior"`, `institution="Consórcio Universitário Integrado"`, `city="Salvador"`, `location="Teatro Universitário"`, `start_year=2025`, `end_year=2025`, `workload_hours=Decimal(4)`.

---

### 2.5 `curriculo_caracteres_acentuados.xml`
- **Arquivo:** [`curriculo_caracteres_acentuados.xml`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/curriculo_caracteres_acentuados.xml)
- **Codificação:** UTF-8
- **Objetivo:** Garantir a preservação fiel de diacríticos e acentuação da língua portuguesa (agudo, circunflexo, til, crase, trema, cedilha) e entidades XML escapadas (`&amp;`).
- **Cabeçalho Esperado (`LattesCurriculum`):**
  - `lattes_id`: `"4444555566667777"`
  - `updated_at`: `"05042025"`
  - `full_name`: `"Vitória Gonçalves da Conceição"`
  - `citation_names`: `["CONCEIÇÃO, V. G.", "GONÇALVES, Vitória"]`
  - `summary`: `"Pesquisadora fictícia dedicada ao estudo de acentuação gráfica: á é í ó ú, à è ì ò ù, â ê î ô û, ã õ, ç Ç, ü Ü, ñ Ñ."`
- **Registros Esperados (`LattesRecord`):**
  1. **Seção 1 (Acadêmica):** `category="FORMACAO_ACADEMICA"`, `subtype="ESPECIALIZACAO"`, `sequence="1"`, `institution="Centro Universitário Santo Agostinho de Marabá"`, `institution_acronym="UNISAM"`, `title="Gestão de Segurança da Informação & Governança"`, `start_year=2022`, `end_year=2023`, `workload_hours=Decimal(360)`, `status="CONCLUIDO"`.
  2. **Seção 2 (Complementar):** `category="FORMACAO_COMPLEMENTAR"`, `subtype="CURTA_DURACAO"`, `sequence="1"`, `institution="Fundação de Apoio à Capacitação Tecnológica de Goiás"`, `institution_acronym="FACT-GO"`, `title="Introdução à Análise Sintática & Detecção de Padrões"`, `start_year=2023`, `end_year=2023`, `workload_hours=Decimal(40)`, `status="CONCLUIDO"`.
  3. **Seção 3 (Evento):** `category="PARTICIPACAO_EVENTO"`, `subtype="SIMPOSIO"`, `sequence="1"`, `title="Contribuição à Resolução de Inconsistências em Certificados Eletrônicos"`, `event_name="Simpósio Maranhense de Computação e Inovação"`, `institution="Núcleo de Pesquisa em Engenharia de Software do Maranhão"`, `city="São Luís"`, `location="Espaço Cultural da Baixada Maranhense"`, `start_year=2024`, `end_year=2024`, `workload_hours=Decimal(20)`.

---

## 3. Manifesto Estruturado (`manifest.json`)

O arquivo [`manifest.json`](../../../../../../../Caleb/dev/ufra-projects/tcc/comprova-lattes-api/tests/fixtures/m1/manifest.json) consolida programaticamente os metadados e os valores esperados para cada arquivo. Ele permite que os futuros testes automatizados do parser façam iteração orientada a dados (data-driven testing), conferindo:
1. `file`: caminho relativo da fixture.
2. `features_tested`: etiquetas dos aspectos exercitados.
3. `expected_counts`: contagem esperada total e discriminada por categoria (`academic`, `complementary`, `event`).
4. `expected_header`: campos canônicos esperados no modelo `LattesCurriculum`.
5. `expected_records`: lista ordenada com cada `LattesRecord` esperado e seus atributos validados.

---

## 4. Como Construir Bytes em ISO-8859-1 em Testes Futuros (Sem Editar Testes Atuais)

Todos os arquivos de fixtures foram gravados como arquivos de texto em codificação **UTF-8**. O Currículo Lattes histórico frequentemente exporta arquivos em `ISO-8859-1` (Latin-1).

Para testar o suporte a `ISO-8859-1` no futuro módulo `comprova_lattes/parser/` sem necessidade de criar réplicas binárias em disco ou alterar os testes existentes, as suites de teste do pytest podem converter os arquivos de texto existentes em bytes `ISO-8859-1` em tempo de execução:

### 4.1 Padrão de Fixture Pytest com Conversão Dinâmica

```python
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "m1"


@pytest.fixture
def lattes_iso88591_bytes() -> bytes:
    """Carrega uma fixture UTF-8 e converte para bytes ISO-8859-1 com prólogo XML ajustado."""
    xml_path = FIXTURES_DIR / "curriculo_caracteres_acentuados.xml"
    content = xml_path.read_text(encoding="utf-8")

    # Substitui a declaração de encoding no cabeçalho XML
    content_iso = content.replace(
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<?xml version="1.0" encoding="ISO-8859-1"?>',
    )

    # Codifica para bytes utilizando Latin-1
    return content_iso.encode("iso-8859-1")
```

### 4.2 Verificação de Consumo com `defusedxml`

Ao consumir bytes codificados em `ISO-8859-1`:
- Se o prólogo contiver `encoding="ISO-8859-1"`, o parser XML `defusedxml.ElementTree.fromstring(raw_bytes)` resolve a codificação a partir do próprio prólogo XML.
- Se o parser receber um objeto `io.BytesIO(raw_bytes)`, a detecção automática do leitor XML trata a codificação declarada.
- Se a função de parsing do sistema aceitar `bytes`, o módulo deve decodificar ou delegar para o `defusedxml` sem assumir cegamente UTF-8 via `.decode("utf-8")`.

---

## 5. Validações Sintáticas Realizadas

Todas as fixtures criadas foram submetidas às seguintes validações automáticas no ambiente virtual do projeto (`comprova-lattes-api/.venv`):
1. **Validação XML Segura:** Cada arquivo XML foi inspecionado com `defusedxml.ElementTree.parse()`, garantindo sintaxe XML 100% válida e integridade de fechamento de tags.
2. **Validação do Manifesto JSON:** O arquivo `manifest.json` foi validado com `json.loads()`, certificando formatação estrita e ausência de campos corrompidos.
3. **Isolamento Completo:** Nenhum schema Pydantic foi modificado; nenhum módulo do parser foi executado ou alterado.
