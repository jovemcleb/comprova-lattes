# Project State & Open Decisions

**Last Updated:** 2026-11-13
**Current Work:** M1 ampliado para cinco categorias (AD-012): 130 testes e Ruff aprovados em verificação local independente; seis fixtures conformes/técnicas revalidadas offline contra XSD. Hydrogen relatou também 130 testes e Ruff em Linux/Python 3.12. Requisito DTD e equivalência UI permanecem pendentes. M2/protocolo em proposta; revisão humana ampliada aprovada em AD-013, ainda não implementada.

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

### AD-004: Um documento por atividade no MVP (2026-11-13)
- **Decisão do usuário:** O fluxo inicial trabalha com um documento comprobatório por atividade; extração de várias atividades de um mesmo documento fica fora do MVP.
- **Motivo:** Reduzir complexidade de extração, associação e avaliação experimental.
- **Limite:** Esta decisão não define automaticamente tratamento de duplicatas, empates ou documentos sem correspondência; esses casos permanecem em OPEN-01. Não selecionar silenciosamente uma atividade em documento que contenha várias.

### AD-005: Registro sem comprovante (2026-11-13)
- **Decisão do usuário:** Registro curricular sem documento comprobatório associado recebe `Inconclusivo`, com motivo `SEM_COMPROVANTE`.
- **Motivo:** Ausência de evidência não equivale a conflito factual; não classificar automaticamente como `Divergente`.

### AD-006: Documento sem registro correspondente (2026-11-13)
- **Decisão do usuário:** Documento sem registro associado no XML é reportado separadamente como `DOCUMENTO_NAO_ASSOCIADO`.
- **Métricas:** Não incluir esse documento como quarta classe nem forçá-lo em `Validado`, `Divergente` ou `Inconclusivo` na matriz de classificação dos registros. Avaliar associação separadamente; denominadores e protocolo final ainda precisam ser especificados.

### AD-007: Associação ambígua e revisão humana (2026-11-13)
- **Decisão do usuário:** Candidatos ambíguos resultam em `Inconclusivo / ASSOCIACAO_AMBIGUA`, com solicitação de revisão humana e apresentação dos candidatos e evidências por campo.
- **Revisão:** Pessoa pode confirmar associação, rejeitar candidatos ou manter inconclusivo. Preservar resultado automático original; registrar decisão humana e motivo separadamente.
- **Experimentos:** Métricas do método automático são calculadas antes da intervenção humana. Critério quantitativo de ambiguidade ainda depende de calibração piloto.

### AD-008: Avaliação sem meta arbitrária de Macro-F1 (2026-11-13)
- **Decisão do usuário:** Remover a meta `Macro-F1 >= 0,85` sem justificativa, conforme comentário #66; reportar resultados efetivamente obtidos com intervalo de confiança.
- **Limite:** Não ajustar gabarito ou conjunto final para atingir resultado desejado. Método estatístico, nível do intervalo e unidade de reamostragem permanecem pendentes de definição no protocolo experimental.

### AD-009: Comparação exata de carga horária (2026-11-13)
- **Decisão do usuário:** Comparar horas em `Decimal` após normalização numérica: `40` e `40.0` são iguais; diferença factual como `40` versus `45` gera conflito de carga horária em par associado.
- **Evidência:** Registrar magnitude da diferença. Valor ausente/descartado como inválido não é conflito numérico comprovado. Classificação final segue tabela por categoria ainda em definição.

### AD-010: Evento, trabalho e papel de participação separados (2026-11-13)
- **Decisão do usuário:** Manter nome do evento, título do trabalho/palestra e papel de participação como informações distintas, extraídas somente quando explícitas. Não concatenar campos nem presumir apresentação a partir de participação genérica.
- **Palestrante/apresentador:** Ausência do título específico no comprovante não invalida automaticamente a atividade. Comparar evento, papel, instituição e data quando disponíveis e pertinentes ao registro.
- **Limite de evidência:** Se o registro declarar título específico não informado no documento, sinalizar esse detalhe como não comprovado, sem convertê-lo em conflito factual. Agregação final de campos incompletos ainda depende da tabela de decisão por categoria.

