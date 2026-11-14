# Project State & Open Decisions

**Last Updated:** 2026-11-13
**Current Work:** S2: bloqueio ORGANIZACAO_EVENTO corrigido com autorização em 2026-11-13. Quando event_name=None, evento recebe NOT_APPLICABLE/STRUCTURAL_NOT_APPLICABLE e titulo é essencial, mesmo ausente; com evento preenchido o comportamento anterior permanece. Regressão parametrizada cobre evento documental ausente/presente e título documental ausente. Todos os testes existentes de matcher e experiments preservados; pilot/final aprovados. Gate completo: 396 passed em 24,09 s; Ruff, npm run lint e npm run build com exit 0. Sem instalação, commit/push ou serviços externos; integração real, DTD e estudo oficial continuam pendentes.

## S2 — correções e bloqueio de escopo (2026-11-13)

- Gerador usa subnós DADOS-BASICOS/DETALHAMENTO em eventos/produção técnica; organização preserva event_name=None; apresentação inclui APRESENTADOR no gabarito documental. Famílias mantêm 25 casos isolados por emissor/template/partição.
- `legitimate`: sigla por emissor materializada por `synthetic_acronyms`, radicais exportados em `SYNTHETIC_ACRONYMS`, espaços e uma edição ASCII no título longo. `factual_mutation` substitui year_mutation: 40→45/400, ano +7, titular e instituição por categoria. Corpus/manifestos antigos precisam ser regenerados.
- Frontend: exemplo operacional explícito sem alegar calibração, restauração do template com limiares nulos, upload incremental com deduplicação nome+tamanho, limpeza e revisão ressincronizada ao reabrir, preservando associação humana nula.
- Reconciliação de README raiz/API/app, quality, ARCHITECTURE e PROFESSOR-REQUIREMENTS: implementação offline separada de estudos/anotação/decisões pendentes; links ../../../../Caleb removidos.
- Bloqueio resolvido nesta continuação autorizada; detalhes e gate atual no início deste documento. O bloqueio relatado na rodada S2 anterior fica superado por esta correção.
- Comandos, resultados e limites em [quality.md](../../docs/quality.md). Sem instalação, commit/push, dados reais ou serviços externos; alterações preexistentes preservadas.

## M6 — interface React e auditoria AD-013 (2026-11-13)

- Rotas `/`, `/validacoes/nova` e `/validacoes/:validationId`, com camadas types/lib/hooks/components/pages. Fetch para os cinco endpoints reais, URL via `VITE_API_BASE_URL` (padrão localhost:8000), TanStack Query para cache/invalidação/polling e React Router para navegação.
- Upload XML binário em `xml_base64` preserva encoding original; texto usa UTF-8 em `xml_content` e rejeita declaração incompatível. Múltiplos comprovantes PDF/PNG/JPEG/WebP em base64; configuração completa do matcher editável e obrigatória, com thresholds inicialmente nulos, sem limiares científicos implícitos.
- Auditoria M1 → M3 → M2: fonte curricular/proveniência por registro, diagnósticos/encoding/variantes, extrações completas e documentos originais, evidências por campo, candidatos e pares. Órfãos DOCUMENTO_NAO_ASSOCIADO separados; contagens automáticas e após revisão distintas, sem interpretação como métricas científicas.
- AD-013: encaminhamento com review_required, revisão solicitada nas outras classes, associação/correção com qualquer documento do lote, rejeições sem contradição, reviewer/justification obrigatórios e histórico de pareceres. Snapshot automático permanece preservado; estado humano vem da resposta do servidor.
- Gate frontend: `npm run lint` e `npm run build`, ambos exit code 0. Smoke checks Node em memória: conversão binária/base64, MatcherConfig, MIME, POST criação/revisão e ID após 503; React SSR das três rotas e detalhe COMPLETED/INCONCLUSIVO com formulário AD-013 renderizados. SSR não é teste interativo de navegador.
- Limites: integração PostgreSQL/Redis/Gemini e percurso interativo em navegador não exercitados. PDF depende do visualizador do navegador (download disponível). Histórico carrega páginas ascendentes da API, ordena globalmente e pagina localmente; custo cresce com o histórico. Backend gate de 390 testes é histórico, não reexecutado nesta tarefa para preservar restrição de escrita em api/.
- Escrita limitada a app/src, app/README e STATE/ROADMAP/HANDOFF; dependências e alterações preexistentes preservadas. Sem instalação, commit, push, corpus real ou mudanças metodológicas.

