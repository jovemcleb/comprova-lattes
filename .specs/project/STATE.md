# Project State & Open Decisions

**Last Updated:** 2026-11-12
**Current Work:** M0 — Setup Base Python + Docker Compose e Organização de Contexto

---

## Decisões Arquiteturais Consolidadas (AD)

### AD-001: Migração da API de Node.js/Fastify para Python 3.11+ (2026-11-12)
- **Decisão:** Substituir o boilerplate Node.js em `comprova-lattes-api/` por Python 3.11+ (`FastAPI`, `Celery`, `Pydantic`, `defusedxml`, `google-genai`).
- **Motivo:** Alinhamento estrito com a seção 6.3 do TCC e com os comentários do orientador (Prof. Dr. Fabrício).
- **Impacto:** O núcleo funcional (`parser`, `extractor`, `matcher`, `experiments`) roda como pacotes Python independentes via CLI (P0) e é exposto via FastAPI + Celery (P2).

### AD-002: Separação Estrita entre Extração (LLM) e Decisão (Motor) (2026-11-12)
- **Decisão:** O Gemini atua exclusivamente convertendo documentos (PDF/imagem) em JSON validado. Campos como `confianca_extracao` e `categoria_sugerida` não podem ser usados na regra de decisão.
- **Motivo:** Exigência metodológica central do projeto (comentários 31, 33, 51 e 52).

### AD-003: Infraestrutura Local via Docker Compose (2026-11-12)
- **Decisão:** Manter `compose.yaml` em `comprova-lattes-api/` com PostgreSQL 16 e Redis 7 prontos para desenvolvimento local e execução do Celery, sem bloquear testes unitários/CLI do núcleo (que rodam sem depender de banco).

---

## Decisões em Aberto (Para Alinhar entre Caleb e Elivanilso)

> Estas perguntas estão documentadas para que a dupla ou o orientador batam o martelo antes/durante os marcos M1–M4:

### [OPEN-01] Unidade Formal de Análise e Cardinalidade (M2 / Comentários 35, 59–61)
- **Questão:** Qual será a unidade formal contabilizada na Matriz de Confusão $3 \times 3$?
- **Proposta padrão adotada até segunda ordem:**
  1. O sistema recebe 1 XML (com $M$ registros auditáveis) e $N$ documentos comprobatórios.
  2. **Etapa 1 (Associação):** O motor busca o melhor par `(registro_lattes, documento)` acima de um limiar mínimo de associação (avaliado por métricas próprias de associação).
  3. **Etapa 2 (Classificação na Matriz $3 \times 3$):** A unidade de análise é o **registro curricular pareado**:
     - Registro sem documento correspondente → `Inconclusivo` (`SEM_COMPROVANTE`).
     - Documento órfão sem registro no XML → reportado separadamente (`DOCUMENTO_NAO_ASSOCIADO`).
     - Empate/ambiguidade entre múltiplos documentos para o mesmo registro → `Inconclusivo` (`ASSOCIACAO_AMBIGUA`).

### [OPEN-02] Obtenção da DTD Oficial do Lattes (M1 / Comentários 24 e 50)
- **Questão:** Onde armazenar o arquivo `.dtd` oficial do CNPq (`curriculo_lattes.dtd`) para validação offline dos XMLs sintéticos?
- **Ação pendente:** Adicionar um arquivo DTD oficial (ou schema derivado de um XML exportado da Plataforma Lattes) em `comprova-lattes-api/schemas/lattes/` com resolução de rede desabilitada (`no_network=True`).

### [OPEN-03] Modelo Exato da Família Gemini e Estratégia de Prompt (M3 / Comentários 31 e 51)
- **Questão:** Qual identificador exato de modelo será fixado nos experimentos (ex.: `gemini-2.5-flash`) e se o experimento principal usará `zero-shot` ou `few-shot`?
- **Proposta padrão:** Fixar o modelo em variável de ambiente (`GEMINI_MODEL=gemini-2.5-flash`), temperatura `0.0`, e testar `zero-shot` com `response_schema` estrito como padrão, documentando a versão exata nos logs de saída.

### [OPEN-04] Protocolo para Kappa de Cohen nos Gabaritos (M4 & M5)
- **Questão:** Como Caleb e Elivanilso farão a rotulagem dupla independente dos cenários sintéticos para calcular o Kappa de Cohen?
- **Proposta padrão:** Cada integrante classifica independentemente uma planilha/JSON dos cenários antes de consolidar o `ground_truth.json` final, salvando ambas as anotações em `data/annotations/` para o script calcular o Kappa automaticamente.

---

## Active Blockers

- Nenhum bloqueador técnico no momento.
