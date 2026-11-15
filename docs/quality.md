# Verificação da base local

## Gate para preparação Git — 2026-11-15

Suíte completa fora do sandbox: **412 passed in 34.65s**, exit 0, com
`PYTHONPATH=.venv/Lib/site-packages`, `PYTHONDONTWRITEBYTECODE=1` e
`python -u -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
--basetemp=tests/.tmp-github-gate-20261115`. Ruff: All checks passed, exit 0.
`docker compose config --quiet`: exit 0, valida configuração sem iniciar serviços.
Template `.env.example` restaurado sem credenciais, modelo AD-015 e opções de timeout/
tentativas. `.env` real e artefatos `.tmp-model-probe-20261115/` ignorados pelo Git.
Varredura dos arquivos alterados comparou a chave local sem exibi-la e procurou
padrões de credenciais: nenhuma ocorrência. Sem nova chamada Gemini nesse gate.

## Sondagem real comparativa — 2026-11-15

Executadas 15 chamadas em cinco comprovantes fictícios do piloto com o extrator
real (uma tentativa de até 45 s por modelo/documento). 3.8: 0/5 sucessos; 3.1 Lite:
4/5; 3.5 Lite: 5/5. Relatório completo e limites em
[gemini-model-probe-20261115.md](gemini-model-probe-20261115.md).
Nenhuma modificação no código ou configuração nesta sondagem; não reexecutada suíte
offline. Não confundir resultado exploratório com avaliação final ou decisão de modelo.

## Política Gemini e catálogo — 2026-11-15

Ajustados timeout (120 s por tentativa), máximo de duas tentativas por padrão,
backoff/jitter e auditoria sanitizada por tentativa. SDK sem retry interno no cliente
de produção para evitar multiplicação. Parâmetros configuráveis e limitados; temperatura
omitida em Gemini 3+ e registrada como null/default, sem alterar modelo ou thinking.
Contrato e limites operacionais em ARCHITECTURE.

Suíte offline fora do sandbox: `python -u -m pytest -q -p no:cacheprovider
-o faulthandler_timeout=30 --basetemp=tests/.tmp-gemini-policy` (PYTHONPATH da .venv)
→ **412 passed in 29.03s**; Ruff aprovado. Regressões novas: política por modelo,
retentativa de 503/504 com sucesso posterior, ausência de retry para 400/403,
sanitização e opções do cliente.

Consulta real `client.models.list()` com chave local retornou modelos de geração,
incluindo 2.5 Flash/Pro/Flash-Lite, 3.1 Flash-Lite, 3.5 Flash/Flash-Lite,
3.6/3.7/3.8 Flash e 4 Argon/Carbon/Hydrogen, além de modelos especializados.
Catálogo não confirma cota, gratuidade ou geração operacional de cada modelo.
Consulta `models.get` de 3.8 Flash confirmou suporte a generateContent.
Teste mínimo de texto sem PDF/schema/temperatura, timeout 120 s e duas tentativas,
terminou com 504 DEADLINE_EXCEEDED; não houve geração bem-sucedida. Não migrado para
Interactions nem testado esse endpoint; nenhum novo pacote instalado. Sem commit/push.

## Primeiro teste real Gemini — 2026-11-15

Usuário configurou chave local e autorizou teste com comprovante fictício. PDF raster
gerado em memória pela stdlib, sem documentos pessoais. Modelo configurado:
`gemini-3.8-flash`; SDK instalado `google-genai 3.3.0`; prompt `entities-v2`.
Credencial não exibida ou salva em relatórios. Execução fora do sandbox após
ConnectError no ambiente restrito; nenhuma instalação ou mudança do modelo.

- Duas chamadas reais rejeitadas com 400 INVALID_ARGUMENT:
  `Unknown name "additional_properties" at generation_config.response_schema`.
  O caminho legado `response_schema=ExtractionPayload` convertia o schema para
  formato incompatível com o endpoint. Corrigido para
  `response_json_schema=ExtractionPayload.model_json_schema()`, preservando
  `additionalProperties: false` e validação Pydantic local.
