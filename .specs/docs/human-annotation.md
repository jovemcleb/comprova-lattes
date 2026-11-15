# Interface Local de Revisão Humana (`/revisao-experimental`), Pacote de Anotação e Auxílio OCR Local

## Testar em outra máquina — Elivanilso (ensaio de cinco casos)

Pré-requisitos: Git, Node/npm compatíveis com o frontend existente e Docker Desktop
com Linux containers. Não precisa de chave Gemini para esta revisão.

```powershell
git clone https://github.com/jovemcleb/comprova-lattes.git
cd comprova-lattes
# Se já tiver clonado: conferir trabalho local antes de git pull --ff-only.
docker compose -f comprova-lattes-api/compose.yaml up --build -d ocr
npm --prefix comprova-lattes-app ci
npm --prefix comprova-lattes-app run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abra http://127.0.0.1:5173/revisao-experimental. O OCR responde em
http://127.0.0.1:8766/health. A página pode indicar API principal indisponível;
isso não impede o ensaio offline de anotação.

Caleb deve enviar separadamente SOMENTE `pacote-anotacao-piloto-legivel.json`
(pacote público sanitizado). Não enviar corpus/gold/mapa privado, respostas pessoais
ou conversa de orientação sobre casos. O pacote local ignorado não está no GitHub.
Para testar os mesmos casos, use o MESMO arquivo, não regenere em outro ambiente:
versões de rasterização podem mudar os bytes e o hash.

Informe “Elivanilso — ensaio” e escolha explicitamente manual ou assistido. Primeiro
anote o documento; depois compare com o currículo. Conclua cada caso. Anterior/Próximo
ficam no fim; a exportação final aparece somente com todos os casos completos.
Backup/importação de rascunho ficam recolhidos durante o preenchimento. Cada revisor
usa seu próprio computador/perfil e exporta somente suas respostas.

Este teste não inicia as150avaliações oficiais nem aprova templates/guia. Rodada de
Caleb discutida no chat foi ensaio orientado; não computar como independente oficial.
ModoOCR gera anotação assistida e pode influenciar a comparação com baseline; o uso
na análise oficial continua pendente. A instalação pelo container usa TesseractLinux,
que pode produzir texto diferente de instalaçõesWindows; registre o ambiente usado.

Se quiser iniciar todo o backend (não necessário ao ensaio):
`docker compose -f comprova-lattes-api/compose.yaml up --build -d`.


## Objetivo e escopo

Esta entrega implementa o fluxo local de anotação humana dos casos sintéticos do piloto: exportador
offline de um **pacote sanitizado** (`experiments/annotation_package.py`, versão
`annotation-package-v1` preservada com hashes idênticos), página React `/revisao-experimental` e
**serviço HTTP local independente de auxílio OCR** (`experiments/review_ocr.py`, `127.0.0.1:8766`).

Escopo desta etapa:

- **Somente partição piloto, 5 casos** (uma categoria cada, operadores variados, famílias distintas).
  O código comporta mais casos na interface (limite de 500 por pacote), mas o exportador **não gera
  150 cenários, não gera corpus final, não executa 150 leituras OCR e não executa
  generate/calibrate/freeze/API/Gemini**.
- **Sem consenso e sem Kappa.** Rascunho, exportação final e arquivos de revisores diferentes ficam
  separados; consenso será terceiro arquivo, em etapa futura.
- **Auxílio OCR opcional (opt-in explícito):** o botão `Ler com OCR` na Fase 1 exibe o texto bruto
  reconhecido pelo `TesseractOCR` separado dos valores recortados por `OCRRegex`, mantendo o
  comprovante visível ao lado e sem preenchimento automático nem exposição de XML, `gold`,
  `expected` ou extrações Gemini. Sem o servidor OCR ativo, a revisão manual permanece 100%
  operacional.
- Estado: ferramenta de ensaio do piloto. **Não é revisão humana executada, nem aprovação do guia,
  nem aprovação dos templates, nem autorização para executar os estudos oficiais.**

## Alteração da condição metodológica e risco de viés pró-baseline (`TesseractOCR` + `OCRRegex`)

- **Revisão assistida vs. anotação independente sem auxílio:** acionar ou exibir o auxílio OCR antes
  da conclusão de um caso (`assisted_before_completion: true`) caracteriza **revisão humana
  assistida** (`evaluation_condition: "ocr_assisted_human_review"`), e **não** anotação humana
  independente sem auxílio (`"independent_unassisted_human_review"`). Não se deve relatar revisão
  assistida por OCR como se fosse rotulagem humana estritamente independente.
- **Risco de viés pró-baseline (circularidade com o Baseline Clássico):** o auxílio na interface
  reutiliza exatamente a mesma pilha do baseline clássico avaliado no Experimento 1 (`TesseractOCR` +
  `OCRRegex`). Se o revisor copiar acriticamente textos ou campos recortados pelo OCR/RegEx sem
  conferência visual direta no comprovante, erros de reconhecimento ou omissões de expressão regular
  do próprio Tesseract/RegEx podem contaminar o parecer humano e inflar artificialmente a
  concordância ou o desempenho aparente do baseline clássico frente ao extrator avaliado.
- **Saída do OCR nunca é gabarito:**
  - Nenhum campo é preenchido automaticamente ao clicar em `Ler com OCR`.
  - Campos não capturados por `OCRRegex` aparecem como `null` (*"Não extraído pela RegEx"*) e
    **jamais** são marcados automaticamente como `Ausente` (`absent`) nem como `Ilegível`.
  - Quando o revisor opta por usar ou copiar um valor sugerido pelo OCR em um campo, deve conferir
    visualmente o comprovante, podendo editar livremente o texto ou clicar em
    **Rejeitar / limpar valor deste campo** (o que limpa o campo mantendo o histórico auditável de
    que o OCR foi consultado).
- **Decisão pendente para a análise oficial:** a decisão metodológica sobre como contabilizar,
  estratificar ou separar anotações assistidas por OCR (`ocr_assisted_human_review`) na análise
  oficial da monografia **permanece pendente de deliberação explícita do usuário/orientador** e não
  autoriza automaticamente a execução dos experimentos finais.

## Como subir e verificar o serviço local de auxílio OCR (`review_ocr`)

O serviço `review_ocr` é um processo FastAPI/uvicorn local, offline e independente da API principal:
não carrega `Settings`/`.env`, não conecta a PostgreSQL ou Redis/Celery e nunca chama Gemini.

1. **Inspecionar disponibilidade do Tesseract, idioma `por` e limites (sem abrir servidor):**

   ```powershell
   Set-Location comprova-lattes-api
   python -m comprova_lattes.experiments.review_ocr --check
   ```

2. **Subir o servidor local em loopback (`127.0.0.1:8766`):**

   ```powershell
   Set-Location comprova-lattes-api
   python -m comprova_lattes.experiments.review_ocr --host 127.0.0.1 --port 8766 --dpi 300 --lang por
   ```

   - **Restrições de rede e segurança:**
     - Faz bind exclusivamente em loopback (`127.0.0.1` ou `localhost`; rejeita `0.0.0.0` ou IPs
       externos tanto na CLI quanto no cabeçalho HTTP `Host`).
     - CORS restrito a `http://127.0.0.1:5173`, `http://localhost:5173`, `http://127.0.0.1:4173` e
       `http://localhost:4173`; origens diversas recebem `403 FORBIDDEN_ORIGIN`.
     - Concorrência limitada por semáforo (`--max-concurrency 1` por padrão; requisições simultâneas
       excedentes recebem `429 OCR_CONCURRENCY_LIMIT`).
     - Limite de payload verificado **antes** da decodificação base64 (`content_base64` e
       `Content-Length`), limite de páginas PDF (`--max-pdf-pages 10`), limite de dimensões de
       imagem (`--max-image-pixels 25000000`) e timeout por subprocesso (`--timeout 30`).
   - **Conferência de `base64`/`sha256` e proteção contra troca de resposta:**
     - O endpoint `POST http://127.0.0.1:8766/ocr` aceita **exclusivamente** `{ document_id,
       mime_type, sha256, content_base64 }`. Qualquer chave de XML, `record`, `gold`, `expected` ou
       metadados do corpus é rejeitada com `422 FORBIDDEN_PAYLOAD_FIELDS`.
     - O servidor decodifica o `content_base64`, verifica a assinatura binária (`%PDF-`, PNG, JPEG),
       recalcula o SHA-256 dos bytes e rejeita divergências com `422 SHA256_MISMATCH`.
     - A resposta ecoa `document_id`, `mime_type` e `sha256`; o navegador valida novamente esses
       três campos contra o comprovante aberto antes de exibir o painel ou atualizar o caso,
       descartando qualquer resposta trocada ou atrasada sem ocultar nem alterar o XML ou os hashes
       base do pacote.
   - **Comportamento offline (sem servidor OCR) e custo de execução:**
     - Se o serviço `review_ocr` estiver desligado, se o binário `tesseract` ou `por.traineddata`
       estiver ausente (`503`) ou se ocorrer timeout (`504`), a interface exibe a mensagem clara do
       erro e **não bloqueia** a transcrição manual nem o salvamento das Fases 1 e 2.
     - **Custo operacional:** cada clique em `Ler com OCR` rasteriza o PDF/imagem localmente (via
       `pypdfium2` + `Pillow` a 300 DPI por padrão) e invoca um subprocesso local do Tesseract
       (~0,3 s a ~2 s por página em CPU local, sem custo financeiro de API e sem tráfego externo).

