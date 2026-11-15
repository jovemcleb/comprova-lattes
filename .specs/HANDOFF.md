# Handoff — Comprova Lattes

## Contexto para Elivanilso — publicação de 2026-11-15

**Leia este resumo primeiro; seções datadas abaixo preservam histórico.**

Verificação desta publicação: suíte backend completa **470 passed, 2 failed em69,60s**,
Ruff global aprovado. Falhas listadas abaixo; nenhuma ocultada ou desativada.

- Modelo escolhido: Gemini `gemini-3.5-flash-lite`, extrai entidades; motor
  determinístico decide. Temperatura omitida em Gemini3+, sem promessa de zero efetivo.
- Bancada inteiramente sintética:150cenários,50piloto(10famílias) e100finais
  (20famílias),5casos/família.120documentos no total,30casos sem comprovante.
- Gerador determinístico, emissores/IDs por partição, piloto invariável ao tamanho
  final. Pillow produz PNG/PDF raster; Tesseract por + conversor PDF implementados.
  Smoke local PNG/PDF funcionou, mas instalação local não é distribuída pelo GitHub.
  Instruções em experiments/README.md; dependências opcionais experiments/ocr.
- Relatórios de telemetria e métricas por categoria + coletor de artefatos/hashes
  implementados. Documentação: .specs/docs/experiment-reporting.md e artifact-collection.md.
- **Estado de desenvolvimento com falhas conhecidas:** após retirar pistas textuais
  das mutações,2testes de vereditos esperam Divergente e recebem Inconclusivo.
  Não mudar limiar/gabarito para esconder resultado. Publicação é compartilhamento
  de trabalho em andamento, não versão experimental validada ou congelada.
- Próximas tarefas autorizadas: distribuir sigla/evidência entre operadores,
  substituir X inicial por variação legítima, diagnosticar os2testes, implementar
  interface de anotação independente. Não rodar estudo oficial antes das correções.
- Caleb e Elivanilso avaliarão os mesmos150casos separadamente, começando por5piloto.
  Nos120com documento, transcrever campos sem sugestões; nos30sem,registrar ausência.
  Associação,classe,motivo; salvar progresso e JSON individual. Preservar A/B antes
  de Kappa e consenso, consenso em terceiro arquivo. Interface ainda não existe.
- Estatística aprovada:3execuções separadas+média; IC95%,2.000reamostragens de
  famílias inteiras incluindo todas repetições; McNemar exato complementar sobre
  acerto integral da família,4comparações Levenshtein vs Exato/Normalizado/JW/Tokens
  com Holm. Não tratar variantes como independentes;20famílias limitam inferência.
- Guia humano: critérios objetivos primeiro, interpretação contextual justificada
  quando necessário; sem evidência suficiente=Inconclusivo. Guia não deriva de
  limiares do algoritmo. Estados ausente/ilegível distintos.
- Ordem: ajustar no piloto -> congelar código/config/gerador/protocolo -> gerar e
  hashear final -> anotações independentes+consenso -> avaliar sem tuning do final.
  Nenhum resultado oficial, consenso humano ou congelamento foi produzido.
- Monografia ainda precisa ser reconciliada com modelo, famílias, templates e
  protocolo. Detalhes atuais em STATE.md e experimental-protocol/proposal.md.


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


## Parecer Argon recuperado — 2026-11-15

Revisão somente leitura via local-agent-flow: run-key
`tcc-150-synthetic-argon-review-20261115`, task `workbench-review`, attempt `att-01`,
sessão `74e7770f-8fc2-44ff-b38c-18e95ca8d0cc`. Ponte retornou succeeded/ok e zero
inferências durante espera; summary truncado. Texto integral recuperado do histórico
local da sessão, em leitura somente, salvo em `.tmp-argon-review-20261115/report.md`
(ignorado pelo Git). Modelo solicitado gemini-4-argon-high; observed_model unknown,
embora UI fornecida pelo usuário identifique Argon high. Não houve nova chamada de
modelo para recuperar o texto. Usuário autorizou chamadas adicionais se necessárias.