- Regressão com SDK real + `httpx.MockTransport` inspeciona o JSON efetivamente
  enviado (`responseJsonSchema`, sem `responseSchema`), sem rede/credencial real.
- Após correção: chamada com timeout de 30 s retornou 504 DEADLINE_EXCEEDED em
  ~28,6 s; última tentativa com timeout de 90 s retornou 503 UNAVAILABLE em
  ~12,7 s. Sem retentativas automáticas. Nenhuma entidade, versão de modelo ou
  contagem de tokens retornada. Não houve extração bem-sucedida nem avaliação de
  precisão; não é possível inferir custo zero ou acesso definitivo só desses erros.

Gate backend fora do sandbox, com `PYTHONPATH=.venv/Lib/site-packages` e
`PYTHONDONTWRITEBYTECODE=1`, de `comprova-lattes-api/`:

```powershell
python -u -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30 --basetemp=tests/.tmp-gemini-json-schema-20261115
python -m ruff check . --no-cache
```

**404 passed in 22.05s**, exit 0; Ruff e `git diff --check` aprovados.
Sem PostgreSQL/Redis, commit ou push. Serviços reais seguem parcialmente verificados:
requisição alcança Google, mas sucesso de extração permanece pendente.

## Investigação do travamento da suíte — 2026-11-15

Diagnóstico confirmado por comparação do mesmo comando dentro/fora do sandbox:
`socket.socketpair()` do Python 3.14 trava em `socket._fallback_socketpair → accept`
no sandbox e conclui fora dele (exit 0). O stack de `faulthandler` do primeiro teste
HTTP mostrou `TestClient.__enter__ → AnyIO → asyncio.ProactorEventLoop →
_make_self_pipe → socketpair`. O bloqueio ocorre na preparação do loop, antes de
atender requisições da aplicação. Não foi necessário mudar código, dependências,
backend assíncrono ou expectativas dos testes.

Os 20 testes de `test_experiments.py` também passaram dentro do sandbox em 14,76 s,
com temporários em `tests/.tmp-investigation-20261115`; não foi reproduzido um
problema de temporários nessa execução. Uma coleta interrompida por watchdog de
10 segundos ainda estava importando dependências: silêncio durante coleta, por si
só, não prova travamento.

Gate completo executado **fora do sandbox**, de `comprova-lattes-api/`:

```powershell
$env:PYTHONPATH = '.venv/Lib/site-packages'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -u -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30 --basetemp=tests/.tmp-investigation-full-20261115
```

Resultado: **403 passed in 32.44s**, exit 0. Inclui os sete novos casos AD-014,
API com SQLite em memória, transportes simulados e experimentos. Dentro do sandbox,
`python -m ruff check . --no-cache` e `git diff --check` também passaram, exit 0.
Sem chamadas ao Gemini, PostgreSQL/Redis, instalações ou alterações no código nesta
investigação. O gate completo substitui a limitação de verificação da rodada AD-014
abaixo; não comprova integração com os serviços reais. Para este executor, repetir
os testes HTTP em ambiente que permita conexões locais de loopback.

## AD-014 — relação institucional documental (2026-11-15)

Contrato `entities-v2` com trecho explícito nome/sigla; equivalência local ao
documento, dicionário fixo preservado, sigla isolada desconhecida inconclusiva.
De `comprova-lattes-api/`, com `PYTHONPATH=.venv/Lib/site-packages` e
`PYTHONDONTWRITEBYTECODE=1`, dependências existentes, sem instalação:

- `python -u -m pytest -q -p no:cacheprovider tests/test_extractor.py tests/test_matcher.py tests/test_extractor_matcher.py tests/test_matcher_assignment.py tests/test_matcher_text.py`
  → **195 passed in 5.47s**, exit 0.
- `python -m ruff check . --no-cache` → **All checks passed**, exit 0.
- `git diff --check` → exit 0.

