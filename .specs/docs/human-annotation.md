# Interface Local de Revisão Humana (`/revisao-experimental`) e Pacote de Anotação

## Objetivo e escopo

Esta entrega implementa o fluxo local aprovado para a anotação humana independente dos casos
sintéticos: exportador offline de um **pacote sanitizado** (`experiments/annotation_package.py`) e
página React `/revisao-experimental` que o importa. Escopo desta etapa:

- **Somente partição piloto, 5 casos** (uma categoria cada, operadores variados, famílias distintas).
  O código comporta mais casos na interface (limite de 500 por pacote), mas o exportador **não gera
  150 cenários, não gera corpus final e não executa generate/calibrate/freeze/API**.
- **Sem consenso e sem Kappa.** Rascunho, exportação final e arquivos de revisores diferentes ficam
  separados; consenso será terceiro arquivo, em etapa futura.
- Estado: ferramenta de ensaio do piloto. **Não é revisão humana executada, nem aprovação do guia,
  nem aprovação dos templates.** Anotação feita por agente não substitui os autores.

A interface não usa API, PostgreSQL, Redis nem Gemini. Roda com `npm run dev`/`vite preview` local;
nenhum servidor público é necessário.

## Fluxo operacional

1. **Gerar o pacote** (preparador, a partir de `comprova-lattes-api/`, com um Corpus já existente
   indicado explicitamente):

   ```powershell
   python -m comprova_lattes.experiments.annotation_package `
     --corpus caminho/corpus.json `
     --output caminho/pacote-anotacao.json `
     [--private-map caminho/mapa-privado.json] [--guide-version operational-guide-draft-v1] [--overwrite]
   ```

   - O CLI **não imprime** operadores, classes ou categorias (o preparador pode ser anotador); mostra
     só versão, hash do pacote e quantidade de casos.
   - Recusa sobrescrever sem `--overwrite`. `--private-map` grava o mapa `case_id neutro → case_id
     original` em arquivo **separado**; ele só é necessário para ligar anotações aos gabaritos depois
     da anotação. **Nunca entregue o mapa aos anotadores nem o abra antes de anotar.**
2. **Importar** o pacote em `/revisao-experimental`. O navegador valida esquema/tipos, rejeita Corpus
   bruto e chaves extras ou proibidas, confere MIME (declarado × assinatura dos bytes), SHA-256 de cada
   documento/XML e o hash do pacote. Falhas mostram mensagem clara e nada é exibido.
3. **Declarar o revisor** (nome livre). O progresso é salvo no `localStorage` por (hash do pacote,
   revisor). O pacote não é guardado no navegador: reimporte-o a cada sessão (o hash liga rascunho e pacote).
4. **Por caso, duas fases:**
   - **Fase 1 – documento.** Ver somente o comprovante e transcrever campos em branco. Cada campo
     exige estado explícito *presente* (com valor literal), *ausente* ou *ilegível*; ilegível nunca é
     convertido em ausente/`None`. Sem XML, sem sugestão Gemini/gold/expected, sem pares alheios.
     Caso sem documento: transcrição desativada; o revisor confirma a ausência explicitamente
     (nada é classificado automaticamente).
   - **Fase 2 – comparação**, liberada somente após salvar a fase 1: registro XML legível (e XML
     original em bloco recolhível) ao lado do comprovante. Registrar associação (*sim/não/incerto*),
     classe (*Validado/Divergente/Inconclusivo*), motivo objetivo e nota contextual. A transcrição da
     fase 1 fica travada; reabri-la apaga a fase 2 e incrementa `phase1_reopen_count` (exposição ao XML
     fica auditável). A interface **não preenche** campos com XML/gold/Gemini e não sugere classe.
5. **Exportar** rascunho (a qualquer momento) ou **final** (somente com todos os casos completos e
   válidos). **Importar** rascunho: exige mesmo pacote (hash), mesma versão de guia e **o mesmo revisor
   declarado**; rascunho de outro revisor é rejeitado, nunca exibido.

## Formato do pacote público (`annotation-package-v1`)

```text
package_version, guide_version, package_sha256, cases[]:
  case_id          neutro: case-001, case-002… (ordem embaralhada de forma determinística)
  document         null | { mime_type, sha256, content_base64 }
  xml              { sha256, content_base64 }          # XML original
  record           registro curricular estruturado (categoria, titular, instituição, título,
                   evento, papel, anos, carga horária como texto decimal, situação, etc.)