Conferidos independentemente no código: grade 25/família, omissão apenas de titular,
ausência dos operadores ampliados, calibração por Macro-F1 com primeiro empate,
McNemar por família toda correta e Holm em todos os pares. Proposta preserva N=150:
40 documentos piloto e 80 finais se preservados 10/20 casos sem comprovante;
120+240 chamadas nominais com três repetições, sem contar retentativas.

Sugestões ainda não aprovadas: redistribuir operadores sem aumentar N; usar blocos
menores com identidades/templates distintos; avaliar trecho nome/sigla por evidência
e não só igualdade literal; separar artefatos piloto/final e congelar parâmetros
após piloto; definir anotação independente/Kappa e desempate antes da avaliação.
Não aceitar automaticamente conclusões estatísticas do parecer: nomes/IDs novos não
provam independência de templates; reportar limitação de poucos clusters; ressalva
textual não torna válido McNemar de variantes dependentes. Gabarito de caso limítrofe
não pode ser definido pelos limiares do motor calibrado. Não aplicado nenhum patch
de implementação ou mudança estatística do worker.

## Modelo aprovado — 2026-11-15

AD-015: usar `gemini-3.5-flash-lite`, após sondagem nos mesmos cinco comprovantes
do piloto (5/5 extrações, 37/37 campos presentes; limites no relatório em docs/).
Padrão/backend e .env local atualizados; sem migração para Interactions. Gemini 3+
usa parâmetros de amostragem do provedor, não temperatura zero. Atualização da
monografia V8 e ampliação da bancada continuam pendentes. Histórico abaixo preservado.

## Atualização — 2026-11-15

AD-014 implementada: relação nome/sigla explícita por documento com trecho literal,
prompt `entities-v2`, dicionário fixo de apoio, sem atualização global. Decisões da
conversa e limites no topo de STATE; contrato em ARCHITECTURE.

Gate completo atual: **403 passed in 32.44s**, Ruff e diff-check aprovados.
Travamento anterior isolado em `socketpair` local do asyncio/TestClient no sandbox;
reprodutor mínimo trava no sandbox e passa fora. Suíte passou fora do sandbox sem
alteração de código/testes. Comando em `docs/quality.md`. Sem serviços externos,
instalações, commit ou push. Registros e gates abaixo permanecem históricos.

**Data:** 2026-11-13

## S2 - matcher corrigido e gate aprovado

S2: bloqueio ORGANIZACAO_EVENTO corrigido com autorização em 2026-11-13. Quando event_name=None, evento recebe NOT_APPLICABLE/STRUCTURAL_NOT_APPLICABLE e titulo é essencial, mesmo ausente; com evento preenchido o comportamento anterior permanece. Regressão parametrizada cobre evento documental ausente/presente e título documental ausente. Todos os testes existentes de matcher e experiments preservados; pilot/final aprovados. Gate completo: 396 passed em 24,09 s; Ruff, npm run lint e npm run build com exit 0. Sem instalação, commit/push ou serviços externos; integração real, DTD e estudo oficial continuam pendentes.

Escrita desta continuação limitada a rules.py, test_matcher.py, quality.md e STATE/ROADMAP/HANDOFF. A rodada anterior abaixo é histórica; sua pendência de autorização e falha de aceite foram superadas. Comandos e limitação do TEMP em docs/quality.md.

## S2 — correções aplicadas, aceite bloqueado