## M6 — backend e revisão auditável (2026-11-13)

- `api/main.py`: health preservado, CORS localhost/127.0.0.1:5173 configurável via fábrica, criação JSON (XML texto ou base64 e PDF/imagens base64), listagem paginada, consulta e revisão por índice de registro. Sem multipart ou pacotes novos.
- SQLAlchemy em `api/db.py`: entrada/documentos, configuração explícita do matcher, relatório M1, extrações M3 e snapshot completo M2 persistidos em JSON; revisões em tabela separada, histórico incremental com revisor, data UTC do servidor, parecer, justificativa, associação e rejeições. Fontes, candidatos e evidências disponíveis na consulta.
- AD-013: inconclusivos encaminhados; POST de revisão constitui solicitação para qualquer classe. Documentos associados/rejeitados precisam pertencer ao lote; correção pode selecionar documento fora dos candidatos automáticos. Contradições e duplicatas rejeitadas. Nunca sobrescreve resultado/evidências automáticos; `automatic_summary` conta classes originais e `reviewed_summary` usa último parecer por registro, com automático como fallback. São contagens operacionais, não métricas científicas.
- `worker.py`: tarefa `comprova_lattes.process_validation`, pipeline M1 → M3 → M2 com extrator injetável. Claim atômico PENDING → PROCESSING evita reprocessamento e sobrescrita em entregas duplicadas. Estados COMPLETED/FAILED e DISPATCH_FAILED, erro sanitizado; health/importação não conectam serviços. Dispatcher injetável nos testes.
- Gate: suíte completa **390 passed em 24,23 s**, incluindo **30 testes API**; `.venv/Scripts/ruff.exe check .` → **All checks passed!**, offline, SQLite em memória, TestClient, extrator fake e Celery local (`apply`). Comandos em HANDOFF.
- Limites: sem autenticação; `reviewer` é identidade declarada, não verificada. Histórico auditável no aplicativo, sem proteção contra administrador do banco. Sem migração de banco existente ou recuperação automática de jobs interrompidos em PROCESSING/dispatch falho. PostgreSQL/Redis/Gemini reais não exercitados. Frontend fora do escopo da entrega backend histórica; implementado na entrega frontend descrita acima. `ARCHITECTURE.md` permanece histórico/alvo por restrição de escrita; estado de implementação atual neste documento.
- Alterações preexistentes preservadas; escrita desta entrega somente api/, worker.py, tests/test_api.py e STATE/ROADMAP/HANDOFF. Sem commit/push ou corpus real.

## M4/M5 — implementação offline (2026-11-13)