### AD-011: Referência estrutural XML e conjuntos de teste (2026-11-13)
- **Decisão do usuário:** Usar XSD oficial do Extrator CNPq como referência principal de estrutura; DTD comunitária como comparação histórica. Criar fixtures conformes separadas dos casos de robustez/tolerância já existentes.
- **Limites:** Não pressupor equivalência integral entre Extrator e exportação da interface. Manter parsing seguro independente e sem rede. Substituição do requisito DTD mencionado pelo professor ainda precisa ser justificada e confirmada com ele; não marcar essa exigência como atendida só pela decisão técnica interna.

---

### AD-012: Apresentação de trabalho e organização de evento no MVP (2026-11-13)
- **Decisão do usuário:** Incluir `APRESENTACAO-DE-TRABALHO` e `ORGANIZACAO-DE-EVENTO` em `PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA`, além das três seções iniciais.
- **Entrega:** Mapear XSD e estender contratos/parser com testes e fixtures conformes em entrega separada. Preservar natureza, título, evento e papel sem inferências indevidas.
- **Limite:** Aprovação não inclui artigos nem trabalhos publicados em anais. Atualizar protocolo experimental para novas categorias antes de avaliá-las; ampliação foi decisão do usuário, não exigência do professor.

### AD-013: Ampliação da revisão humana auditável (2026-11-13)
- **Decisão do usuário:** Encaminhar associações ambíguas e demais resultados `Inconclusivo` para revisão humana. Permitir também revisão de `Validado` e `Divergente` quando solicitada pelo usuário, sem exigir revisão de todos os registros.
- **Fluxo aprovado:** Apresentar documentos, candidatos de associação, dados comparados, evidências por campo e motivos. A pessoa pode confirmar ou corrigir a associação, rejeitar candidatos e emitir parecer manual, inclusive manter `Inconclusivo`. Toda alteração exige justificativa; registrar revisor, data, parecer e motivo.
- **Rastreabilidade:** Preservar resultado e evidências automáticos originais. Registrar associação e parecer humanos separadamente, sem sobrescrever a decisão automática.
- **Experimentos:** Calcular métricas automáticas antes da intervenção humana. Se resultados após revisão forem avaliados, apresentá-los separadamente; esta aprovação não define um experimento humano adicional nem altera o gabarito.
- **Fundamento e alcance:** O comentário #38 do professor menciona revisão manual de possíveis associações. A extensão para todos os inconclusivos e para revisão solicitada de outras classes é decisão do usuário, não exigência explícita do professor.
- **Entrega:** Contratos M2/protocolo reconciliados após a entrega parcial do Argon; implementar o fluxo de revisão na etapa de API/interface. Decisão registrada, funcionalidade ainda não implementada. Não altera a prioridade do M1 nem resolve a tabela de essencialidade por categoria ou as escolhas estatísticas pendentes.

## Pendências Administrativas (CTES / Orientador)

### [ADMIN-01] Justificativa de Mudança para Dados Sintéticos junto à CTES (Comentário #48)
- **Contexto:** Pelo Art. 21, parágrafo único do regulamento de TCC da UFRA, a substituição de dados reais por dados sintéticos em relação ao pré-projeto exige envio de justificativa formal do orientador à CTES até **30 dias antes da defesa**.
- **Minuta pronta para enviar ao Prof. Fabrício:**
  > *"Em atendimento ao Art. 21, parágrafo único, do Regulamento de TCC, informamos a adequação metodológica do protocolo experimental do TCC 2 para a utilização exclusiva de uma bancada de dados sintéticos controlados (arquivos XML e documentos comprobatórios fictícios), em substituição à coleta de currículos e documentos pessoais de terceiros prevista no pré-projeto. A alteração justifica-se pela necessidade de controle estrito das variáveis experimentais e dos operadores de perturbação (gabarito ground truth exato), pela eliminação de riscos relativos ao tratamento de dados pessoais identificáveis (Lei nº 13.709/2018 – LGPD e Resolução CNS nº 466/2012) e pela garantia de reprodutibilidade e disponibilização pública do conjunto de testes sem prejuízo aos objetivos geral e específicos da pesquisa."*

---

## Decisões em Aberto (Para Alinhar entre Caleb e Elivanilso)

### [OPEN-01] Unidade Formal de Análise e Cardinalidade (M2 / Comentários #38, #61 e #62)
- **Parte decidida:** Um documento por atividade (AD-004), registro sem comprovante como `Inconclusivo / SEM_COMPROVANTE` (AD-005) e documento órfão separado como `DOCUMENTO_NAO_ASSOCIADO` (AD-006). Demais regras abaixo ainda são propostas.
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
