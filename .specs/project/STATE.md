# Project State & Open Decisions

## Protocolo aprovado — 2026-11-15

Usuário aprovou três execuções separadas + média das métricas; IC95% com2.000
reamostragens por família preservando casos e repetições; semente explícita fixada
antes de executar. Guia prioriza critérios objetivos e análise contextual justificada,
sem evidência suficiente=Inconclusivo, sem copiar limiares do motor. Ordem aprovada:
ajustes piloto -> congelar código/config/gerador/guia/protocolo -> gerar/hash final ->
anotações humanas independentes e consenso -> avaliação final sem tuning posterior.
Detalhes e limites na seção mais recente de experimental-protocol/proposal.md.
Testes/final fixtures já vistos não tornam avaliação oficial cega retroativamente.
Pendências de execução: interface de revisão ainda não implementada, distribuição
aprovada das características dos certificados, diagnóstico de2testes falhando e
reconciliação de código/docs às decisões. Não houve estudo oficial nem nova execução
de testes nesta atualização documental.


## McNemar complementar por família aprovado — 2026-11-15

Usuário aprovou McNemar exato complementar sobre acerto integral dos cinco casos
por família (20famílias finais), quatro comparações Levenshtein versus Exato,
Normalizado,Jaro-Winkler e Tokens, com correção Holm. Métricas principais continuam
sobre100casos e intervalos por família; teste não mede diferença de Macro-F1.
Descrever perda de resolução (4/5 é família incompleta), baixa potência possível
e necessidade de justificar independência entre famílias, sem supô-la automática.
Não altera gabaritos/limiares nem aprova execução final. Tratamento dos IC e
repetições deve ser reconciliado explicitamente antes do congelamento.


## Anotação humana de campos aprovada — 2026-11-15

Usuário aprovou incluir anotação independente de campos documentais na mesma
revisão dos150cenários por Caleb e Elivanilso. Nos120cenários com documento,
cada um transcreve titular,instituição/nome-sigla,evidência literal,título/atividade,
evento,papel,carga horária e anos presentes no comprovante. Campos inicialmente
em branco; estados presente/ausente/ilegível explícitos, sem converter ilegível
em None silenciosamente. Não apresentar sugestões Gemini/gold/expected/pares alheios.
Copiar valores do XML para preencher lacunas do documento não é permitido; UI deve
separar fase documental da comparação XML para reduzir influência. Nos30cenários
sem documento, registrar ausência e não exigir transcrição. Preservar anotações
A/B originais e evidências; consenso separado. Decisão é escopo aprovado da futura
interface, não implementação concluída nem revisão humana já executada.


## Revisão humana integral aprovada — 2026-11-15

Usuário escolheu revisão dos mesmos150cenários por Caleb e Elivanilso,
independentemente (150avaliações por pessoa;300respostas individuais), em vez de
amostras distintas por família. Consenso somente após preservar respostas originais
e calcular concordância pré-consenso. Ensaio inicial com cinco casos piloto;
se guia/ficha mudar, reavaliar esses casos antes da concordância oficial.
Interface proposta: XML organizado e comprovante lado a lado, associação/classe/motivo,
progresso salvo e exportação JSON separada por avaliador; consenso em terceiro arquivo.
Interface ainda não implementada/verificada. Não mostrar expected/gold/resultado motor
nem resposta do outro avaliador. Conferência do gabarito de campos de extração e
escolhas estatísticas restantes não são aprovadas por consequência desta decisão.


## Decisão sobre pistas remanescentes — 2026-11-15

Usuário aprovou distribuir características dos certificados entre casos, incluindo
presença de sigla/evidência, e substituir X inicial por variação legítima, mantendo
150cenários. Implementação dessa ampliação ainda pendente. Não implica aprovação
de anotação por agentes como substituição dos autores, nem escolha estatística.
Usuário solicitou alternativas de anotação assistida e protocolo estatístico.


## Correção de pistas explícitas e bloqueio atual — 2026-11-15

Delegação neutral-mutations concluída: nomes alternativos com mesmo prefixo e
comprimento, sem OUTRA/DIVERGENTE, derivados deterministicamente sem usar scores.
Coordenador executou tests/test_synthetic_leakage.py + test_certificate_templates.py
+ test_experiments.py: **28 passed, 2 failed (14,23s)**; Ruff global aprovado.
Falhas em test_synthetic_categories_and_operator_verdicts[pilot/final]: mutação
factual retorna INCONCLUSIVO em vez de DIVERGENTE com limiares fixos de teste.
Não alterar gabarito nem calibrar contra final para mascarar falha; diagnóstico e
tratamento metodológico pendentes. Gate469 anterior é histórico, não estado atual.
Parecer humano recebido como proposta: revisão visual piloto, anotações A/B cegas
independentes, hash pré-consenso, consenso separado e Kappa pré-consenso. Recomendação
anotar150 e alternativa amostral ainda exigem decisão do usuário. Templates e
protocolo humano não aprovados por agente. Sem freeze/estudo/API Gemini/publicação.


## Integração das delegações — 2026-11-15