Suíte completa e tentativas ampliadas não finalizaram e foram interrompidas
(exit 1, sem diagnóstico conclusivo de causa). Não há gate completo aprovado
nesta rodada; não atribuir esses bloqueios ao código ou ambiente sem investigação.
Sem Gemini real, PostgreSQL/Redis, alterações de dependências, commit ou push.
Regressões cobrem transporte do trecho, relação incompleta, tokens de sigla,
UNREADABLE, escopo por documento, baselines e nome declarado contraditório.


## S2 - ORGANIZACAO_EVENTO corrigido (2026-11-13)

Correcao autorizada: event_name=None torna evento NOT_APPLICABLE com regra
STRUCTURAL_NOT_APPLICABLE; titulo passa a essencial mesmo se ausente.
Com evento preenchido, preservado o comportamento anterior. Regressao cobre
evento documental presente/ausente e titulo documental ausente. Testes
existentes preservados, inclusive os casos pilot/final de experiments.

Gate completo: **396 passed em 24,09 s, exit 0**. Da API:

```powershell
python -B -u -c "import sys, tempfile, uuid; sys.path.insert(0, '.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=' + tempfile.gettempdir() + '/comprova-org-' + uuid.uuid4().hex]))"
.\.venv\Scripts\ruff.exe check . --no-cache
```

Ruff: All checks passed, exit 0, com aviso de acesso negado na descoberta.
Da app: npm run lint e npm run build, ambos exit 0; build com 140 modulos.
Primeira rodada direcionada: 119 passed e um erro de setup por permissao no
TEMP padrao do pytest; suite completa com basetemp exclusivo no TEMP passou.
Sem pacotes novos, commit/push, dados reais ou servicos externos. DTD,
integracao real e estudo oficial continuam pendentes. Escrita de fontes apenas
nos seis alvos autorizados; temporarios/build sao artefatos dos checks.

O bloqueio relatado abaixo e historico e foi resolvido nesta continuacao.

## Auditoria S2 — 2026-11-13

Implementados nos alvos autorizados: subnós XML de eventos/produção técnica,
papel APRESENTADOR no gabarito, siglas por emissor e edição ASCII leve, mutações
40→45/400 horas, ano +7, titular e instituição; exemplo operacional explícito,
upload incremental/limpeza e ressincronização da revisão humana. Links da raiz
corrigidos e documentação reconciliada. Alterações preexistentes preservadas.

Gate completo executado nesta rodada (dependências existentes, sem instalação):

| Diretório | Comando | Resultado observado |
| --- | --- | --- |
| API | `python -m pytest -q -p no:cacheprovider --basetemp=$env:TEMP/comprova-s2-final` | 392 passaram, 2 falharam; exit 1 |
| API | `python -m ruff check .` | All checks passed; exit 0; aviso de acesso negado ao cache |
| App | `npm run lint` | exit 0 |
| App | `npm run build` | exit 0; TypeScript + Vite, 140 módulos |

Backend usa Python global com `$env:PYTHONPATH = '.venv/Lib/site-packages'`
e `PYTHONDONTWRITEBYTECODE=1` na suíte completa, sem depender do launcher uv.
Temporários ficam no TEMP do sistema. Smoke Node/Vite em memória: template com
limiares nulos rejeitado e exemplo operacional aceito pelo parser de configuração.
Smoke adicional dos handlers reais dos componentes, transpilados em memória com
hooks simulados: anexação incremental, deduplicação, limpeza e reabertura da
revisão com parecer/rejeições atualizados e associação humana nula passaram.
Lint/build e smoke não substituem interação em navegador ou integração real.

**Bloqueio de escopo:** os dois testes novos de veredictos (piloto/final) expõem
`ORGANIZACAO_EVENTO` identity/legitimate como INCONCLUSIVO: parser preserva
`event_name=None`, mas `matcher/rules.py:essential_fields` exige `evento` para
essa categoria. S2 proíbe escrita em matcher/. Correção mínima recomendada:
exigir evento apenas nas categorias que possuem esse campo aplicável, mantendo
título/papel/ano/titular e evidências. Ampliação de escopo solicitada; pendente
de autorização. Não foram alterados matcher/parser/extractor/api, gabaritos
não foram ajustados para mascarar a falha e o aceite integral S2 não foi atingido.