## Fluxo operacional na interface (`/revisao-experimental`)

1. **Gerar o pacote** (preparador, a partir de `comprova-lattes-api/`, com um Corpus já existente
   indicado explicitamente):

   ```powershell
   python -m comprova_lattes.experiments.annotation_package `
     --corpus caminho/corpus.json `
     --output caminho/pacote-anotacao.json `
     [--private-map caminho/mapa-privado.json] [--guide-version operational-guide-draft-v1] [--overwrite]
   ```

2. **Importar** o pacote em `/revisao-experimental`. O navegador valida esquema/tipos, rejeita Corpus
   bruto e chaves proibidas, confere MIME, SHA-256 de cada documento/XML e o `package_sha256`.
3. **Declarar o revisor e o modo de revisão (`unassisted` vs. `ocr_assisted`):**
   - `unassisted` (padrão): revisão manual sem auxílio (`independent_unassisted_human_review`).
   - `ocr_assisted` (opt-in): revisão assistida por OCR (`ocr_assisted_human_review`).
   - O `localStorage` armazena rascunhos em slots separados por `(package_sha256, reviewer,
     review_mode)`. Caso o revisor inicie em modo `unassisted` e decida ativar `Ler com OCR` durante
     a Fase 1, a interface exige confirmação explícita de opt-in e preserva o rascunho `unassisted`
     anterior separado antes de promover a sessão ativa para `ocr_assisted`.
4. **Por caso, duas fases:**
   - **Fase 1 – documento.** Ver o comprovante e transcrever os 11 campos (`present`, `absent` ou
     `illegible`). Se desejar, clicar em **Ler com OCR (opt-in)** para abrir o painel com:
     1. *Texto bruto reconhecido pelo Tesseract (`TesseractOCR`)* e botão `Copiar texto bruto`;
     2. *Valores recortados por expressão regular (`OCRRegex`)* separados do texto bruto, com botões
        por campo (`Usar no campo` ou `Copiar valor`) apenas onde houve captura e aviso explícito de
        *Não extraído pela RegEx* onde o valor é `null`.
   - **Fase 2 – comparação**, liberada somente após salvar a Fase 1: registro XML estruturado e XML
     original ao lado do comprovante, resumo travado da Fase 1 (com indicação de rastreabilidade OCR
     se acionado) e julgamento de associação, classe e motivo.
5. **Exportar e importar rascunhos/finais (`annotation-export-v2` + compatibilidade `v1`):**
   - A exportação gera `export_version = "annotation-export-v2"`, contendo `review_mode`,
     `evaluation_condition`, `mode_opted_in_at`, `migrated_from_export_version`, `methodology_note`
     e, em cada caso, `ocr_assistance` completo (`status`, `assisted_before_completion`,
     `requested_count`, `first_requested_at`, `last_accessed_at`, `last_error`, `document_id`,
     `document_mime_type`, `document_sha256`, `provider`, `tesseract_version`, `params`,
     `ocr_raw_text`, `regex_fields`, `observable_copied_raw_text`, `observable_copied_fields`,
     `observable_copy_events`, `observability_limit_note`).
   - **Limite de observabilidade:** o JSON registra apenas cliques explícitos nos botões do painel
     OCR (`Copiar texto bruto`, `Usar no campo`, `Copiar valor`); não alega detectar digitação
     manual, leitura visual do painel nem seleção livre com atalhos do sistema (`Ctrl+C`).
   - **Compatibilidade retroativa e bloqueio de mistura silenciosa:** arquivos antigos
     `annotation-export-v1` continuam 100% importáveis (com verificação do `annotation_sha256`
     original de `v1` e migração clara para `review_mode: "unassisted"`,
     `migrated_from_export_version: "annotation-export-v1"`). Por padrão, importar um arquivo
     `ocr_assisted` em uma sessão `unassisted` (ou vice-versa) é bloqueado até que o revisor
     confirme explicitamente a alternância de modo, preservando o rascunho anterior separado.

## Formato do pacote público (`annotation-package-v1` — inalterado)

```text
package_version, guide_version, package_sha256, cases[]:
  case_id          neutro: case-001, case-002… (ordem embaralhada de forma determinística)
  document         null | { mime_type, sha256, content_base64 }
  xml              { sha256, content_base64 }          # XML original
  record           registro curricular estruturado (categoria, titular, instituição, título,
                   evento, papel, anos, carga horária como texto decimal, situação, etc.)