Coletados OCR/metrics/artifacts/template-review. Ponte marcou OCR e metrics como
failed por turno sem resposta final, apesar de código presente. Coordenador não
assumiu conclusão: executou testes conjuntos (77 passed, 32,73 s), suíte completa
backend fora do sandbox (469 passed, 43,96 s) e Ruff global aprovado. Tesseract
5.4.0.20240606 executado, idioma por disponível, pypdfium2 5.15.2 e Pillow13 local.
Smoke real de PNG e PDF raster de registro identity piloto, degradação0/DPI72,
retornou statusOK, titular e40h; não comprova acurácia global nem avaliação oficial.
Relatórios e coletor implementados; reporting.py acrescentado pelo coordenador ao
inventário de código para hashes. Coleta definitiva deve ocorrer após integração.
Sonnet solicitada para revisão, observed_model unknown na ponte: parecer reporta
cinco imagens legitimate vistas e aponta valor INSTITUICAO DIVERGENTE SINTETICA,
pistas estruturais exclusivas de legitimate e realismo limitado. Achados exigem
revisão humana/desenho, não foram alterados implicitamente. Não usar documentos
finais para ajustar regex/prompt. Estatística, anotação humana, aprovação dos templates
e congelamento oficial seguem pendentes. Sem chamadas Gemini, commit ou push.


## Templates sintéticos em português (rascunho assistido) — 2026-11-15

Implementados em `experiments/synthetic.py` os cabeçalhos/frases fixas neutras de
apresentação para as cinco categorias (`FORMACAO_ACADEMICA`, `FORMACAO_COMPLEMENTAR`,
`PARTICIPACAO_EVENTO`, `APRESENTACAO_TRABALHO` e `ORGANIZACAO_EVENTO`) e os rótulos
em português do contrato (`Titular`, `Atividade`, `Evento`, `Papel`, `Instituição emissora`,
`Sigla da instituição`, `Identificação da instituição`, `Ano de início`, `Ano de conclusão`,
`Ano da atividade` e `Carga horária`), substituindo as chaves inglesas do schema no
`document_text`. Assinatura `document_text(record, layout=0, category=None)` preserva
compatibilidade de chamadas e recebe `category` no `generate`. Valores literais do
registro (`gold`), ausência de campos `None`, `Decimal` numérico sem unidade em
carga horária, trecho literal AD-014 (`Identificação da instituição`), ordenação
relativa das chaves antes de omissões, independência do piloto, 150 cenários (50+100)
e isolamento entre famílias permanecem inalterados. O template depende apenas de
família/layout/categoria, sem imprimir status, operador ou chaves técnicas.

**Proveniência e limites metodológicos:** a redação dos cabeçalhos e frases em
português constitui rascunho de composição assistida por agente da mesma família de
modelos (`Gemini`, `TEMPLATE_PROVENANCE`), exigindo validação e aprovação humana
explícita antes do congelamento (`freeze`) e da execução dos experimentos oficiais.
Não se afirma independência metodológica entre a preparação textual da bancada e o
extrator avaliado, nem realismo gráfico documental. Atualizados `test_experiments.py`
e criado `test_certificate_templates.py`; o teste `test_baseline_injected_and_failures`
usa `document_text` real com layout/categoria e depende da adaptação concorrente de
`experiments/baseline.py` para os rótulos em português. Nenhum corpus oficial foi
gerado ou congelado; calibração, OCR real e estudos M3/M4/M5 continuam pendentes.


## Integração Pillow e correções do gerador — 2026-11-15

Retornos delegados recolhidos; integração verificada pelo coordenador: 45 testes
em test_experiments.py + test_render_pillow.py aprovados (8,77 s), Ruff global
aprovado. Pillow opcional instalado localmente (13.0.0), raster PNG/PDF com mesma
matriz grayscale; metadados registram versão Pillow/FreeType. Inspeção visual de
amostra local legível, mas formato ainda usa nomes técnicos de campos, sem alegação
de realismo. Fonte embarcada com diacríticos compostos exige validar percepção/OCR.
Piloto invariável ao tamanho final, ordem de campos estável nas omissões, sem
render de no_document; legitimate usa evidência local nome/sigla sem tabela final.
Não houve estudo oficial, chamada Gemini, instalação OCR ou mudança estatística.
Pendentes: adaptador Tesseract real, métricas/telemetria agregadas, artefatos reais
de congelamento e decisões sobre anotação, repetições e comparações estatísticas.
Não reutilizar corpus antigo como nova bancada; registrar ambiente antes de congelar.


## Reorganização aprovada e implementada — AD-016 (2026-11-15)

150 cenários: **10 famílias piloto de cinco casos (50)** e **20 famílias finais
 de cinco casos (100)**. Cada família mantém um registro-base/categoria e os cinco
operadores existentes; categorias balanceadas separadamente por partição.
Emissores exclusivos, ordem dos campos, margens e espaçamento variam deterministicamente.
A mudança não comprova independência estatística. Não executar estudo oficial nem
reutilizar corpus/manifestos antigos. Ampliação de operadores e revisão das métricas
continuam pendentes; não foram implicitamente concluídas por esta reorganização.