- Escrita restrita aos 15 alvos da solicitação S2. Nenhuma instalação, commit/push ou alteração em parser/matcher/extractor/api; mudanças preexistentes preservadas.
- XML de eventos/produção técnica com subnós corretos, APRESENTADOR documental e event_name=None em organização; 25 casos/família. Siglas explícitas por emissor via `synthetic_acronyms(corpus.cases)` e radicais `SYNTHETIC_ACRONYMS`; variação ASCII leve e mutações de carga 40→45/400, ano +7, titular e instituição. Operador agora `factual_mutation`; regenerar corpus/manifestações de integridade antigos.
- Exemplo operacional do matcher continua opção explícita sem calibração aprovada; template inicial nulo. Upload incremental/deduplicação nome+tamanho/limpeza, e revisão humana restaura estado persistido ao reabrir, inclusive associação explicitamente nula.
- Gates: suíte completa final S2 teve 392 passed / 2 failed, exit 1; Ruff exit 0 com aviso de cache; npm lint/build exit 0. Smoke Node/Vite confirma template inválido até preencher e exemplo operacional aceito. Comandos e limites em [quality.md](../docs/quality.md).
- **Pendência concreta:** `matcher/rules.py:essential_fields` exige `evento` em ORGANIZACAO_EVENTO, embora parser preserve event_name=None. Testes de identity/legitimate expõem INCONCLUSIVO em ambas as partições. Solicitada ampliação mínima de escopo para corrigir essencialidade e cobrir regressão. Aguardar decisão antes de escrever em matcher; não mascarar com evento inventado ou expectativa enfraquecida. O aceite integral não foi atingido.
- README raiz/API/app, ARCHITECTURE e PROFESSOR-REQUIREMENTS reconciliados com código offline; DTD, estudos reais Gemini/Tesseract, Kappa humano, calibração e cronometragem seguem pendentes. Histórico abaixo mantém seus resultados/limites originais.
**Foco:** M6 backend verificado offline e interface React implementada. Gate frontend: lint/build exit 0 e smoke checks Node/React SSR. Gate backend histórico: 390 testes e Ruff. Integração interativa com serviços reais e estudo oficial pendentes. Histórico abaixo preservado; implementação frontend atual descrita a seguir.

## Gate M6 frontend (2026-11-13)

- Implementado em `comprova-lattes-app/src/`: rotas `/`, `/validacoes/nova`, `/validacoes/:validationId`; tipos, serviço HTTP, hooks TanStack Query, componentes e páginas separados. Nenhuma alteração em package.json/package-lock, instalação ou escrita em api/.
- Cinco endpoints reais conectados. URL via `VITE_API_BASE_URL` ou localhost:8000; CORS requer origem permitida. Health exibe metadados sem presumir infraestrutura ativa. Listagem percorre páginas de 100, ordena globalmente por data decrescente e pagina localmente em 20; revisar estratégia para histórico volumoso.
- XML via ArrayBuffer/base64 preserva bytes/ISO-8859-1; texto UTF-8 rejeita declaração incompatível. Documentos PDF/PNG/JPEG/WebP base64, até 100. MatcherConfig completo editável, thresholds nulos exigindo decisão explícita; validação local sem alegar calibração.
- Polling somente PENDING/PROCESSING; erros da API apresentados. Erro 503 de despacho preserva link ao ID criado. Auditoria M1/M3/M2 completa, documentos originais/extrações, evidências por campo, candidatos, pares, diagnósticos e órfãos separados. Sumários são contagens operacionais.
- AD-013: formulário aberto para review_required, revisão sob solicitação para outras classes, parecer inclusive INCONCLUSIVO, reviewer/justification obrigatórios, associação a qualquer documento do lote e rejeições mutuamente consistentes. Histórico preserva automático e exibe último parecer separado; identidade declarada, sem autenticação.
- Executados de `comprova-lattes-app/`: `npm run lint` → exit 0; `npm run build` → exit 0 (TypeScript + Vite/React Compiler). Smoke checks Node em memória, sem arquivos/pacotes novos: bytes/base64 preservados, configuração nula/ordem/MIME inválidos rejeitados, rotas/payloads de POST e ID recuperável no erro 503. Renderização SSR via Vite/React: três rotas e detalhe completo sintético com encaminhamento AD-013 aprovados.
- Limites de verificação: sem percurso interativo/visual em navegador, chamadas ao Gemini, Postgres/Redis ou teste ponta a ponta real. Prévia PDF depende do navegador, com download alternativo. Gate backend abaixo não reexecutado porque testes escrevem temporários no diretório api/ fora do escopo autorizado. Nenhuma alegação nova de infraestrutura funcional, dados reais ou resultados científicos.
- Uso, organização e limites em `comprova-lattes-app/README.md`. Preservadas alterações preexistentes; sem commit/push.