```

## Arquivos

- Backend: `comprova-lattes-api/src/comprova_lattes/experiments/annotation_package.py`,
  `comprova-lattes-api/src/comprova_lattes/experiments/review_ocr.py`, testes em
  `comprova-lattes-api/tests/test_annotation_package.py` e
  `comprova-lattes-api/tests/test_review_ocr.py`.
- Frontend: `comprova-lattes-app/src/lib/annotation/` (`canonical.ts`, `package.ts`, `ocr.ts`,
  `draft.ts`), `comprova-lattes-app/src/components/annotation/` (`OcrAssistPanel.tsx`,
  `DocumentPhase.tsx`, `ComparisonPhase.tsx`, `ReviewerGate.tsx`, `DraftControls.tsx`,
  `CaseList.tsx`, `annotation.css`), `comprova-lattes-app/src/pages/ExperimentalReviewPage.tsx`.


## Clareza do fluxo — atualização de UX (2026-11-15)

Etapa1 agora pergunta “O que está no comprovante?” e traz orientações por campo,
especialmente atividade específica versus cabeçalho e ano da atividade versus
início/conclusão. Etapa2 apresenta Campo / Sua transcrição / Declarado no currículo
em uma tabela, sem calcular igualdade, sugerir classe ou alterar respostas. Campos
sem correspondente direto no XML são identificados, sem derivação silenciosa de anos.
XML bruto,IDs e rastreabilidade OCR permanecem nos detalhes técnicos recolhidos.
Comprovante pode abrir em nova guia, com download preservado. Formato de rascunhos,
JSONs e hashes não mudou; reabrir etapa1 mantém registro de exposição aoXML.
Orientação mudou durante ensaio: reavaliar os5piloto comguia aprovado antes de
computar concordância oficial. Nenhuma resposta humana foi corrigida automaticamente.
Validação: lint/build frontend aprovados; navegador de teste com revisorUX-check-local,
11linhas na comparação,fontes em colunas e detalhes/XML recolhidos. Anotações desse
revisor são simulação de interface,não dados humanos experimentais.


## Navegação e entrega — atualização de UX (2026-11-15)

Anterior/Próximo ficam no fim do caso, após o formulário. Salvar a avaliação de cada
caso continua necessário para validar as respostas. Exportar avaliação final só é
exibido quando incompleteCases confirma todos os casos completos, não apenas pela
posição no último caso. Backup/importação de rascunho seguem disponíveis em bloco
recolhido; se salvamento local falhar, bloco abre com aviso. Dados e formatos não
mudaram. Lint/build aprovados; estados incompleto/completo conferidos no navegador
com respostas simuladas no revisor Navigation-QA, sem usar respostas humanas.


## Inicialização com Docker Compose

Na pasta comprova-lattes-api, `docker compose up --build -d` inclui o serviço `ocr`
(Tesseract português), acessível em127.0.0.1:8766. Não precisa iniciar review_ocr
em terminal separado. Se houver serviço Python antigo na mesma porta, parar com
Ctrl+C antes. Para usar apenas revisão, `docker compose up --build -d ocr` basta,
além do frontend. Modo assistido continua opt-in e rastreado, não gabarito independente.
