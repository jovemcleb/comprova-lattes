# Verificação da base local

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
- Na rodada histórica havia somente o healthcheck. Atualmente schemas/parser estão implementados e testados; matcher, extrator e experimentos continuam planejados. Testes não comprovam integração com serviços nem atendimento da exigência DTD.
- Instalação Python inicial concluiu com sucesso. Uma tentativa sobreposta encontrou `WinError 32`; verificações acima foram repetidas após conclusão da instalação original.
- Ambiente usa versões resolvidas a partir de limites abertos em `pyproject.toml`; lockfile e padronização do Python continuam decisões pendentes antes dos experimentos reproduzíveis.
- Referências legadas em `references/legacy-drive/` não pertencem ao código ativo nem aos gates descritos aqui.

## Gate pré-publicação — 2026-11-13

Reexecutados no backend: `python -m pytest -q` com a `.venv` → **130 passed in 1.64s**; `python -m ruff check .` → **All checks passed**; `docker compose config --quiet` → exit 0. Sem alteração de dependências/código nesta reconciliação. Frontend alterado somente no README; lint/build do frontend não foram repetidos. Esses gates não comprovam serviços iniciados nem conclusão integral do M1.
