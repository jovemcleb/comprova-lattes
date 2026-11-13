# Verificação M1 — evidências por ambiente (2026-11-13)

## Gate histórico Linux (antes da ampliação)

- Imagem local: `comprova-lattes-api:m1-check`, baseada em Python 3.12-slim.
- Container descartável (`docker run --rm`), sem PostgreSQL, Redis ou Gemini.
- `src`, `tests` e `pyproject.toml` montados em `/input` somente leitura e copiados para `/tmp/m1check` no container. Apenas essa cópia recebeu permissões 0644 para arquivos e 0755 para diretórios; nenhum arquivo do host foi alterado.
- Ferramentas pytest/httpx/Ruff instaladas somente no container temporário.
- Comandos na cópia: `PYTHONPATH=/tmp/m1check/src python -m pytest -q -p no:cacheprovider` e `ruff check --no-cache src tests`.
- Resultado observado: **92 passed in 0.84s**, **All checks passed**, exit code 0.
- A falha anterior EXE002 não se reproduziu com permissões Linux corretas. Nenhuma regra foi desabilitada.
- Valida o código atual copiado para o container, não prova conformidade DTD nem serviço de banco/fila, e não congela versões de dependências.

## Revisão independente após ampliação AD-012

- Windows/Python 3.14, no diretório `comprova-lattes-api/`: `.\.venv\Scripts\python.exe -m pytest -q` → **130 passed in 1.31s**; `.\.venv\Scripts\python.exe -m ruff check .` → **All checks passed!**. Execução pelo revisor, sem mudanças de código posteriores nesta reconciliação.
- XSD: seis XMLs (quatro em `m1-conformant/` e dois em `m1-technical/`) aprovados independentemente via `lxml.etree.XMLSchema.assertValid`. Imagem existente `grammar-lxml-scratch:tmp`, `docker run --rm -i --network none --read-only`, gramáticas e fixtures montadas somente leitura. Parser com `resolve_entities=False`, `no_network=True`, `load_dtd=False`, `dtd_validation=False`, `attribute_defaults=False`, `huge_tree=False`; entradas sem DOCTYPE/ENTITY. Sem dependências novas no host.
- SHA-256 observados: `acentuacao_campos_opcionais` = `a2787066701cec7ad8c49443b7722aed7fea2965c72dc7e7a8c364391d9aeb1b`; `carga_fracionaria` = `9dc430d21f2ba915562883b54f7f316d39f1135ab34cb8c18c7debd26300ada5`; `completo` = `098e737c12a0295d9f0fb22dadb6819c33421cfea7b6aae507f5ab192aed01de`; `eventos_subnos` = `4ec13e23f9e37c6c6a86919c05314940d27b7513ae258683a2c8aa480858a889`; técnico `ausencias_e_acentuacao` = `674d3cd5fdef395dd1810f7ead41708b42ffabb754426079fefff4b0628f6a44`; técnico `producao_completa` = `9653f6df970ee0bebf571f85a8b77da5969791ec1d904eaa3272bb2054127795`.

## Evidência Linux relatada pelo Hydrogen

Relatório final recuperado no histórico da sessão `ba572676-15ee-4cfc-8ed5-67a4b1730392`, resposta 136. A ponte havia coletado uma resposta intermediária. O worker relata Python **3.12.16**, **130 passed in 1.38s** e Ruff **All checks passed**, com os comandos Linux históricos acima em cópia temporária. O revisor não repetiu esse gate Linux: a imagem disponível não contém pytest/Ruff. Isso não invalida o relato, mas distingue sua origem do gate local independente.

## Limites da revisão

Leitura dos contratos, mapeamentos, caminho técnico do parser, parsing seguro e novos testes não identificou bloqueio de segurança na ampliação examinada. A suíte aprovada não prova cobertura exaustiva nem validação de gramática em runtime. `ORGANIZADOR` é derivado estruturalmente de `ORGANIZACAO-DE-EVENTO`, inclusive para outras naturezas preservadas em `nature_raw`; equivalências de papéis e essencialidade do M2 continuam pendentes. Valores canônicos removem espaços externos, mas a proveniência preserva atributos originais. `record_id` é opcional e não é preenchido pelo parser atual; não há comprovação de IDs estáveis gerados pelo M1.

Conformidade ao XSD do Extrator não encerra o requisito DTD do professor nem comprova equivalência com XML exportado pela interface. Qualquer uso de XML real exige autorização específica. Sem commit/push/deploy.