## Gate M6 backend (2026-11-13)

- **390 passed em 24,23 s**, incluindo **30 testes novos em tests/test_api.py**; `.venv/Scripts/ruff.exe check .` → **All checks passed!**. TestClient, SQLite em memória (`StaticPool`), extrator fake, dispatcher injetável e tarefa Celery local sem broker. Nenhuma instalação, Postgres/Redis/Gemini ativo ou chamada paga.
- Comandos efetivamente executados de `comprova-lattes-api/`, usando Python global e dependências existentes da `.venv` (launcher uv tem restrição local):

```powershell
python -u -c "import sys; sys.path.insert(0, '.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=tests/.tmp-m6-gate']))"
.\.venv\Scripts\ruff.exe check .
```

- Contrato HTTP/OpenAPI em `/docs`: POST `/validations` exige `matcher_config` (MatcherConfig completo com thresholds explícitos), exatamente um de `xml_content` UTF-8 ou `xml_base64` (preserva bytes/encoding), e `documents` com document_id/filename/mime_type/content_base64. Sem `UploadFile`/`Form`. Resposta 202, ID persistido antes de despacho. GET `/validations` tem offset/limit; GET `/validations/{id}` inclui fontes, configuração, relatório M1, entidades M3, resultado M2/candidatos/evidências, registros e histórico.
- POST `/validations/{id}/records/{index}/review`: reviewer/status/justification obrigatórios; matched_document_id opcional e rejected_document_ids. Data UTC do servidor; nenhum campo de resultado automático aceito na entrada. POST é solicitação explícita de revisão para VALIDADO/DIVERGENTE; INCONCLUSIVO já sinaliza review_required. Permite parecer manual sem associação e manutenção de inconclusão, confirmação/correção para qualquer documento do lote e rejeição de candidatos; IDs externos, duplicatas e associação simultaneamente rejeitada retornam 422.
- Histórico append-only pelos endpoints, último evento por registro determina parecer corrente. `automatic_result` e `automatic_summary` permanecem originais; `reviewed_summary` conta último parecer ou automático para registros sem revisão. Documentos órfãos/evidências automáticos não são reescritos por parecer manual; associação humana fica no evento. Contagens não são avaliação científica.
- `worker.process_validation_task` (`comprova_lattes.process_validation`) usa serviço compartilhado `api/service.py`; `ping_task` mantido. Ciclo PENDING → PROCESSING → COMPLETED/FAILED, erro só por tipo sem conteúdo sensível; claim atômico impede redelivery de reexecutar resultado pronto. Falha de despacho persiste DISPATCH_FAILED e responde 503 com ID consultável. Parser rejeita XML inseguro antes de enfileirar. CORS local Vite, configurável no create_app.
- Runtime configurado pelo Settings existente: SQLAlchemy cria tabelas ausentes lazy no primeiro acesso, API e worker compartilham database_url; Celery usa redis_url. Extrator padrão usa GeminiExtractor e fecha cliente próprio. Sem migração de esquema existente, retry/recovery de jobs interrompidos em PROCESSING ou dispatch falho, autenticação ou identidade verificada do revisor. Não implica serviço pronto para exposição pública nem auditoria imutável contra acesso administrativo ao banco.
- Cobertura: pipeline real parser/matcher, três classes, ambiguidade, órfãos/correção, rejeições, histórico sucessivo, preservação automática, validação de entrada e atomicidade de rejeições, falhas sanitizadas, estados pendentes, redelivery e tarefa Celery local. Integração PostgreSQL/Redis/Gemini reais não verificada; frontend permanece pendente.
- Escrita somente `api/`, `worker.py`, `tests/test_api.py` e STATE/ROADMAP/HANDOFF; alterações preexistentes preservadas. `ARCHITECTURE.md` não atualizado por estar fora do escopo autorizado; consultar STATE para implementação atual. Sem commit/push, documentos reais ou mudança nos módulos científicos. Temporários do gate em `tests/.tmp-m6-gate/`, não versionar.