**Atualizar depois na monografia:** substituir 2/4 famílias de 25 por 10/20 de cinco;
explicar definição da família, balanceamento por categoria e diversidade de layouts;
atualizar quadro de composição e figuras; revisar unidade de reamostragem e limitações.
Continuam 40 documentos piloto e 80 finais; três repetições seriam 120 + 240 chamadas,
sem contar retries, reaproveitando extrações na etapa integrada. Sem resultados novos.


## Bancada aprovada — AD-016 (2026-11-15)

Usuário confirmou **150 cenários inteiramente sintéticos: 50 piloto + 100 finais**.
Não derivar XMLs ou documentos da edição de currículos pessoais. Esta decisão
substitui a proposta histórica de 30/~90 nos documentos do projeto. Piloto serve
para calibração e ajustes; final para avaliação com parâmetros congelados.
O gerador atual contém cinco casos por família (10 piloto + 20 finais).
Ampliação dos operadores e adequação estatística ainda precisam de revisão, sem
aumentar N implicitamente. Não tratar 100 variantes como 100 unidades independentes.
Argon será consultado somente para revisão de estrutura/cobertura, sem gerar
conteúdo documental ou gabaritos. Geração deve permanecer determinística e fictícia.

## Modelo escolhido — AD-015 (2026-11-15)

Usuário aprovou `gemini-3.5-flash-lite` após a sondagem comparativa. Atualizados
modelo padrão do backend e `.env` local, sem alterar a chave. Essa decisão substitui
a proposta de 2.5 Flash em OPEN-03 e a escolha anterior de 3.8. Temperatura permanece
omitida para Gemini 3+, com metadados provider_default; não afirmar temperatura zero
efetiva. Modelo será usado na continuidade do piloto; avaliação final exige congelar
também prompt e parâmetros. V8 da monografia ainda descreve 2.5 e deve ser atualizada,
assim como a referência técnica. A sondagem não equivale à avaliação científica final.

## Sondagem real de modelos — 2026-11-15

Comparação autorizada em cinco comprovantes sintéticos `identity` do piloto,
mesmos bytes e contrato, uma chamada/modelo/documento. 3.8: 0/5 sucessos; 3.1
Flash-Lite: 4/5, 30/30 campos presentes corretos nos sucessos; 3.5 Flash-Lite:
5/5, 37/37 campos presentes corretos, média 1,63 s. Sem diferenças nos campos
ausentes em respostas concluídas. Sondagem simplificada, ordem sequencial e uma
repetição; não comprova superioridade ou estudo oficial. Modelo configurado
preservado. Evidências, hashes e limitações em
[relatório](../../docs/gemini-model-probe-20261115.md).

## Ajustes operacionais Gemini — 2026-11-15

Temperatura omitida em Gemini 3+ com metadados corretos, timeout e número de
tentativas configuráveis, backoff/jitter e auditoria sanitizada implementados.
Gate: 412 testes aprovados e Ruff. Catálogo da chave consultado; não prova cota ou
gratuidade. Teste mínimo 3.8 Flash ainda retorna 504; extração real pendente.
Modelo não alterado, sem migração para Interactions. Detalhes em quality/ARCHITECTURE.

## Teste real Gemini — 2026-11-15

Primeiro teste com PDF fictício e modelo local `gemini-3.8-flash`: corrigido erro
400 no transporte do JSON Schema (SDK 3.3.0), passando a `response_json_schema`.
Após correção, serviço retornou 504 e 503; nenhuma extração bem-sucedida. Não trocar
modelo ou enfraquecer contrato silenciosamente. Gate offline atualizado: **404 testes
aprovados em 22,05 s**, Ruff/diff-check aprovados. Detalhes em `docs/quality.md`.

## Verificação atual — 2026-11-15

Investigado travamento da suíte: `socketpair` interno ao loop asyncio bloqueado no
sandbox, reproduzido sem código do projeto e resolvido ao executar fora dele.
Gate completo: **403 testes aprovados em 32,44 s**, Ruff e diff-check aprovados.
Sem correção no código ou dependências; serviços reais continuam não verificados.
Comandos e evidência em [quality.md](../../docs/quality.md).

## Decisões do usuário — 2026-11-15

- AD-014 aprovada: extrair relação explícita nome/sigla do emissor com trecho
  documental, aplicá-la apenas ao documento e manter dicionário fixo como apoio.
  Sigla isolada desconhecida sinaliza incerteza. Implementação e limites em
  [ARCHITECTURE.md](../codebase/ARCHITECTURE.md), prompt `entities-v2`.
- Aprovados os três experimentos, incluindo Gemini real e baseline OCR + regras;
  ampliar cobertura com coexistência de papéis e similaridade limítrofe sem forçar
  desempate; incluir telas na monografia após teste interativo. Ampliação da bancada
  e capturas ainda não executadas; tamanho/distribuição continuam pendentes.
- Usuário concordou em testar Gemini 3.8 Flash no piloto; configuração ainda não
  alterada. A V8 da monografia especifica 2.5 Flash, portanto OPEN-03 abaixo é
  histórico e texto/configuração precisam ser reconciliados antes da avaliação.

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
