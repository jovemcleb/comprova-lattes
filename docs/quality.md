# Verificação da base local


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