- Gerador determinístico stdlib: 5 categorias × 5 operadores por família, XML consumível pelo parser e PDF raster/PNG com degradação. Família/emissor/template não atravessam piloto/final. Rótulos são intenções sintéticas, não consenso humano.
- Exp 1: OCR+RegEx injetável, 3 saídas preservadas, métricas por campo, falhas e estabilidade sem triplicar N. Exp 2: A/B e Levenshtein/Jaro-Winkler/tokens. Exp 3: reutiliza extrações, matriz 3×3 automática pré-revisão, associação separada, órfãos fora da matriz e propagação de erros.
- Kappa pré-consenso, bootstrap percentil de famílias, McNemar binomial exato por acerto integral da família e Holm. Semente/réplicas/confiança explícitos; sem meta arbitrária. Repetições distintas são relatadas separadamente, sem adotar consenso silencioso.
- Calibração rejeita final; seleção por Macro-F1 piloto com desempate pelo primeiro candidato. Manifesto verifica hashes de artefatos, configuração, XML, documentos e gabaritos antes dos runners CLI.
- Limites: bancada atual usa um registro por XML, sem competição entre vários registros. Renderização direta stdlib substitui HTML/DOCX nesta implementação autorizada. Sem alegação de conformidade XSD/DTD, execução Tesseract/Gemini real ou rotulagem independente concluída. Corpus materializa ambas as partições; freeze verifica integridade, não prova cegamento cronológico.
- Uso e formatos: `comprova-lattes-api/src/comprova_lattes/experiments/README.md`. Configurações demonstrativas não aprovam desenho definitivo, modelo, tamanhos ou limiares. Sem documentos reais, novos pacotes, commit/push ou alterações a parser/matcher/extractor.
- Gate final executado: suíte completa **360 passed em 20,10 s**; `.venv/Scripts/ruff.exe check .` → **All checks passed!**. Python 3.14 global com dependências já instaladas da `.venv`; cache desativado e temporários direcionados para `tests/` devido a restrições locais. Comando reproduzível e limitações no HANDOFF.

## S1 / AV-05 — evidência local (2026-11-13)

- Decimal: igualdade direta e diferença exata com precisão e faixa de expoentes locais, independentes do contexto externo; regressões de baixa precisão, arredondamento, underflow, overflow e serialização.
- Falhas M3: excluídas da atribuição; registros sem par recebem inconclusão por falha/ilegibilidade quando há extrações malsucedidas no lote, com diagnósticos identificando documento/status. Isso sinaliza incerteza do lote e não prova vínculo entre falha e registro. Documentos permanecem no relatório de não associados; pares válidos não são contaminados.
- Âncoras: título/evento somente pontuação não sustenta associação após normalização. Ano inicial comparado quando presente em ambas as fontes, preservando regra de ano final/intervalo.
- M1: cinco categorias e regressões existentes verificadas, incluindo IDs determinísticos, contêineres repetidos e fallbacks de títulos, resumo, status e ano. Parser preservado nesta tarefa; requisito DTD e equivalência UI continuam pendentes.
- M2: associação global um-para-um, três modos (exato, normalizado e proposto), métricas textuais, regras por categoria, evidências e contratos de revisão implementados. Limiares dos testes são sintéticos, não calibração científica; fluxo de revisão na API/interface ainda planejado.
- M3: SDK multimodal, validação local JSON/Pydantic e metadados implementados; integração M3 → M2 testada com transporte simulado para sucesso, precisão Decimal, conflito de ano inicial, falhas isoladas e lotes mistos. Confiança/categoria sugeridas não participam da decisão.
- Gate final: `python -m pytest -q -p no:cacheprovider` → **344 passed**; `python -m ruff check .` → **All checks passed!**. Python 3.14 global com dependências existentes da `.venv` em `PYTHONPATH`; launcher uv da `.venv` bloqueado por acesso negado. Reprodução em HANDOFF. Cache pytest desativado após aviso de escrita; nenhum teste desativado.
- Nenhum corpus real, calibração piloto, Macro-F1, chamada paga ou revalidação XSD nesta tarefa. O histórico de 130 testes/XSD permanece em `docs/m1-linux-verification.md`; não confundir com o gate atual.
- Escrita restrita a matcher, testes e STATE/ROADMAP/HANDOFF; diffs preexistentes de parser/extrator preservados. Sem commit/push. Descrições planejadas em `codebase/ARCHITECTURE.md` e contratos históricos não foram alteradas por estarem fora do escopo autorizado.

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
- **Entrega:** Contratos M2/protocolo reconciliados após a entrega parcial do Argon; backend de revisão verificado offline e interface implementada no M6; integração real pendente. Não resolve o requisito DTD do M1, a tabela de essencialidade por categoria ou escolhas científicas pendentes.

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