Gates históricos abaixo permanecem como histórico: não comprovam calibração,
anotação humana independente, DTD oficial ou execução dos estudos. Não foram
iniciados PostgreSQL/Redis/worker, usados dados pessoais, nem chamados Gemini
ou Tesseract reais. Compose/XSD não foram revalidados nesta rodada.

## Atualização M1 — 2026-11-13

- Expectativa de `validation_code` corrigida com aprovação: código CAPES permanece na proveniência, não como autenticação documental.
- Gate atual independente, Python 3.14 local: **130 testes e Ruff aprovados**. Seis fixtures conformes/técnicas aprovadas contra XSD offline; detalhes e hashes em [m1-linux-verification.md](m1-linux-verification.md).
- Linux/Python 3.12: gate histórico independente de 92 testes; relatório final Hydrogen informa 130 testes e Ruff após ampliação. O revisor confirmou 130 testes localmente; não repetiu o gate Linux ampliado.
- Ruff no bind mount Windows inicialmente reportou 18 ocorrências `EXE002`. Repetição em cópia temporária Linux com permissões corretas passou, assim como os 92 testes; nenhuma regra foi desabilitada. Ver `m1-linux-verification.md`.
- Conformidade DTD continua pendente. Aprovação dos testes de parsing não comprova conformidade oficial.

## Histórico do setup — 2026-11-12

As evidências abaixo correspondem ao setup inicial, não ao estado atual do M1.

## Ambiente

- Backend: ambiente virtual local `comprova-lattes-api/.venv`, Python 3.14.0; dependências instaladas com `python -m pip install -e ".[dev]"`.
- Dockerfile usa Python 3.12; compatibilidade nessa imagem ainda não foi testada nesta rodada.
- Frontend: dependências locais existentes, sem atualização de pacotes.

## Evidências

| Diretório | Comando | Resultado |
| --- | --- | --- |
| `comprova-lattes-api` | `.venv/Scripts/python.exe -m pytest -q` | 1 teste passou (`/health`) |
| `comprova-lattes-api` | `.venv/Scripts/python.exe -m ruff check .` | Passou |
| `comprova-lattes-api` | `.venv/Scripts/python.exe -m pip check` | Sem dependências quebradas |
| `comprova-lattes-api` | `docker compose config --quiet` | Passou; valida somente configuração |
| `comprova-lattes-app` | `npm run lint` | Passou |
| `comprova-lattes-app` | `npm run build` | Passou, incluindo compilação TypeScript |

## Limites e próximos checks

- Não foram iniciados PostgreSQL, Redis ou worker; conexões e tarefa Celery não foram testadas.
- Não houve chamada ao Gemini, uso de certificados ou teste visual do frontend.
- Na rodada histórica havia somente o healthcheck. O estado atual M1–M6 e o bloqueio S2 estão descritos no topo; os resultados históricos não comprovam integração real nem atendimento da exigência DTD.
- Instalação Python inicial concluiu com sucesso. Uma tentativa sobreposta encontrou `WinError 32`; verificações acima foram repetidas após conclusão da instalação original.
- Ambiente usa versões resolvidas a partir de limites abertos em `pyproject.toml`; lockfile e padronização do Python continuam decisões pendentes antes dos experimentos reproduzíveis.
- Referências legadas em `references/legacy-drive/` não pertencem ao código ativo nem aos gates descritos aqui.

## Gate pré-publicação — 2026-11-13

Reexecutados no backend: `python -m pytest -q` com a `.venv` → **130 passed in 1.64s**; `python -m ruff check .` → **All checks passed**; `docker compose config --quiet` → exit 0. Sem alteração de dependências/código nesta reconciliação. Frontend alterado somente no README; lint/build do frontend não foram repetidos. Esses gates não comprovam serviços iniciados nem conclusão integral do M1.
