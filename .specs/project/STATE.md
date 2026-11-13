# Project State & Open Decisions

**Last Updated:** 2026-11-12
**Current Work:** M0 Concluído — Pronto para iniciar M1 (Parser XML) e migração dos artefatos da pasta `TCC 2 / sharing` do Google Drive.

---

## Decisões Arquiteturais Consolidadas (AD)

### AD-001: Migração da API de Node.js/Fastify para Python 3.11+ (2026-11-12)
- **Decisão:** Substituir o boilerplate Node.js em `comprova-lattes-api/` por Python 3.11+ (`FastAPI`, `Celery`, `Pydantic`, `defusedxml`, `google-genai`).
- **Motivo:** Alinhamento estrito com a seção 6.3 do TCC e com os 88 comentários do orientador (Prof. Dr. Fabrício).

### AD-002: Separação Estrita entre Extração (LLM) e Decisão (Motor) (2026-11-12)
- **Decisão:** O Gemini atua exclusivamente convertendo documentos (PDF/imagem) em JSON validado. Campos como `confianca_extracao` e `categoria_sugerida` não podem ser usados na regra de decisão (Comentário #52).
- **Motivo:** Exigência metodológica central do trabalho.

### AD-003: Infraestrutura Local via Docker Compose (2026-11-12)
- **Decisão:** Manter `compose.yaml` em `comprova-lattes-api/` com PostgreSQL 16 e Redis 7 prontos para desenvolvimento local e execução do Celery, sem bloquear testes unitários/CLI do núcleo (Comentário #55).

---

## Pendências Administrativas (CTES / Orientador)

### [ADMIN-01] Justificativa de Mudança para Dados Sintéticos junto à CTES (Comentário #48)
- **Contexto:** Pelo Art. 21, parágrafo único do regulamento de TCC da UFRA, a substituição de dados reais por dados sintéticos em relação ao pré-projeto exige envio de justificativa formal do orientador à CTES até **30 dias antes da defesa**.
- **Minuta pronta para enviar ao Prof. Fabrício:**
  > *"Em atendimento ao Art. 21, parágrafo único, do Regulamento de TCC, informamos a adequação metodológica do protocolo experimental do TCC 2 para a utilização exclusiva de uma bancada de dados sintéticos controlados (arquivos XML e documentos comprobatórios fictícios), em substituição à coleta de currículos e documentos pessoais de terceiros prevista no pré-projeto. A alteração justifica-se pela necessidade de controle estrito das variáveis experimentais e dos operadores de perturbação (gabarito ground truth exato), pela eliminação de riscos relativos ao tratamento de dados pessoais identificáveis (Lei nº 13.709/2018 – LGPD e Resolução CNS nº 466/2012) e pela garantia de reprodutibilidade e disponibilização pública do conjunto de testes sem prejuízo aos objetivos geral e específicos da pesquisa."*

---

## Decisões em Aberto (Para Alinhar entre Caleb e Elivanilso)

### [OPEN-01] Unidade Formal de Análise e Cardinalidade (M2 / Comentários #38, #61 e #62)
- **Proposta padrão adotada:**
  1. O sistema recebe 1 XML (com $M$ registros auditáveis) e $N$ documentos comprobatórios.
  2. **Etapa 1 (Associação):** O motor busca o melhor par `(registro_lattes, documento)` acima de um limiar mínimo de associação (avaliado por Acurácia, Precisão e Revocação da associação — Comentário #65).
  3. **Etapa 2 (Classificação na Matriz $3 \times 3$, fundamentada em Fellegi & Sunter, 1969 — Comentário #38):** A unidade de análise é o **registro curricular pareado**:
     - Registro sem documento correspondente → `Inconclusivo` (`SEM_COMPROVANTE`).
     - Documento órfão sem registro no XML → reportado separadamente (`DOCUMENTO_NAO_ASSOCIADO`).
     - Empate/ambiguidade entre múltiplos documentos para o mesmo registro → `Inconclusivo` (`ASSOCIACAO_AMBIGUA`).

### [OPEN-02] Migração e Refatoração do Código Preliminar do Drive (`TCC 2 / sharing`)
- **Contexto:** Existe na pasta `TCC 2 / sharing` do Google Drive uma versão preliminar em `lattes_validator/` e os 30 casos piloto em `.html`/`.txt`.
- **Ação:** Migrar essa lógica para `comprova-lattes-api/src/comprova_lattes/` aplicando as correções do professor (`defusedxml`, validação DTD, geração de PDF/imagem com degradação visual via script em vez de `.txt`/`.html` limpos — Comentário #46).

### [OPEN-03] Modelo Exato da Família Gemini e Estratégia de Prompt (M3 / Comentários #32, #34 e #53)
- **Proposta padrão:** Fixar `GEMINI_MODEL=gemini-2.5-flash`, `temperatura = 0.0`, executar **3 repetições por documento** para medir variância e documentar a versão exata, data de execução e prompt (`zero-shot` com `response_schema`) no apêndice.

### [OPEN-04] Protocolo para Kappa de Cohen nos Gabaritos (M4 / Comentário #47)
- **Proposta padrão:** Caleb e Elivanilso rotulam independentemente os cenários sintéticos antes de fechar o `ground_truth.json`, salvando as duas anotações em `data/annotations/` para cálculo automático do Kappa de Cohen.