## Gate M4/M5 (2026-11-13)

- **360 passed em 20,10 s**, suíte completa; `.venv/Scripts/ruff.exe check .` → **All checks passed!**. `git diff --check` sem erro (aviso CRLF preexistente no extrator).
- Launcher uv da `.venv` retorna `permission denied`; Python 3.14.7 global executou dependências já instaladas, sem instalação. Pytest sem cache e com `--basetemp` em tests porque o diretório temporário padrão está bloqueado. Comando efetivamente executado, da API:

```powershell
python -u -c "import sys; sys.path.insert(0, '.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=tests/.tmp-experiments-gate-final-1794617948']))"
.\.venv\Scripts\ruff.exe check .
```

- Instruções CLI/formato em `src/comprova_lattes/experiments/README.md`. Testes incluem geração determinística/isolamento, PNG CRC/dados e PDF xref/stream, degradação, OCR simulado, 3 repetições, classes/associação/órfãos/propagação, estatística conhecida, calibração/freeze e replay dos três comandos CLI.
- Escrita restrita a experiments, novo `tests/test_experiments.py` e STATE/ROADMAP/HANDOFF. Alterações preexistentes de parser/matcher/extractor/testes preservadas. Nenhuma chamada paga, pacote novo, corpus real, commit ou push.
- Família é indivisível e identifica emissor/template exclusivos. Tamanho configurável em famílias de 25 casos, sem fixar 30/~90 como aprovados. XML gerado não foi validado contra gramática externa; imagens raster stdlib substituem HTML/DOCX neste recorte.
- Limites: um registro por XML, sem avaliação de concorrência multirregistro; rótulos são intenções, não anotação humana independente. CLI usa extrações capturadas; OCR real é injetável e Tesseract não é instalado. Metadados são preservados sem estimar custo ausente. Distribuição, modelo/prompt e desenho oficial continuam pendentes.
- Calibração rejeita final e hash verifica artefatos/configuração/corpus. O gerador materializa ambas as partições: controle externo deve manter final oculto antes do congelamento. Integridade SHA-256 não comprova cegamento ou cronologia. Sem resultado científico real ou meta de F1.
- Temporários dos testes ficaram em `tests/.tmp-experiments-gate-1794617948/` e `tests/.tmp-experiments-gate-final-1794617948/`; remoção recursiva foi rejeitada pela política automática do ambiente. Não versionar esses diretórios.

## Gate atual S1 (2026-11-13)