```

- `package_sha256` = SHA-256 do JSON canônico (chaves ordenadas, separadores compactos, saída ASCII,
  mesmo `canonical` de `experiments/freeze.py`) **sem** o campo `package_sha256`. O browser recalcula
  o mesmo hash. Os JSONs usam apenas strings, `null` e inteiros.
- **Excluídos:** `gold`, `expected`, `operator`, `family_id`, `template_id`, `issuer_id`, partição,
  degradação, seed, `curriculum` bruto, `raw_metadata`, sugestões/confiança do LLM, scores/evidências do
  motor e os `case_id` originais. O exportador falha (`PackageError`) se detectar chave proibida ou
  vazamento de `case_id`/`template_id`/operador/classe esperada no JSON.
- **Limite conhecido:** os valores sintéticos do XML e do documento carregam um sufixo hexadecimal da
  família (`PESSOA FICTICIA <hex>`). Esse texto é o conteúdo comparado e não é removido; ele não
  codifica a classe, mas identifica a família. A presença/ausência de documento e o MIME (PDF/PNG) também
  são visíveis por natureza. O pacote **não** esconde estas pistas estruturais.

## Formato de rascunho/exportação (`annotation-export-v1`)

`export_version`, `kind` (`draft`|`final`), `package_version`, `guide_version`, `package_sha256`,
`reviewer`, `exported_at`, `cases[]` (na ordem do pacote) e `annotation_sha256` (SHA-256 canônico do
restante). Cada caso traz `document_sha256`, `xml_sha256`, `phase1` (`status`, `absence_acknowledged`,
`fields` com `state`+`value`, `saved_at`), `phase2` (`association`, `verdict`, `reason_code`,
`basis_fields`, `note`, `saved_at`) e `phase1_reopen_count`. Respostas A/B originais nunca são
alteradas por esta tela; exportações de revisores distintos são arquivos distintos.

## Rascunho do guia operacional

O guia vigente é **rascunho** (`guide_version` = `operational-guide-draft-v1`) e depende de aprovação
humana. Princípios usados na interface, alinhados a `experimental-protocol/proposal.md`:

- Priorizar critérios objetivos (presença, valores, anos, equivalências previstas no guia), sem copiar
  limiares do motor. Análise contextual exige nota com trecho documental. Sem evidência suficiente:
  **Inconclusivo**.
- Motivos objetivos (por classe): Validado — `CAMPOS_COMPATIVEIS`, `EQUIVALENCIA_EXPLICITA`;
  Divergente — `VALOR_FACTUAL_DIFERENTE` (exige campos); Inconclusivo — `DOCUMENTO_AUSENTE`,
  `CAMPO_ESSENCIAL_AUSENTE`, `CAMPO_ILEGIVEL`, `EVIDENCIA_INSUFICIENTE`; qualquer classe —
  `ANALISE_CONTEXTUAL` (nota ≥ 10 caracteres). Mudar a lista exige novo `guide_version` e, segundo o
  protocolo, reavaliar os cinco casos antes da concordância oficial.
- Regras lógicas aplicadas: associação "sim" é impossível sem documento; motivo `DOCUMENTO_AUSENTE`
  contradiz caso com documento; anos têm quatro dígitos.
- Procedimento de adjudicação/consenso: **não definido aqui**; será descrito antes das anotações oficiais.

## Isolamento, salvamento local e perfis separados: o que **não** é garantido

- Isolamento é **por perfil/navegador e por chave de `localStorage`** (`comprova-lattes:annotation-draft:v1:<package_sha256>:<reviewer>`).
  **Não é autenticação forte**: quem usa o mesmo perfil pode abrir, sobrescrever ou apagar dados de qualquer
  revisor no DevTools ou digitando o nome dele.
- **Passos para perfis separados (quando os dois revisores usarem a mesma máquina):**
  1. Crie um perfil dedicado do navegador para cada revisor (ex.: Chrome/Edge → menu do perfil no canto superior direito → *Adicionar novo perfil*; Firefox → `about:profiles` → *Criar um novo perfil*) ou use contas de usuário distintas do sistema operacional.
  2. Entregue aos revisores apenas o arquivo público `pacote-anotacao.json` (nunca o `corpus.json` nem o `--private-map`).
  3. Ao encerrar cada sessão, clique em **Exportar rascunho (JSON)** (ou **Exportar final validado (JSON)** quando concluir os 5 casos) e salve o arquivo em pasta individual do revisor (`anotacao-<revisor>-<hash>-draft|final.json`).
- **Robustez de armazenamento (`localStorage`):**
  - Se o armazenamento falhar (ex.: `QuotaExceededError` ou modo restrito), `persistDraft` captura a falha sem interromper a edição e a interface exibe alerta orientando exportar o rascunho em JSON imediatamente.
  - Se o rascunho salvo em `localStorage` estiver corrompido ou incompatível, `ReviewerGate` bloqueia o carregamento silencioso, informa o erro e oferece descartar o rascunho corrompido para iniciar limpo.
  - Ao recarregar a página, basta reimportar o mesmo pacote JSON e informar o mesmo identificador de revisor para retomar o progresso local automaticamente.
- O nome do revisor é declarado e não verificado. Os hashes detectam corrupção/edição acidental, não
  autoria nem adulteração maliciosa (quem altera o JSON pode recalcular os hashes).
- Documentos são exibidos por Blob URL local (sem rede). PDFs usam o visualizador do navegador em
  `<iframe>`; o conteúdo vem de pacote que o próprio usuário escolheu e passou na verificação de
  assinatura/hash, mas isso não equivale a varredura de malware.
- `crypto.subtle` exige contexto seguro (`localhost`/`127.0.0.1` ou HTTPS); sem ele a importação falha com mensagem.
- Dados ficam em `localStorage` sem criptografia; evite documentos reais sem decisão explícita do
  protocolo. Esta etapa usa apenas dados sintéticos, com um registro curricular por XML (`len(records) == 1`) conforme a bancada aprovada.
- **Templates e guia permanecem em rascunho:** tanto os templates textuais em português (`TEMPLATE_PROVENANCE`, `ptbr-contract-draft-v1`) quanto o guia operacional (`operational-guide-draft-v1`) exigem validação e aprovação humana explícita antes do congelamento (`freeze`) e do estudo oficial.

## Verificação executada e fora do escopo

- **Verificações executadas localmente (offline, sem API/banco/fila/Gemini):**
  - `pytest tests/test_annotation_package.py`: **19 passed** (seleção determinística de 5 casos piloto cobrindo as 5 categorias e famílias distintas, ausência de `gold`/`expected`/`operator`/`family_id`/`template_id`/`issuer_id` fora do conteúdo comparado, IDs neutros `case-001`..`case-005`, verificação de bytes/MIME/SHA-256, CLI e execução sem módulos de banco/fila/Gemini).
  - `ruff check` em `annotation_package.py` e `test_annotation_package.py`: **All checks passed!**
  - `npm run lint` e `npm run build` (`tsc -b && vite build`) em `comprova-lattes-app/`: **exit 0**.
  - Inspeção do bundle gerado (`dist/assets/`): confirmado que nenhum gabarito (`gold`), `private-map` ou dado do corpus é embutido no bundle estático.
  - Cruzamento Node + navegador headless (`http://127.0.0.1:4173/revisao-experimental` via Vite preview local e Chrome headless CDP): verificados equivalência de `canonicalJson`/`canonicalSha256` entre Python (`freeze.canonical`) e TypeScript, rejeição de corpus bruto, campos inicialmente em branco (`present`/`absent`/`illegible` com preservação explícita de `illegible`), ausência de renderização do XML na Fase 1, desabilitação de campos e confirmação explícita nos casos sem documento, liberação da Fase 2 com XML ao lado e Fase 1 travada, reabertura auditável (`phase1_reopen_count`), retomada após reload do navegador, tratamento de erro de quota/corrupção e exportação/reimportação validada com bloqueio entre revisores distintos.
- **Fora do escopo desta entrega:** consenso/adjudicação na UI, cálculo de Kappa/concordância, geração do pacote de 150 cenários ou corpus final oficial, calibração/congelamento (`freeze`) e aprovação humana do guia ou dos templates.

## Arquivos

- Backend: `comprova-lattes-api/src/comprova_lattes/experiments/annotation_package.py`, testes em
  `comprova-lattes-api/tests/test_annotation_package.py`.
- Frontend: `comprova-lattes-app/src/lib/annotation/` (hash/validação/rascunho),
  `comprova-lattes-app/src/components/annotation/`, `comprova-lattes-app/src/pages/ExperimentalReviewPage.tsx`,
  rota em `App.tsx` e link em `AppShell.tsx`.
