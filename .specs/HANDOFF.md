# Handoff — Comprova Lattes

**Data:** 2026-11-13
**Foco:** revisão técnica da ampliação M1 realizada; concluir decisões por categoria antes de implementar M2. M1 permanece aberto pelo requisito DTD do professor.

## Ler primeiro

`AGENTS.md`, `.specs/project/{PROJECT,ROADMAP,STATE}.md`. Requisitos: `.specs/codebase/PROFESSOR-REQUIREMENTS.md`; fonte: `docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md`. Perguntar antes de decisões materiais. Preservar diffs; sem commit/push, chamadas pagas ou uso experimental de documentos pessoais.

## Entregas e verificação

- M1: cinco categorias, parser seguro (`defusedxml`), UTF-8/ISO-8859-1, limites de tamanho/profundidade, proveniência. Carga inválida vira `None` com diagnóstico; frações em `Decimal`. `record_id` é opcional e não é gerado pelo parser: relato anterior de IDs estáveis não estava sustentado.
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
- Essencialidade, título omitido no comprovante e coexistência de papéis ainda precisam de decisão. Ouvinte não implica exclusão de apresentação/organização no mesmo evento. Ausência estrutural de horas não é divergência nem motivo global de inconclusão.
- Unidade formal, distribuição dos 30/~90 casos pelas cinco categorias, famílias/agrupamento, IC/reamostragem, agregação de repetições diferentes e McNemar continuam propostas. Não aplicar integralmente recomendações do Argon sem aprovação.
- Documentos órfãos fora da matriz 3×3; associação avaliada separadamente. Métricas automáticas anteriores à revisão humana. M2 e protocolo não implementados.

## Próximos passos

1. Decidir tabela de essencialidade/agregação por categoria com o usuário, usando exemplos de certificado/declaração, data/local/evento e evidência de atuação.
2. Fechar desenho da bancada e estatística antes de gerar o corpus; manter piloto separado do final e não usar documentos reais sem autorização.
3. Confirmar com orientador a alternativa XSD ao requisito DTD; compatibilidade UI permanece não comprovada.
4. Implementar M2 somente após fechamento dos contratos; API/interface e revisão humana em etapa posterior.

## Workspace

Usuário autorizou commit/push do trabalho acumulado em 2026-11-13 para `jovemcleb/comprova-lattes` (público). Publicação inclui M1, testes sintéticos, documentação e ferramentas próprias. Legado do Drive e cópias locais de gramáticas/metadados de terceiros excluídos por `.gitignore`; licenças ainda pendentes. Referências históricas a caminhos locais não significam que os arquivos estão no clone público. A reconciliação final alterou somente documentação; código do Hydrogen preservado. Gate pré-publicação repetido: 130 testes, Ruff e `docker compose config --quiet` aprovados. Git diff sem erro de whitespace. Para estado efetivo da publicação, consultar Git/remoto, não inferir deste texto. Evidências históricas de 92/105 testes não devem ser confundidas com o gate atual de 130.