- **344 testes aprovados**, Python 3.14 local; **Ruff aprovado**, sem erros. Testes incluem o parser M1 e extrator M3 preexistentes, preservados nesta tarefa.
- Comandos executados em `comprova-lattes-api/`:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) '.venv/Lib/site-packages')
python -m pytest -q -p no:cacheprovider
python -m ruff check .
```

- O launcher uv de `.venv/Scripts/python.exe` recebeu acesso negado; o Python global não possui pytest/Ruff. Os comandos acima usam as dependências existentes, sem instalar pacotes. Primeira execução: 340 testes aprovados com aviso de escrita no cache; gate final desativa somente o cache e inclui quatro casos adicionais, sem aviso. Nenhum teste desativado.
- Correções: comparação direta de Decimal e diferença exata em contexto local dimensionado; falhas M3 fora da atribuição e sinalizadas nos registros sem par; âncoras com conteúdo após normalização; ano inicial comparado quando presente nos dois lados mesmo com ano final igual.
- Falhas sem entidades não autorizam associação. Registros sem par recebem `FALHA_EXTRACAO` ou `DOCUMENTO_ILEGIVEL` e diagnósticos com documento/status, sinalizando incerteza do lote. Documentos continuam não associados; pares válidos permanecem válidos. Sem falhas no lote, ausência de comprovante continua `SEM_COMPROVANTE`.
- Testes integrados usam `GeminiExtractor.extract` com transporte SDK simulado e passam seus contratos reais ao matcher: sucesso, Decimal além de 28 dígitos, conflito de ano inicial, `API_ERROR`, `INVALID_JSON`, `UNREADABLE`, lotes mistos, nenhum registro e round-trip JSON. Teste de importação isolada mantém matcher independente de Google/Redis/PostgreSQL.
- M2 implementa associação global, baselines exato/normalizado/proposto, normalização, siglas, métricas textuais, regras/evidências e contratos de revisão. M3 implementa entrada multimodal, JSON Schema/Pydantic, entidades separadas, metadados e erros. Isso não comprova qualidade de extração real nem desempenho experimental.
- Nenhum experimento, corpus real, chamada paga, revalidação XSD, frontend ou Compose executado nesta tarefa. Limiares dos testes são sintéticos. Escrita restrita a matcher, testes e STATE/ROADMAP/HANDOFF; sem commit/push. Diffs preexistentes preservados.
- STATE e ROADMAP refletem este gate. Descrições planejadas em `codebase/ARCHITECTURE.md` e contratos históricos permanecem fora do escopo de escrita; reconciliar em tarefa autorizada posterior.

## Ler primeiro

`AGENTS.md`, `.specs/project/{PROJECT,ROADMAP,STATE}.md`. Requisitos: `.specs/codebase/PROFESSOR-REQUIREMENTS.md`; fonte: `docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md`. Perguntar antes de decisões materiais. Preservar diffs; sem commit/push, chamadas pagas ou uso experimental de documentos pessoais.

## Histórico M1 anterior ao gate S1

- M1: cinco categorias, parser seguro (`defusedxml`), UTF-8/ISO-8859-1, limites de tamanho/profundidade, proveniência. Carga inválida vira `None` com diagnóstico; frações em `Decimal`. No gate S1, o parser preexistente já gera IDs determinísticos únicos; testes cobrem repetição e independência da ordem dos atributos. A descrição histórica de ausência de IDs foi superada.
- AD-012: apresentação de trabalho e organização de evento implementadas em categorias próprias; título/evento/natureza/papel separados. Ensino fundamental e olimpíada mapeados. Sem artigos/anais. Referência de mapeamento técnico: `features/m1-parser/technical-production.md`.
- Gate independente local: **130 testes e Ruff aprovados**, Python 3.14. Seis fixtures de `m1-conformant/` e `m1-technical/` revalidadas independentemente contra XSD, sem rede e somente leitura. Evidência e hashes em `docs/m1-linux-verification.md`.
- Hydrogen relata também **130 testes e Ruff em Linux/Python 3.12.16**. Relatório final recuperado no histórico, resposta 136; ponte havia coletado mensagem intermediária. Gate Linux não repetido pelo revisor; imagem local não contém pytest/Ruff.
- Revisão de segurança, contratos, proveniência e testes técnicos sem bloqueio identificado no recorte examinado; não equivale a cobertura exaustiva ou conformidade runtime. `ORGANIZADOR` deriva da seção XML, inclusive para curadoria/montagem/museologia; M2 não deve assumir equivalência com papel documental sem decisão. Brutos canônicos removem espaços externos; originais permanecem na proveniência.
- XSD oficial do Extrator é referência principal; DTD comunitária é comparação histórica. Conformidade XSD não comprova equivalência UI nem cumprimento do requisito DTD do professor. Licenças/publicação pendentes. `lxml` somente container descartável, nunca host/runtime.

## Delegações encerradas

Ponte: skill global `local-agent-flow`; executável `C:\Users\Caleb Lima\AppData\Local\Programs\simple-orchestrator\simple-orchestrator.exe`.

- Hydrogen: run `tcc-m1-technical-hydrogen-20261113`, task `technical-production`, attempt `att-01`, sessão `ba572676-15ee-4cfc-8ed5-67a4b1730392`. Encerrado; relatório final recuperado após mensagem intermediária. Não há pergunta do worker pendente para esta entrega.
- Argon revisão inicial: run `tcc-argon-methodology-review-20261113`, task `methodology-review`, attempt `att-01`, sessão `63470ec1-931c-4ded-bfbd-7cdcc2745c05`. Relatório integral recuperado no histórico (a ponte truncou o corpo). Sugestões não são decisões aprovadas.
- Argon consistência: run `tcc-argon-doc-consistency-20261113`, task `doc-consistency`, attempt `att-01`, sessão `b21e5ccc-25b3-4800-b494-40ed71f58198`. **Falhou sem resposta final**; deixou PROJECT, ROADMAP e proposta M2 alterados. Reconciliação documental concluída pelo Codex, preservando diffs e sem editar código.

## Decisões e pendências

- AD-013 aprovada: todos os inconclusivos encaminhados à revisão humana; validados/divergentes revisáveis por solicitação. Documentos/candidatos/evidências/motivos visíveis; confirmar/corrigir associação, rejeitar candidatos, emitir parecer ou manter inconclusivo; justificar alterações e registrar revisor/data. Resultado automático e métricas preservados, parecer manual separado. Contratos M2/protocolo atualizados; fluxo ainda não implementado, previsto na API/interface.
- Usuário aceita declarações ou certificados como tipos de comprovante e orienta alinhar evento, data e local. Isso não aprova automaticamente suficiência documental nem resolve essencialidade por categoria. Comparar somente precisão temporal disponível; sem inventar data completa.
- Usuário orientou contar resultados idênticos das três repetições uma vez por caso; preservar saídas para estabilidade. Regra para execuções diferentes continua pendente.
- M2 já implementa essencialidade, título omitido e coexistência de papéis; isso não encerra decisões científicas ainda registradas como propostas. Ouvinte não implica exclusão de apresentação/organização no mesmo evento. Ausência estrutural de horas não é divergência nem motivo global de inconclusão.
- Unidade formal, distribuição dos 30/~90 casos pelas cinco categorias, famílias/agrupamento, IC/reamostragem, agregação de repetições diferentes e McNemar continuam propostas. Não aplicar integralmente recomendações do Argon sem aprovação.
- Documentos órfãos fora da matriz 3×3; associação avaliada separadamente. Métricas automáticas anteriores à revisão humana. M2 implementado e verificado offline; protocolo/experimentos M4 e fluxo operacional de revisão ainda planejados.

## Próximos passos

1. Revisar pendências científicas da tabela implementada e alinhar os contratos históricos antes de calibrar M2; implementação não resolve decisões metodológicas automaticamente.
2. Fechar desenho da bancada e estatística antes de gerar o corpus; manter piloto separado do final e não usar documentos reais sem autorização.
3. Confirmar com orientador a alternativa XSD ao requisito DTD; compatibilidade UI permanece não comprovada.
4. Calibrar e congelar limiares somente no piloto aprovado; definir modelo e repetições de M3. API/interface e revisão humana em etapa posterior.

## Workspace — histórico de autorização anterior

A tarefa S1 atual proíbe commit/push; a autorização histórica abaixo não foi utilizada nesta execução.

Usuário autorizou commit/push do trabalho acumulado em 2026-11-13 para `jovemcleb/comprova-lattes` (público). Publicação inclui M1, testes sintéticos, documentação e ferramentas próprias. Legado do Drive e cópias locais de gramáticas/metadados de terceiros excluídos por `.gitignore`; licenças ainda pendentes. Referências históricas a caminhos locais não significam que os arquivos estão no clone público. A reconciliação final alterou somente documentação; código do Hydrogen preservado. Gate pré-publicação repetido: 130 testes, Ruff e `docker compose config --quiet` aprovados. Git diff sem erro de whitespace. Para estado efetivo da publicação, consultar Git/remoto, não inferir deste texto. Evidências históricas de 92/105 testes não devem ser confundidas com o gate atual de 130.
