# Proposta de Especificação M2 (P0-C) — Motor Determinístico de Associação e Classificação

> Decisões aprovadas consolidadas em `STATE.md` (`AD-004` a `AD-012`): escopo ampliado pelo usuário para **5 categorias** (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`, sem artigos/anais, `AD-012`), mantendo **3 classes de resultado** (`Validado`, `Divergente`, `Inconclusivo`); 1 documento por atividade (`AD-004`); sem comprovante → `Inconclusivo / SEM_COMPROVANTE` (`AD-005`); documento órfão fora da matriz $3 \times 3$ como `DOCUMENTO_NAO_ASSOCIADO` (`AD-006`); associação ambígua → `Inconclusivo / ASSOCIACAO_AMBIGUA` com revisão humana separada e métricas automáticas calculadas antes da revisão (`AD-007`); igualdade exata de horas em `Decimal` (`40 == 40.0` e `40` vs `45` como conflito por campo no par associado, com agregação final ainda pendente, `AD-009`); separação de nome do evento, título e papel explícito (`AD-010`, sem tratar certificado de ouvinte como contradição automática de apresentação/organização, pois papéis podem coexistir). Essencialidade e agregação final por categoria, título omitido, coexistência de papéis e limiares quantitativos permanecem propostas sem aprovação.

> [!WARNING]
> **Documento de proposta — NÃO IMPLEMENTADO.**
> Esta especificação descreve contratos, regras já aprovadas (`AD-004` a `AD-012`) e decisões ainda em aberto para o Marco **M2 (P0-C)**. O módulo `comprova-lattes-api/src/comprova_lattes/matcher/` contém atualmente apenas um pacote inicial vazio (`__init__.py`), o Marco **M1** segue em andamento (extensão `AD-012` em entrega separada; referência estrutural XSD/DTD definida em `AD-011`, com requisito DTD do professor ainda pendente) e nenhuma regra do M2 foi implementada ou validada em código.

**Última atualização:** 2026-11-13
**Base documental consultada:** `PROJECT.md`, `ROADMAP.md`, `STATE.md`, `PROFESSOR-REQUIREMENTS.md`, `.specs/features/m1-parser/spec.md`, `.specs/features/m2-matcher/event-role-contract.md` e `docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md` (especialmente comentários #16, #36, #37, #38, #52, #59, #60, #61, #62, #63, #64, #65 e #67).

---

## 1. Objetivo e Escopo da Proposta

Definir formalmente o **motor determinístico de associação e classificação** (`matcher/`) responsável por cruzar registros extraídos do XML do Currículo Lattes (`LattesCurriculum` / `LattesRecord` nas **5 categorias-alvo**: `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`) com registros estruturados extraídos de documentos comprobatórios (`ExtractedDocumentRecord`), atribuindo a cada registro curricular uma das **três classes finais** (`Validado`, `Divergente` ou `Inconclusivo`) com trilha de auditoria por atributo.

Esta proposta cobre:
- Invariantes e decisões já consolidadas (`AD-002`, `AD-004` a `AD-012`) que restringem o desenho do M2;
- Separação arquitetural entre **Etapa 1 (Associação)** e **Etapa 2 (Classificação)**, fundamentada em Fellegi e Sunter (1969);
- Contratos conceituais de entrada, configuração/limiares simbólicos, saída (incluindo preservação do resultado automático frente à revisão humana de `AD-007`) e evidência por campo;
- Distinção entre equivalência de siglas, normalização léxica e similaridade aproximada (com guarda de string vazia);
- Distinção entre variação legítima, omissão/detalhe não comprovado e mutação factual;
- Proposta de tabela de decisão por campo (`titular`, `titulo`, `evento`, `papel`, `instituicao`, `ano`, `carga`), destacando o que já foi aprovado (`AD-009`, `AD-010`) e o que permanece pendente de aprovação (essencialidade e agregação final por categoria, título omitido e coexistência de papéis);
- Especificação dos baselines comparativos (`Exact Match` e `Normalizado`);
- Pendências remanescentes para decisão do usuário;
- Critérios verificáveis e matriz de casos de teste propostos (sem implementação de código).

---

## 2. Decisões e Invariantes Já Aprovados (Restrições Fixas)

As regras abaixo já estão aprovadas no projeto (`STATE.md`, `PROFESSOR-REQUIREMENTS.md` e `.specs/features/m1-parser/spec.md`) e **não devem ser reabertas** na implementação do M2:

1. **LLM apenas extrai; motor determinístico decide (`AD-002`, Comentário #52):** o módulo `matcher/` nunca importa ou chama `google-genai`. Campos oriundos do extrator como `confianca_extracao` e `categoria_sugerida` são estritamente ignorados na associação e na classificação.
2. **Um documento por atividade no MVP (`AD-004`):** cada `ExtractedDocumentRecord` representa uma única atividade comprobatória. Extração/desmembramento de múltiplas atividades em um mesmo documento está fora do escopo do MVP, e o motor não deve selecionar silenciosamente uma atividade dentre várias caso um documento contenha múltiplas.
3. **Registro sem comprovante → `Inconclusivo / SEM_COMPROVANTE` (`AD-005`):** registro curricular do XML sem documento comprobatório associado recebe obrigatoriamente `Inconclusivo` com código de motivo `SEM_COMPROVANTE`. Ausência de prova não equivale a conflito factual (`Divergente`).
4. **Documento sem registro correspondente fora da matriz $3 \times 3$ (`AD-006`):** documento sem registro associado no XML é reportado separadamente como `DOCUMENTO_NAO_ASSOCIADO`. Não entra como quarta classe nem é forçado em `Validado`, `Divergente` ou `Inconclusivo` na matriz $3 \times 3$ dos registros; a associação é avaliada separadamente (denominadores e protocolo final ainda pendentes).
5. **Associação ambígua e revisão humana (`AD-007`):** candidatos ambíguos na Etapa 1 resultam em `Inconclusivo / ASSOCIACAO_AMBIGUA`, com solicitação de revisão humana e apresentação dos candidatos e evidências por campo. A pessoa revisora pode confirmar associação, rejeitar candidatos ou manter inconclusivo, mas o sistema **preserva o resultado automático original** e registra a decisão humana e o motivo separadamente. As métricas experimentais do método automático são calculadas **antes** da intervenção humana. O critério quantitativo de ambiguidade e a mecânica de disputa entre registros ainda dependem de decisão e calibração piloto.
6. **Avaliação sem meta arbitrária de Macro-F1 (`AD-008`, Comentário #66):** não há meta fixa `Macro-F1 >= 0,85`; reporta-se o desempenho observado com intervalo de confiança (cujo método, nível e unidade de reamostragem permanecem em proposta no protocolo experimental).
7. **Comparação exata de carga horária em `Decimal` (`AD-009`, M1-spec §2.1 e §3):** horas são comparadas em `Decimal` finito após normalização numérica (`40` e `40.0` são iguais). Diferença factual como `40` versus `45` (ou `40` versus `400`) gera conflito de carga horária (`CONFLICT`) por campo no par associado, registrando a magnitude da diferença na evidência. Valor ausente (`None`) ou descartado pelo parser (`INVALID_WORKLOAD_HOURS`) não é conflito numérico comprovado. A agregação/classificação final do registro segue a tabela de decisão por categoria, ainda pendente de fechamento.
8. **Evento, título do trabalho/palestra e papel de participação separados (`AD-010`):** manter nome do evento (`event_name`), título do trabalho/palestra (`title` / `activity_title`) e papel de participação (`participation_role` / `participation_role_raw`) como informações distintas, extraídas somente quando explícitas, sem concatenar campos nem presumir apresentação a partir de participação genérica. A ausência do título específico no comprovante não invalida automaticamente palestra/apresentação; se o registro declarar título específico não informado no documento, sinalizar como detalhe não comprovado (`MISSING_DOCUMENT`), sem convertê-lo em conflito factual (`CONFLICT`). Certificado de ouvinte não deve ser tratado como contradição automática de apresentação/organização, pois papéis em um mesmo evento podem coexistir (regra de agregação documentada como pendência).
9. **Referência estrutural XML (`AD-011`):** o XSD oficial do Extrator CNPq é a referência estrutural principal e a DTD comunitária serve como comparação histórica (com fixtures conformes separadas dos casos de robustez), sem presumir equivalência integral com a exportação da interface web (UI) e sem encerrar por decisão interna o requisito de validação DTD do orientador (#25). Na gramática XML, `CARGA-HORARIA` não existe em eventos, produção técnica (`APRESENTACAO-DE-TRABALHO`, `ORGANIZACAO-DE-EVENTO`) nem em cursos de graduação/mestrado/doutorado; ausência estrutural chega como `None` e nunca deve ser tratada como divergência automática.
10. **Cinco categorias no escopo do MVP, mantendo três classes (`AD-012`):** além das três seções iniciais (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`), entram no escopo `APRESENTACAO_TRABALHO` (`APRESENTACAO-DE-TRABALHO`) e `ORGANIZACAO_EVENTO` (`ORGANIZACAO-DE-EVENTO`) em `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA` (entrega separada do M1), mantendo as 3 classes de decisão (`Validado`, `Divergente`, `Inconclusivo`). Artigos e trabalhos publicados em anais (`TRABALHO-EM-EVENTOS`) permanecem fora de escopo.
11. **Ausência explícita como `None` e independência operacional (M1-spec §3, `ARCHITECTURE.md`):** campos ausentes ou em branco são `None` (nunca sentinelas inventadas), e o M2 executa offline via funções puras e CLI/`pytest` sem PostgreSQL, Redis, Celery ou API externa.
12. **Calibração e congelamento de limiares (`PROJECT.md`, Comentários #45 e #62):** **nenhum limiar numérico final é inventado ou fixado nesta proposta**. Todos os limiares aparecem como parâmetros simbólicos a serem calibrados exclusivamente no conjunto piloto e congelados antes da execução do conjunto final.

---

## 3. Separação Formal: Associação vs. Classificação (Comentários #38, #61 e #65)

Atendendo ao Comentário #61 e às decisões `AD-004` a `AD-007` e `AD-012`, define-se explicitamente a **unidade de análise** e a separação em duas etapas sequenciais:

- **Entrada da execução:** $1$ `LattesCurriculum` contendo $M$ registros auditáveis (`LattesRecord` nas **5 categorias-alvo**: `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`) e $N$ documentos extraídos (`ExtractedDocumentRecord`), podendo $M \neq N$.
- **Unidade de classificação na matriz $3 \times 3$:** o **registro curricular** (`LattesRecord`). Todo registro do XML entra na avaliação final com exatamente um veredito dentre as **3 classes** (`Validado`, `Divergente` ou `Inconclusivo`).
- **Fundamentação em Fellegi e Sunter (1969) (Comentário #38):** o modelo adota dois limiares delimitando três regiões de decisão — vínculo confirmado (`Validado`), zona intermediária/incerta para revisão (`Inconclusivo`) e conflito/não confirmação — com a adaptação explícita ao domínio de conferência documental de que **`Divergente` pressupõe associação prévia bem-sucedida** com conflito factual comprovado.

```text
[M registros XML (5 categorias)] + [N documentos extraídos (1 doc/atividade, AD-004)]
        │
        ▼
Etapa 1 — Associação Determinística (Pareamento registro ↔ documento)
  ├── Escore de afinidade ≥ τ_assoc (sem ambiguidade) ──► Par (registro, documento) ──► Etapa 2
  ├── Candidatos ambíguos / empate (AD-007) ────────────► Registro: Inconclusivo (ASSOCIACAO_AMBIGUA)
  │                                                       + revisão humana separada (métricas antes da revisão)
  ├── Registro sem candidato ≥ τ_assoc (AD-005) ────────► Registro: Inconclusivo (SEM_COMPROVANTE)
  └── Documento sem registro ≥ τ_assoc (AD-006) ────────► Fora da matriz 3×3: DOCUMENTO_NAO_ASSOCIADO
        │
        ▼
Etapa 2 — Classificação por Regras e Tabela de Decisão (sobre cada par associado)
  ├── Conflito factual em atributo decisivo ────────────► Divergente
  ├── Atributos essenciais da categoria atendidos ──────► Validado
  └── Ausência / detalhe não comprovado / zona cinzenta ► Inconclusivo
      (agregação final por categoria ainda pendente de aprovação)
```

**Separação das métricas experimentais (Comentário #65, `AD-006`, `AD-007`, `AD-008`):**
- A **Etapa 1 (Associação)** é avaliada separadamente da matriz $3 \times 3$ dos registros, contemplando os pares `(record_id, document_id)` e o reporte de `DOCUMENTO_NAO_ASSOCIADO` (`AD-006`; denominadores e protocolo final da associação ainda pendentes de especificação).
- A **Etapa 2 / Fluxo Completo (Classificação)** é avaliada por **matriz de confusão $3 \times 3$**, **Acurácia, Precisão, Revocação, F1 por classe e Macro-F1 observado com intervalo de confiança** (`AD-008`) sobre os registros curriculares, calculados **antes** de qualquer intervenção humana nos casos `ASSOCIACAO_AMBIGUA` (`AD-007`). O método/nível de IC via bootstrap e a parametrização do teste de McNemar permanecem propostas pendentes de aprovação no protocolo experimental.

---

## 4. Contratos Propostos (Estruturas Conceituais)

> Os contratos abaixo especificam interfaces e tipos propostos em nível de especificação, alinhados a `LattesCurriculum` e `LattesRecord` e ao contrato mínimo de papéis em `.specs/features/m2-matcher/event-role-contract.md`. Nenhum arquivo de código do M2 foi criado.

### 4.1 Contrato de Entrada

1. **`LattesCurriculum` (origem M1):**
   - `full_name: str | None` e `citation_names: list[str]` (referência canônica do titular do currículo);
   - `records: list[LattesRecord]` contendo `record_id`, `category` (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO`, `ORGANIZACAO_EVENTO` — `AD-012`), `subtype`, `provenance`, `holder_name`, `institution`, `institution_acronym`, `title`, `event_name`, `city`, `location`, `start_year`, `end_year`, `workload_hours` (`Decimal | None`), `status`, além dos campos de natureza e papel (`nature_raw`, `participation_type_raw`, `participation_form_raw`, `participation_role` — `AD-010`).
   - `parse_diagnostics: list[LattesParseDiagnostic]` (opcional na entrada do M2 para propagar diagnóstico `INVALID_WORKLOAD_HOURS` para a trilha de auditoria quando `workload_hours` foi descartado como `None` no parser).
2. **`ExtractedDocumentRecord` (interface desacoplada com futuro M3 e baselines):**
   - `document_id: str` (obrigatório, identificador único do documento no lote);
   - `extraction_status: ExtractionStatus` (`OK` | `UNREADABLE` | `INVALID_JSON` | `API_ERROR`);
   - `holder_name: str | None` (nome do titular extraído do documento);
   - `activity_title: str | None` (título específico do curso, formação, palestra ou trabalho apresentado, quando explícito — `AD-010`);
   - `event_name: str | None` (nome oficial do evento/congresso quando distinto do título do trabalho/palestra — `AD-010`);
   - `participation_role_raw: str | None` (papel explícito de participação no documento, ex.: `"Palestrante"`, `"Ouvinte"`, `"Apresentador"`, `"Organizador"`, `"Participante"`, quando explícito — `AD-010`);
   - `issuer_institution: str | None` (nome da instituição emissora/promotora);
   - `issuer_acronym: str | None` (sigla explícita se presente no documento);
   - `start_year: int | None` / `end_year: int | None` (ou `activity_year: int | None`, a alinhar com o schema de M3);
   - `workload_hours: Decimal | None` (finito e não negativo; valores negativos eventuais de OCR/baseline devem ser descartados antes ou convertidos em `None` com diagnóstico próprio);
   - `raw_metadata: dict[str, Any]` (opcional/informativo; **proibido** na lógica de decisão caso contenha `confianca_extracao` ou `categoria_sugerida`).

### 4.2 Contrato de Configuração e Limiares (`MatcherConfig` — Simbólico)

- `mode`: `PROPOSED` | `BASELINE_EXACT` | `BASELINE_NORMALIZED`
- `text_metric`: `LEVENSHTEIN_NORM` | `JARO_WINKLER` | `TOKEN_HYBRID`
- `thresholds` (placeholders simbólicos sem valores finais hardcoded):
  - $\tau_{\text{assoc}}$: escore mínimo para aceitar associação `(registro, documento)`;
  - $\Delta_{\text{empate}}$: margem para detecção de ambiguidade entre candidatos (`ASSOCIACAO_AMBIGUA`, `AD-007`);
  - $\tau_{\text{titular}}$: limiar de similaridade para aceitação do nome do titular;
  - $\tau_{\text{titulo\_alto}}$ e $\tau_{\text{titulo\_baixo}}$: limiares superior (aceitação) e inferior (conflito) para título específico e nome do evento (comparados separadamente conforme `AD-010`);
  - $\tau_{\text{inst\_alto}}$ e $\tau_{\text{inst\_baixo}}$: limiares superior e inferior para instituição (após checagem de siglas);
  - *Nota sobre carga horária (`AD-009`):* não há limiar de tolerância $\delta_{\text{carga}}$, pois `AD-009` aprovou comparação exata em `Decimal` (`40 == 40.0`; `40` vs `45` gera conflito no campo `carga` em par associado com registro da magnitude);
  - `calibration_metadata`: `{ "calibrated_on": "pilot_30", "frozen": true | false }`.
- `acronym_table`: mapeamento explícito e versionado entre siglas e formas por extenso normalizadas (ex.: `ufra` ↔ `universidade federal rural da amazonia`, `usp` ↔ `universidade de sao paulo`).

### 4.3 Contrato de Saída (`MatchingResult`)

- `mode`: modo executado (`PROPOSED`, `BASELINE_EXACT` ou `BASELINE_NORMALIZED`);
- `record_verdicts: list[RecordVerdict]`: exatamente 1 entrada por `LattesRecord` do XML, contendo:
  - `record_index: int` e `record_id: str | None`;
  - `category: LattesCategory` (uma das 5 categorias de `AD-012`);
  - `matched_document_id: str | None`;
  - `association_score: float | None` (escore determinístico da Etapa 1);
  - `status: MatchStatus` (`VALIDADO` | `DIVERGENTE` | `INCONCLUSIVO` — veredito automático original preservado para cálculo das métricas antes da revisão humana conforme `AD-007` e `AD-013`);
  - `reason_code: MatchReasonCode` (código principal da decisão automática);
  - `ambiguity_candidates: list[AssociationCandidate]` (preenchido quando `ASSOCIACAO_AMBIGUA`, expondo candidatos e evidências por campo para revisão humana — `AD-007`);
  - `human_review: HumanReviewRecord | None` (separado do resultado automático: confirmar/corrigir associação, rejeitar candidatos ou emitir parecer manual, inclusive manter inconclusivo; registrar revisor, data, parecer e justificativa obrigatória para alteração — `AD-007`, `AD-013`);
  - `field_evidences: list[FieldEvidence]` (cobrindo os atributos pertinentes à categoria: `titular`, `titulo`, `evento`, `papel_participacao`, `instituicao`, `ano`, `carga` — granularidade final pendente de aprovação);
  - `diagnostics: list[str]` (ex.: propagação de `INVALID_WORKLOAD_HOURS` do M1 quando aplicável);
- `orphan_documents: list[OrphanDocumentReport]`: documentos que não atingiram $\tau_{\text{assoc}}$ com nenhum registro (`document_id`, `reason_code="DOCUMENTO_NAO_ASSOCIADO"`, `best_candidate_record_id`, `best_association_score` — fora da matriz $3 \times 3$ conforme `AD-006`);
- `association_pairs: list[AssociationPair]`: pares efetivamente formados na Etapa 1 para avaliação auditável e separada da associação (`AD-006`).

**Revisão aprovada (AD-013):** todos os resultados automáticos `INCONCLUSIVO` são encaminhados à revisão; `VALIDADO` e `DIVERGENTE` podem ser revisados por solicitação. `status`, `reason_code`, `matched_document_id` e evidências originais permanecem preservados; associação e parecer humanos são separados. O encaminhamento não bloqueia nem substitui a medição automática. Fluxo ainda não implementado; API/interface em etapa posterior.

### 4.4 Contrato de Evidência por Campo (`FieldEvidence`)

Cada registro classificado após Etapa 1 (e com placeholders explícitos quando `SEM_COMPROVANTE` ou `ASSOCIACAO_AMBIGUA`) emite registros de evidência por atributo contendo:
- `field_name`: `titular` | `titulo` | `evento` | `papel_participacao` | `instituicao` | `ano` | `carga`;
- `lattes_raw`: valor bruto vindo do M1 (`str | int | Decimal | None`);
- `document_raw`: valor bruto vindo do documento (`str | int | Decimal | None`);
- `lattes_normalized`: representação normalizada usada na comparação (`None` se ausente);
- `document_normalized`: representação normalizada usada na comparação (`None` se ausente);
- `rule_applied`: identificador da regra determinística acionada (ex.: `EXACT_MATCH`, `NORMALIZED_MATCH`, `ACRONYM_EQUIVALENCE`, `SIMILARITY_PASS`, `SIMILARITY_BORDERLINE`, `SIMILARITY_CONFLICT`, `YEAR_CONFLICT`, `WORKLOAD_DECIMAL_MATCH`, `WORKLOAD_DECIMAL_CONFLICT`, `MISSING_DOCUMENT_VALUE`, `UNPROVEN_SPECIFIC_TITLE`, `ROLE_COEXISTENCE_PENDING`, `PARSER_DISCARDED_NEGATIVE_WORKLOAD`);
- `similarity_score`: escore numérico (`float | None`) quando houver comparação textual;
- `numeric_difference`: diferença absoluta/relativa em `Decimal | None` quando houver conflito numérico em `carga` (`AD-009`);
- `outcome`: `MATCH` | `CONFLICT` | `INCONCLUSIVE_BORDERLINE` | `MISSING_LATTES` | `MISSING_DOCUMENT` | `MISSING_BOTH` | `NOT_APPLICABLE`;
- `justification_pt`: explicação legível em português para auditoria e interface.

---

## 5. Normalização, Siglas, Similaridade e Guarda de String Vazia

### 5.1 Pipeline de Normalização $N(s)$

Aplicado antes da comparação textual (no `BASELINE_NORMALIZED` e no `PROPOSED`, nunca no `BASELINE_EXACT`):
1. Converter `None` → `None` (não transformar ausência em `""`).
2. Aplicar decomposição Unicode `NFKD` e remover marcas combinantes (acentos/diacríticos).
3. Converter para minúsculas com `casefold()`.
4. Substituir pontuações e separadores (`-`, `/`, `.`, `,`, `:`, `;`, `(`, `)`) por espaço único.
5. Colapsar múltiplos espaços e aplicar `strip()`.
6. Se após os passos 2–5 a string resultar em `""`, tratá-la como ausência (`None`) na camada de atributos, impedindo correspondência vazia.

### 5.2 Equivalência de Siglas vs. Similaridade (Comentário #36)

Conforme orientação explícita do professor, **Levenshtein não resolve siglas**: comparar `"UFRA"` com `"Universidade Federal Rural da Amazônia"` gera distância de edição alta e similaridade próxima de zero. Portanto, o motor aplica **duas camadas distintas em ordem fixa**:

1. **Camada 1 — Tabela Explícita de Equivalência de Siglas (Regra):**
   - Verifica se $N(\text{instituição}_{\text{XML}})$ (ou $N(\text{sigla}_{\text{XML}})$) e $N(\text{instituição}_{\text{doc}})$ (ou $N(\text{sigla}_{\text{doc}})$) mapeiam para a mesma entidade canônica na tabela explícita de siglas (ex.: `ufra` ↔ `universidade federal rural da amazonia`; `usp` ↔ `universidade de sao paulo`).
   - Adicionalmente (a confirmar na decisão `D-M2-05`), pode-se verificar compatibilidade estrutural quando uma forma for explicitamente sigla contida no texto composto do outro lado (ex.: `"UFRA - Campus Paragominas"`).
   - Se houver equivalência explícita de sigla: `rule_applied = "ACRONYM_EQUIVALENCE"`, `outcome = MATCH`, sem penalização por distância de edição.
2. **Camada 2 — Métrica de Similaridade Aproximada (Somente no `PROPOSED`):**
   - Aplicada somente quando não houve igualdade normalizada nem equivalência por sigla, para lidar com erros de digitação, pequenas omissões ou ruído de extração.
   - Métrica base P0: **Levenshtein normalizado** (Navarro, 2001 — Comentário #59):
     $$S_{\text{lev}}(s_1, s_2) = 1 - \frac{d_{\text{lev}}(N(s_1), N(s_2))}{\max(|N(s_1)|, |N(s_2)|)}$$
   - **Suporte comparativo (Comentário #37):** o comparador de texto será abstraído por interface para permitir avaliar também **Jaro-Winkler** (especialmente para nomes próprios/instituições) e **métrica baseada em tokens** (ordem de palavras e preposições, conforme Cohen, Ravikumar e Fienberg, 2003).

### 5.3 Guarda Explícita para Strings Vazias (Comentário #60)

- **Na função matemática de similaridade:** quando $\max(|N(s_1)|, |N(s_2)|) = 0$ (ambas as strings normalizadas são vazias), a função **não executa divisão por zero**. O retorno explícito da função pura para dois vazios é `0.0` (ou erro controlado caso se proíba entrada vazia), **nunca** `1.0` automático que pudesse induzir falso positivo em pontuação agregada.
- **Na camada de regra por campo:** valores `None` ou que se tornam vazios após $N(s)$ **nunca chegam** ao cálculo de similaridade; são interceptados antes e classificados como `MISSING_LATTES`, `MISSING_DOCUMENT` ou `MISSING_BOTH` conforme Seção 6.

---

## 6. Variação Legítima vs. Mutação Factual e Tabela de Decisão

### 6.1 Distinção Conceitual (Comentários #63 e #64, `AD-009`, `AD-010`)

| Tipo de fenômeno | Exemplos sintéticos (fictícios) | Resultado no campo / Classe esperada | Justificativa |
| :--- | :--- | :--- | :--- |
| **Variação legítima** | `"Maria Silva Oliveira"` vs `"MARIA SILVA OLIVEIRA"` (sem acento/caixa); `"UFRA"` vs `"Universidade Federal Rural da Amazônia"`; `"40"` vs `"40.0"` em `Decimal` (`AD-009`); preposição/pontuação no título | Campo: `MATCH` → Classe: `Validado` (quando atributos essenciais da categoria forem atendidos) | Mesma entidade e mesmos fatos declarados, apenas com variação ortográfica, formatação numérica equivalente ou sigla conhecida. |
| **Omissão / Detalhe não comprovado / Incerteza** | Campo ausente (`None`) no documento; título específico declarado no XML e ausente no comprovante de evento/palestra (`AD-010` → `MISSING_DOCUMENT`); certificado de `Ouvinte` frente a registro de apresentação/organização (papéis podem coexistir no evento, sem contradição automática); `workload_hours=None` após descarte de negativo no parser (`INVALID_WORKLOAD_HOURS`); documento `UNREADABLE`; registro sem comprovante (`SEM_COMPROVANTE`, `AD-005`); associação ambígua (`ASSOCIACAO_AMBIGUA`, `AD-007`); similaridade na zona intermediária $[\tau_{\text{baixo}}, \tau_{\text{alto}})$ | Campo: `MISSING_*` ou `INCONCLUSIVE_BORDERLINE` → Classe: `Inconclusivo` (ou conforme agregação final por categoria, ainda pendente para detalhes opcionais/título omitido) | Falta evidência suficiente para confirmar ou refutar o fato declarado, sem conflito factual comprovado. |
| **Mutação factual (após associação)** | Troca de titular (`"Maria Silva"` vs `"Carlos Souza"`); instituição distinta sem equivalência (`"UFRA"` vs `"UFPA"`); ano divergente (`2023` vs `2021`); divergência de carga horária em par associado (`40h` vs `45h` ou `40h` vs `400h`, `AD-009`); título de outra atividade incompatível dentro do mesmo par | Campo: `CONFLICT` → Classe: `Divergente` (conforme tabela de agregação por categoria, ainda em definição) | Há associação prévia ao registro, mas o comprovante contradiz objetivamente um fato declarado. |

> [!NOTE]
> Sobre carga horária (`AD-009` e Comentário #63, ex.: `40h -> 45h` vs `40h -> 400h`): a decisão aprovada exige **igualdade exata em `Decimal`** após normalização numérica (`40 == 40.0`). Em par associado, tanto `40` vs `45` quanto `40` vs `400` produzem `CONFLICT` no campo `carga`, registrando-se a magnitude da diferença na `FieldEvidence`. Valor ausente ou descartado como inválido (`None`) não é conflito numérico comprovado, e a agregação final para o veredito do registro ainda depende da tabela de decisão por categoria.

### 6.2 Tabela de Decisão por Campo (Método Proposto — Essencialidade e Agregação por Categoria Pendentes)

> **Importante:** As regras de comparação por campo para `carga` (`AD-009`) e para separação entre `titulo`, `evento` e `papel_participacao` (`AD-010`) já estão aprovadas. Entretanto, a **essencialidade por categoria** (nas 5 categorias: `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`), o **veredito final quando o título específico é omitido no comprovante**, e o **tratamento de papéis e sua coexistência** permanecem **propostas sem aprovação**.

| Campo | Origem XML (`M1`) vs. Documento (`M3`) | Essencialidade por Categoria (*Proposta pendente de aprovação*) | Condição `MATCH` (Variação Legítima) | Condição `INCONCLUSIVE` / Não Comprovado (`MISSING_*` / Zona Cinzenta) | Condição `CONFLICT` (Mutação Factual) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`titular`** | XML: `record.holder_name` se preenchido; senão `curriculum.full_name` (e `curriculum.citation_names` como apoio)<br>Doc: `holder_name` | *Proposta:* Essencial nas 5 categorias | Igualdade normalizada **ou** similaridade $\ge \tau_{\text{titular}}$ (ou regra explícita de abreviação legítima se aprovada em `D-M2-05`) | `document.holder_name is None` (sem conflito nos demais) **ou** `lattes` ausente **ou** similaridade na faixa cinzenta $[\tau_{\text{titular\_baixo}}, \tau_{\text{titular}})$ | Titular distinto com similaridade $< \tau_{\text{titular\_baixo}}$ (ex.: troca de pessoa) |
| **`titulo`** | XML: `title` (separado de `event_name`, `AD-010`)<br>Doc: `activity_title` (extraído só quando explícito, `AD-010`) | *Proposta:* Essencial em `FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR` e `APRESENTACAO_TRABALHO`; condicional em `PARTICIPACAO_EVENTO` e `ORGANIZACAO_EVENTO` (agregação final de título omitido pendente) | Igualdade normalizada **ou** similaridade $\ge \tau_{\text{titulo\_alto}}$ | Valor ausente (`None`) em um dos lados — incluindo título específico declarado no XML e omitido no comprovante (`MISSING_DOCUMENT`, sinalizado como detalhe não comprovado sem conflito factual conforme `AD-010`) — **ou** similaridade em $[\tau_{\text{titulo\_baixo}}, \tau_{\text{titulo\_alto}})$ | Ambos presentes e título factualmente incompatível ($< \tau_{\text{titulo\_baixo}}$) após associação confirmada |
| **`evento`** | XML: `event_name` (separado de `title`, `AD-010`)<br>Doc: `event_name` (extraído só quando explícito, `AD-010`) | *Proposta:* Aplicável em `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`; `NOT_APPLICABLE` nas formações | Igualdade normalizada **ou** similaridade $\ge \tau_{\text{titulo\_alto}}$ | Ausente (`None`) em um dos lados (`MISSING_DOCUMENT` / `MISSING_LATTES`) **ou** similaridade na zona intermediária $[\tau_{\text{titulo\_baixo}}, \tau_{\text{titulo\_alto}})$ | Ambos presentes e nome do evento factualmente incompatível ($< \tau_{\text{titulo\_baixo}}$) |
| **`papel_participacao`** | XML: `participation_role` / `participation_type_raw` / `participation_form_raw` (e contexto de `APRESENTACAO_TRABALHO` / `ORGANIZACAO_EVENTO`, sem inferir papel a partir de `NATUREZA="CONFERENCIA"`, `AD-010`, `AD-012`)<br>Doc: `participation_role_raw` | *Proposta:* Aplicável em `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO` (regras detalhadas de papel e coexistência pendentes) | Papéis explícitos mapeados e compatíveis | Papel ausente em um ou ambos os lados (`MISSING_*`), bruto não mapeado, **ou certificado de `Ouvinte`/`Participante` frente a registro de apresentação/organização** (papéis podem coexistir no mesmo evento; não tratar como contradição automática — pendência documentada) | Contradição factual estrita apenas se definida e aprovada na tabela de categoria (atualmente pendente; certificado de ouvinte **não** gera `CONFLICT` automático) |
| **`instituicao`** | XML: `institution` e `institution_acronym` (estritamente separado de `city` e `location`)<br>Doc: `issuer_institution` e `issuer_acronym` | *Proposta:* Essencial em `FORMACAO_ACADEMICA` e `FORMACAO_COMPLEMENTAR`; contextual nas categorias de evento/produção técnica quando declarada | Igualdade normalizada **ou** equivalência explícita na `acronym_table` **ou** similaridade $\ge \tau_{\text{inst\_alto}}$ | Ausência no documento (`None`) sem contradição **ou** ausência no XML (`NOT_APPLICABLE` / `MISSING_LATTES`) **ou** escore em $[\tau_{\text{inst\_baixo}}, \tau_{\text{inst\_alto}})$ | Siglas/instituições conhecidas e distintas **ou** similaridade $< \tau_{\text{inst\_baixo}}$ sem equivalência de sigla |
| **`ano`** | XML: `start_year`, `end_year`, `status`<br>Doc: `start_year`, `end_year` / `activity_year` | *Proposta:* Essencial nas 5 categorias quando declarado no XML | `CONCLUIDO` / `PARTICIPOU` / ano único: igualdade exata com `end_year` (ou `start_year` quando `end_year is None`). `EM_ANDAMENTO`: ano do documento compatível com intervalo $[start\_year, \infty)$ | Ano ausente no documento (`None`) ou ausente no XML (`None`) | Ano(s) do documento incompatível(is) com o ano/intervalo declarado no XML |
| **`carga`** | XML: `workload_hours` (`Decimal \| None`)<br>Doc: `workload_hours` (`Decimal \| None`) | *Proposta:* Essencial em `FORMACAO_COMPLEMENTAR` (quando declarada); opcional/`NOT_APPLICABLE` quando `None` no XML (inexistente na gramática XML de eventos, produção técnica e graduação/pós `stricto sensu`, `AD-011`) | **Aprovado (`AD-009`):** Igualdade exata em `Decimal` após normalização numérica (`40 == 40.0`) | Ausência não prova conflito (AD-009). Campo inexistente na gramática da categoria/subtipo é `NOT_APPLICABLE`, sem rebaixamento automático; campo aplicável ausente ou descartado gera `MISSING_*`/diagnóstico, com agregação por categoria ainda pendente | **Aprovado (`AD-009`):** Ambos presentes em `Decimal` em par associado e diferentes ($\|h_{\text{xml}} - h_{\text{doc}}\| > 0$, ex.: `40` vs `45` ou `40` vs `400`), registrando a magnitude da diferença |

### 6.3 Regra de Agregação do Veredito Final do Registro (Proposta Pendente de Fechamento por Categoria)

As regras 1 e 2 abaixo já estão aprovadas (`AD-005`, `AD-007`); a agregação final dos campos na Etapa 2 (itens 4 a 6, incluindo essencialidade por categoria nas 5 categorias, título omitido e coexistência de papéis) **permanece em definição e aguarda aprovação**:

1. **Sem documento associado na Etapa 1 (`AD-005` — Aprovado):** `Inconclusivo` (`SEM_COMPROVANTE`).
2. **Candidatos ambíguos na Etapa 1 (`AD-007` — Aprovado):** `Inconclusivo` (`ASSOCIACAO_AMBIGUA`), encaminhado para revisão humana com preservação do resultado automático original (métricas calculadas antes da revisão).
3. **Falha de legibilidade/extração do documento pareado (`extraction_status != OK`):** `Inconclusivo` (`DOCUMENTO_ILEGIVEL` ou `FALHA_EXTRACAO`).
4. **Conflito factual em atributo aplicável (`outcome == CONFLICT`, proposta de agregação pendente por categoria):** `Divergente` (o `reason_code` registra o campo conflitante e `field_evidences` preserva todos os conflitos e magnitudes, como em `AD-009`).
5. **Ausência ou detalhe não comprovado em atributo exigido pela categoria (`MISSING_DOCUMENT`, `INCONCLUSIVE_BORDERLINE`, título omitido conforme `AD-010`, coexistência de papéis ou descarte de carga inválida — proposta de agregação pendente por categoria):** `Inconclusivo` (`EVIDENCIA_INSUFICIENTE` / `ATRIBUTO_ESSENCIAL_AUSENTE` / `ZONA_INCERTA_FELLEGI_SUNTER`).
6. **Atributos essenciais da categoria atendidos (`outcome == MATCH`, proposta de agregação pendente por categoria):** `Validado` (`VALIDADO_CORRESPONDENCIA_COMPLETA`).

---

## 7. Baselines Comparativos (Comentário #16)

Todos os baselines operam sobre os **mesmos contratos de entrada e saída** (`LattesCurriculum`, `ExtractedDocumentRecord[]` → `MatchingResult`) para garantir comparação pareada justa (Experimento 2 e teste de McNemar, cujos detalhes estatísticos permanecem em proposta no protocolo experimental):

| Modo | Normalização $N(s)$ | Tabela de Siglas | Similaridade Aproximada | Carga `Decimal` Exata (`AD-009`) | Finalidade Experimental |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`BASELINE_EXACT`** | Não (apenas igualdade literal exata após `strip()` mínimo ou sem transformação de caixa/acento) | Não | Não | Igualdade literal/exata | Piso mínimo (*Exact Match* puro). |
| **`BASELINE_NORMALIZED`** | Sim (caixa, acentos, pontuação, espaços) | Não | Não | Igualdade exata em `Decimal` (`40 == 40.0`) | Isolar o ganho real da normalização léxica e numérica simples (Comentário #16). |
| **`PROPOSED`** | Sim | Sim | Sim (Levenshtein normalizado + comparação com Jaro-Winkler / tokens) | Igualdade exata em `Decimal` (`AD-009`) + separação título/evento/papel (`AD-010`) + limiares calibrados no piloto | Medir o ganho incremental de siglas, similaridade e regras de domínio sobre ambos os baselines. |

---

## 8. Síntese do que Foi Aprovado vs. O que Permanece em Aberto

Conforme `STATE.md` (`AD-004` a `AD-012` e `OPEN-01`), distingue-se estritamente o que já está decidido do que continua como proposta sem aprovação:

1. **Já aprovados (`STATE.md`):**
   - Um documento por atividade no MVP (`AD-004`);
   - Registro sem comprovante → `Inconclusivo / SEM_COMPROVANTE` (`AD-005`);
   - Documento sem registro correspondente → `DOCUMENTO_NAO_ASSOCIADO`, reportado fora da matriz $3 \times 3$ e avaliado separadamente nas métricas de associação (`AD-006`);
   - Associação ambígua → `Inconclusivo / ASSOCIACAO_AMBIGUA`, com solicitação de revisão humana, preservação do veredito automático original e cálculo das métricas automáticas antes da intervenção humana (`AD-007`);
   - Comparação exata de carga horária em `Decimal`: `40 == 40.0`; diferença factual como `40` vs `45` gera conflito no campo em par associado com registro da magnitude; ausência/`None` não é conflito numérico (`AD-009`);
   - Separação estrita entre nome do evento, título específico e papel de participação (extraídos só quando explícitos; título ausente no documento fica como detalhe não comprovado sem conflito factual, `AD-010`);
   - Cinco categorias no MVP (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO`, `ORGANIZACAO_EVENTO`), mantendo três classes (`Validado`, `Divergente`, `Inconclusivo`), sem incluir artigos ou trabalhos em anais (`AD-012`).
2. **Permanecem propostas sem aprovação (não devem ser decididas silenciosamente em código):**
   - Critério quantitativo de ambiguidade ($\tau_{\text{assoc}}$, $\Delta_{\text{empate}}$) e mecânica exata de resolução de disputas entre múltiplos registros/documentos na Etapa 1 (`OPEN-01`);
   - Denominadores exatos e protocolo final das métricas de associação (`AD-006`);
   - Tabela de essencialidade por categoria e regra de agregação final nas **5 categorias** (`AD-009`, `AD-010`, `AD-012`), incluindo:
     - veredito final do registro quando o título específico declarado no XML está ausente no certificado (`AD-010`);
     - tratamento formal de papéis de participação e coexistência de papéis em eventos (ex.: certificado de `Ouvinte` frente a `APRESENTACAO_TRABALHO` ou `ORGANIZACAO_EVENTO` **não** é contradição automática, pois a pessoa pode ter atuado em ambos os papéis no mesmo evento);
   - Regra para abreviação legítima de nomes próprios (`titular`) e siglas institucionais compostas (`D-M2-05`);
   - Escopo de entrega das métricas textuais adicionais (`Jaro-Winkler` e similaridade por tokens, `D-M2-06`).

---

## 9. Status das Decisões do M2 (`D-M2-01` a `D-M2-07`)

### `D-M2-01` — Política de Associação e Ambiguidade (`OPEN-01`, `AD-007`)
- **Status:** **Parcialmente decidida em `AD-007`.**
- **Parte aprovada (`AD-007`):** Candidatos ambíguos resultam em `Inconclusivo / ASSOCIACAO_AMBIGUA`, com encaminhamento à revisão humana (exibindo candidatos e evidências por campo), preservação da decisão automática original e cálculo das métricas automáticas antes da revisão humana.
- **Parte ainda pendente:** Definição da mecânica exata de disputa entre múltiplos registros/documentos (pareamento por afinidade com margem $\Delta_{\text{empate}}$ vs. atribuição global 1-para-1 com detecção de empate) e calibração dos limiares no piloto.

### `D-M2-02` — Escopo da Matriz $3 \times 3$ vs. Documentos Órfãos (Comentário #61, `AD-006`)
- **Status:** **Resolvida em `AD-006` (com denominadores de associação pendentes no protocolo experimental).**
- **Decisão aprovada (`AD-006`):** A matriz $3 \times 3$ avalia exclusivamente os registros curriculares nas 3 classes (`Validado`, `Divergente`, `Inconclusivo`); documentos sem registro correspondente são reportados fora da matriz como `DOCUMENTO_NAO_ASSOCIADO` e a associação é avaliada separadamente. Denominadores e protocolo final da associação permanecem pendentes.

### `D-M2-03` — Separação entre `title`, `event_name` e `participation_role` (`M1-OPEN-04`, `AD-010`)
- **Status:** **Parcialmente decidida em `AD-010`.**
- **Parte aprovada (`AD-010`):** Manter nome do evento, título específico da palestra/trabalho e papel de participação como campos distintos, sem concatenação; ausência de título específico no comprovante não invalida automaticamente palestra/apresentação e é registrada como detalhe não comprovado (`MISSING_DOCUMENT`), sem conflito factual.
- **Parte ainda pendente:** Como a tabela de decisão por categoria agrega campos incompletos (ex.: se título declarado no XML e ausente no certificado leva a `Inconclusivo` ou permite `Validado` com ressalva quando evento, papel, instituição e ano coincidem).

### `D-M2-04` — Política de Carga Horária em `Decimal` (`M1-OPEN-02`, Comentário #63, `AD-009`)
- **Status:** **Parcialmente decidida em `AD-009`.**
- **Parte aprovada (`AD-009`):** Igualdade exata em `Decimal` após normalização numérica (`40 == 40.0`); diferença factual como `40` vs `45` gera conflito de carga horária por campo no par associado, registrando a magnitude da diferença; valor ausente/`None` não é conflito numérico.
- **Parte ainda pendente:** Tabela de essencialidade e agregação final por categoria para determinar o veredito do registro a partir das evidências por campo.

### `D-M2-05` — Abreviações Legítimas de Nome do Titular e Siglas Compostas (Comentários #36, #37 e #64)
- **Status:** **Proposta pendente de aprovação.**
- **Opções:**
  - **A (Recomendada):** Regra determinística explícita de compatibilidade de iniciais/tokens para nomes abreviados + correspondência de sigla no prefixo/token institucional na tabela de siglas.
  - **B:** Depender apenas da métrica de similaridade global (`Levenshtein` / `Jaro-Winkler` / `Token`).

### `D-M2-06` — Seleção da Métrica Textual Principal vs. Comparação entre Métricas (Comentário #37)
- **Status:** **Proposta pendente de aprovação.**
- **Opções:**
  - **A (Recomendada):** Interface comparadora plugável já no M2 com Levenshtein normalizado como padrão e Jaro-Winkler / tokens disponíveis como variantes puras configuráveis.
  - **B:** Implementar somente Levenshtein normalizado no M2 e deixar Jaro-Winkler/tokens para o M5.

### `D-M2-07` — Essencialidade por Categoria (5 Categorias) e Coexistência de Papéis (`AD-010`, `AD-012`)
- **Status:** **Proposta pendente de aprovação.**
- **Escopo da decisão necessária:**
  1. Fechar a matriz de atributos essenciais vs. opcionais/não aplicáveis para cada uma das **5 categorias** (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`, `PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`), respeitando que `CARGA-HORARIA` não existe na gramática XML de eventos, produção técnica e graduação/pós `stricto sensu` (`AD-011`).
  2. Definir a regra de evidência e agregação para **coexistência de papéis em eventos**: um certificado de `Ouvinte` (ou `Participante`) para o mesmo evento **não** constitui contradição factual automática de um registro de `APRESENTACAO_TRABALHO`, `ORGANIZACAO_EVENTO` ou `Palestrante`, pois a mesma pessoa pode exercer múltiplos papéis no evento; deve-se aprovar se tal par resulta em `Inconclusivo` por papel específico não comprovado pelo documento pareado.

---

## 10. Critérios de Aceite Verificáveis (Para Futura Implementação do M2)

Quando as decisões pendentes forem aprovadas e o M2 for implementado, o módulo será considerado verificável pelos seguintes critérios objetivos:

1. **Isolamento e Determinismo:**
   - Execução de toda a suíte `pytest` do `matcher/` sem Docker, PostgreSQL, Redis, rede ou variável `GEMINI_API_KEY`;
   - Ausência de qualquer importação de `google.genai`, `fastapi`, `celery`, `sqlalchemy` ou `redis` dentro de `comprova_lattes/matcher/`;
   - Duas execuções idênticas sobre as mesmas entradas e `MatcherConfig` produzem `MatchingResult` bit-a-bit idêntico.
2. **Neutralidade do LLM (`AD-002`, #52):**
   - Alterar `confianca_extracao` (ex.: `0.01` vs `0.99`) ou `categoria_sugerida` em `raw_metadata` não altera em nenhum caso a associação, o `status`, o `reason_code` ou os escores das `field_evidences`.
3. **Guarda Matemática de String Vazia (#60):**
   - Chamadas à função de similaridade com strings vazias ou strings que normalizam para vazio (`"---"`, `"   "`) não lançam `ZeroDivisionError` e não produzem `MATCH` espúrio em campos vazios.
4. **Fidelidade Numérica e Carga Exata (`Decimal`, `AD-009`):**
   - Cargas horárias (`Decimal("40")` vs `Decimal("40.0")` → `MATCH`; `Decimal("40")` vs `Decimal("45")` → `CONFLICT` no campo `carga` em par associado com magnitude `Decimal("5")` registrada) são comparadas sem coerção para `int` nem perda de precisão binária de `float`.
   - Registros cujo `workload_hours` é `None` (por ausência estrutural na categoria ou por descarte de valor inválido no parser com `INVALID_WORKLOAD_HOURS`) nunca geram conflito numérico inventado nem falso `MATCH` de carga horária.
5. **Separação Associação × Classificação e Revisão Humana (`AD-005`, `AD-006`, `AD-007`, #38, #61, #65):**
   - Registro sem comprovante resulta em `Inconclusivo / SEM_COMPROVANTE` (`AD-005`);
   - Documento órfão vai para `orphan_documents` com `DOCUMENTO_NAO_ASSOCIADO` fora da matriz $3 \times 3$ (`AD-006`);
   - Candidatos ambíguos produzem `Inconclusivo / ASSOCIACAO_AMBIGUA`, expondo candidatos para revisão humana e preservando o veredito automático original para que as métricas automáticas sejam calculadas antes da revisão (`AD-007`).
6. **Separação de Evento, Título e Papel (`AD-010`, `AD-012`):**
   - `event_name`, `title`/`activity_title` e `participation_role`/`participation_role_raw` são avaliados separadamente nas categorias aplicáveis dentre as 5 categorias do MVP;
   - Título específico declarado no XML e ausente no documento é registrado como `MISSING_DOCUMENT` (não comprovado), nunca `CONFLICT`;
   - Certificado de ouvinte não dispara `CONFLICT` automático contra registro de apresentação de trabalho ou organização de evento.
7. **Baselines e Rastreabilidade (#16, #62):**
   - Todos os modos (`BASELINE_EXACT`, `BASELINE_NORMALIZED`, `PROPOSED`) retornam `FieldEvidence` completa por atributo avaliado.
   - Limiares ficam externalizados em `MatcherConfig` com marcação explícita de calibração piloto vs. congelamento antes do conjunto final.

---

## 11. Casos de Teste Propostos (Sem Código)

> Todos os exemplos abaixo são **100% sintéticos e fictícios**.

| ID do Caso | Cenário / Regra Testada | Entrada Sintética Resumida (XML M1 + Doc) | Resultado Esperado | Requisito / Decisão |
| :--- | :--- | :--- | :--- | :--- |
| **TC-M2-01** | Variação legítima de caixa, acentuação e igualdade `Decimal` | XML: `"João Pedro Almeida"`, `"Análise de Dados"`, `"2024"`, `"40.0"`; Doc: `"JOAO PEDRO ALMEIDA"`, `"Analise de Dados"`, `"2024"`, `"40"` | `Validado`; `carga` com `MATCH` exato em `Decimal` (`40 == 40.0`) | #64, `AD-009` |
| **TC-M2-02** | Equivalência explícita de sigla institucional | XML: `institution="Universidade Federal Rural da Amazônia"`, `acronym="UFRA"`; Doc: `issuer_institution="UFRA"` | `Validado`; `instituicao` com `rule_applied="ACRONYM_EQUIVALENCE"` (sem depender de Levenshtein) | #36 |
| **TC-M2-03** | Abreviação legítima de titular (pendente `D-M2-05`) | XML: `"Maria Clara Ferreira"`; Doc: `"Maria C. Ferreira"` (demais campos compatíveis) | Proposta: `Validado` (se `D-M2-05=A`), diferenciando de troca de titular | #64, `D-M2-05` |
| **TC-M2-04** | Mutação factual — troca de titular | XML: `"Maria Clara Ferreira"`; Doc associado pelo restante: `"Carlos Eduardo Souza"` | `Divergente` (`CONFLITO_TITULAR`) | #38, #64 |
| **TC-M2-05** | Mutação factual — instituição distinta | XML: `"UFRA"`; Doc: `"UFPA"` (mesmo curso/ano/titular) | `Divergente` (`CONFLITO_INSTITUICAO`) | #36, #64 |
| **TC-M2-06** | Conflito de carga horária em `Decimal` (`40 vs 45` e `40 vs 400`) | Caso A: XML `40` vs Doc `45`; Caso B: XML `40` vs Doc `400` em par associado | `AD-009`: ambos geram `CONFLICT` no campo `carga` com magnitude (`5` e `360`) registrada na `FieldEvidence`; classificação final do registro segue tabela de agregação por categoria (pendente) | #63, `AD-009` |
| **TC-M2-07** | Mutação factual — ano incompatível por status | XML: `CONCLUIDO`, `end_year=2023`; Doc: `2021` (e caso `EM_ANDAMENTO`, `start_year=2023`, Doc `2024`) | Concluído `2023` vs `2021` → `Divergente`; Em andamento `2023` vs `2024` → `Validado` | Tabela §6.2 |
| **TC-M2-08** | Registro sem comprovante | XML com 2 registros, apenas 1 documento correspondente | Registro 1 avaliado na Etapa 2; Registro 2 → `Inconclusivo` (`SEM_COMPROVANTE`) | `AD-005`, #61 |
| **TC-M2-09** | Documento órfão sem registro no XML | XML com 1 registro (`"Curso A"`); 2 documentos (`"Curso A"` e `"Congresso X"` de outro tema/ano) | `"Curso A"` pareado; `"Congresso X"` em `orphan_documents` (`DOCUMENTO_NAO_ASSOCIADO`), fora da matriz $3 \times 3$ | `AD-006`, #38, #61, #65 |
| **TC-M2-10** | Associação ambígua e revisão humana separada | 1 registro e 2 documentos candidatos ambíguos | Registro → `Inconclusivo` (`ASSOCIACAO_AMBIGUA`), candidatos expostos para revisão humana; veredito automático original preservado para métricas pré-revisão | `AD-007`, #61 |
| **TC-M2-11** | Carga negativa descartada pelo parser M1 | XML recebeu `CARGA-HORARIA="-20"` → M1 entrega `workload_hours=None` + diagnóstico `INVALID_WORKLOAD_HOURS`; Doc traz `20` | `workload_hours` ausente no XML não gera conflito numérico inventado nem falso `MATCH` (`AD-009`); diagnóstico preservado | M1-spec §2.1, `AD-009` |
| **TC-M2-12** | Independência de `confianca_extracao` / `categoria_sugerida` | Par com conflito factual de ano, porém `raw_metadata={"confianca_extracao": 0.99, "categoria_sugerida": "Validado"}` | `Divergente` (metadados do LLM ignorados) | `AD-002`, #52 |
| **TC-M2-13** | Documento ilegível (`UNREADABLE`) | Documento pareado (ou único) com `extraction_status="UNREADABLE"` e campos `None` | `Inconclusivo` (`DOCUMENTO_ILEGIVEL`) | `ROADMAP.md` M3 |
| **TC-M2-14** | Guarda de divisão por zero em strings vazias | Campos normalizam para vazio (`"---"`, `"   "`) em ambos os lados | Sem exceção `ZeroDivisionError`; evidência marcada como `MISSING_BOTH`, nunca `MATCH` | #60 |
| **TC-M2-15** | Diferenciação entre Baselines A, B e Proposto | Caso 1: diferença só de caixa/acento; Caso 2: sigla `"UFRA"` + erro leve de digitação no título | `BASELINE_EXACT` falha nos 2; `BASELINE_NORMALIZED` acerta Caso 1 e falha Caso 2; `PROPOSED` acerta ambos | #16, #36 |
| **TC-M2-16** | Evento/apresentação com `title` no XML e apenas `event_name` no certificado | XML (`PARTICIPACAO_EVENTO` ou `APRESENTACAO_TRABALHO`) com `title="Artigo X"` e `event_name="Seminário Y"`; Doc apenas `event_name="Seminário Y"` | `AD-010`: `evento` avaliado separadamente (`MATCH`) e `titulo` marcado como `MISSING_DOCUMENT` (detalhe não comprovado, sem `CONFLICT`); veredito final do registro aguarda aprovação da agregação por categoria (`D-M2-07`) | `AD-010`, `AD-012` |
| **TC-M2-17** | Coexistência de papéis (certificado de ouvinte frente a apresentação/organização) | XML (`APRESENTACAO_TRABALHO` ou `ORGANIZACAO_EVENTO`) no `"Congresso Z"`; Doc pareado atesta `"Ouvinte"` no `"Congresso Z"` | Não gera `CONFLICT` / `Divergente` automático (papéis podem coexistir no evento); sinaliza papel específico da atividade como não comprovado pelo certificado, aguardando política de agregação (`D-M2-07`) | `AD-010`, `AD-012`, `D-M2-07` |
