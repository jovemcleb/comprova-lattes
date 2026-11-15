# Qualidade OCR no Serviço Assistido (`review_ocr`)

> **Escopo e condição experimental:** este documento registra a investigação conduzida **exclusivamente** sobre os documentos do pacote piloto [pacote-anotacao-piloto-legivel.json](../../.tmp-pilot-review/pacote-anotacao-piloto-legivel.json) (sem leitura de `xml`, `record`, gabarito ou partição `final`) e sobre amostras sintéticas fixas de regressão. O uso do painel OCR mantém a condição explícita **`ocr_assisted`** (`ocr_assisted_human_review`), nunca independente.

## 1. Sintoma observado no piloto (`case-001`)

Na revisão assistida do caso piloto `case-001` (PDF `628×352` pt nativos):
- **Texto visível na imagem (`scale=1.0`):** cabeçalho `DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO`, `Titular: Vitor Ferreira`, `Identificação da instituição: Escola Vale Regional - EVR`, `Sigla da instituição: EVR`, `Ano de início: 2031`, `Ano de conclusão: 2031`, `Ano da atividade: 2031`.
- **Saída do OCR baseline (`TesseractOCR`, `300 DPI`, `pdfium`):** `DECL&RAÇHD DE PARTICIPAÇED EM EVENTO`, `Identificação dainstituição: Escola Vale Regional - EVR`, `Ano de início: 20381`.
- **Sintomas correlatos observados em outros PDFs piloto:** `case-003` (`662×333` pt) exibiu `Ano deinício: 2020`; `case-004` (`852×438` pt) exibiu `documentalLl.`.

## 2. Causa provável com evidências

1. **Baixa resolução nativa e métricas tipográficas de [render.py](../../comprova-lattes-api/src/comprova_lattes/experiments/render.py):**
   - Os documentos são gerados em `72 DPI` (`1 px = 1 pt`) com fonte `Aileron Regular` nos tamanhos `16..22 px` e diacríticos desenhados manualmente com traço de `1 px` (`_draw_diacritic`).
   - Em `font_size=16`, a altura de caixa-baixa é `a_h=9 px` (`A_h=11 px`) e o avanço de espaço é apenas `space_adv=3.00 px` (`size=18`: `4.00 px`; `size=22`: `5.00 px`).
2. **Reamostragem não inteira no `pypdfium2` (`300/72 ≈ 4.167x`):**
   - O baseline `TesseractOCR()` renderiza PDFs diretamente via `pdfium` com `scale = dpi / 72` (`4.167x` a `300 DPI`) sem `--psm` explícito (`psm=None`).
   - Em glifos pequenos com diacríticos de `1 px` e contraste sintético, a escala fracionária introduz ruído entre hastes e acentos (ex.: `ÇÃ` -> `ÇH`/`ÇE`, `2031` -> `20381`) e funde espaços estreitos de `3 px` (`da instituição` -> `dainstituição`).
3. **Efeito em PNGs pequenos sem reamostragem:**
   - Um PNG `628×352` enviado diretamente ao Tesseract `5.4.0` sem upscaling colapsa palavras curtas; com upscaling `LANCZOS` até teto moderado, o reconhecimento recupera a estrutura textual.

## 3. Comparação controlada no piloto (sem comparação com `final`)

| Configuração | `case-001` | `case-002` / `case-003` / `case-004` | Degradação sintética `1..2` |
| --- | --- | --- | --- |
| Baseline (`dpi=300`, `pdfium`, `psm=None`) | `DECL&RAÇHD`, `20381`, `dainstituição` | `case-003`: `deinício`; `case-004`: `documentalLl.` | Mantido como referência do pipeline |
| `pillow_lanczos` (`dpi=288`, `4x` inteiro, `psm=3`) | `DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO`, `Ano de início: 2031`; persiste `dainstituição` | `case-002`, `case-003` (`Ano de início: 2020`) e `case-004` (`documental.`) legíveis | Melhor que `psm=6` sob ruído, mas `degradation=2` ainda erra anos (`2021` -> `9021`/`9031`) |
| `psm=6` em bloco único | Similar em documento limpo | — | Introduz alucinações em ruído de borda sob `degradation=1..2` |

## 4. Mitigações implementadas (somente serviço assistido e UI)

1. **Defaults do baseline preservados:** [ocr.py](../../comprova-lattes-api/src/comprova_lattes/experiments/ocr.py) mantém `DEFAULT_OCR_DPI = 300`, `DEFAULT_PDF_RESAMPLING = "pdfium"`, `upscale_small_images = False` e `psm = None`. Os novos parâmetros (`pdf_resampling`, `upscale_small_images`, `small_image_upscale_max_dim`, `psm`) são estritamente opt-in.
2. **Preset explícito e auditado em [review_ocr.py](../../comprova-lattes-api/src/comprova_lattes/experiments/review_ocr.py):**
   - O servidor local padrão passa a usar o preset **`assisted-lanczos-4x-dpi288-v1`** (`dpi=288`, `pdf_resampling="pillow_lanczos"`, `upscale_small_images=True`, `psm=3`), exposto e auditado via `assist_preset` em `/health` e `/ocr` (com opção `--preset baseline` para `baseline-default-v1`).
3. **Bloqueio visível de sugestões inválidas sem adulterar o OCR bruto:**
   - O texto `ocr_text` permanece integralmente imutável e copiável (`20381` nunca é autocorrigido para `2031`).
   - Capturas RegEx sintaticamente inválidas (ex.: ano de 5 dígitos `20381`, ano malformado `20a1`, carga horária `40h`, ou evidência `issuer_name_acronym_evidence` incompatível) permanecem `null` em `regex_fields`, **não** entram em `unextracted_fields` (evitando confundir captura inválida com campo ausente) e são expostas em `invalid_regex_fields` + `field_warnings` (`diagnostics_version="ocr-diagnostics-v1"`).
   - No frontend ([ocr.ts](../../comprova-lattes-app/src/lib/annotation/ocr.ts) e [OcrAssistPanel.tsx](../../comprova-lattes-app/src/components/annotation/OcrAssistPanel.tsx)), há validação defensiva no cliente (inclusive após recarga via `ocr_raw_text`), alerta explícito em caixa `.attention`, badge `Captura RegEx inválida (bloqueada)` e supressão dos botões `Usar no campo` / `Copiar valor` para campos bloqueados.

## 5. Limitações remanescentes e proposta não implementada

- **Limitações atuais:**
  - Em `case-001`, o rótulo `Identificação da instituição` ainda pode ser lido sem espaço (`Identificação dainstituição`) mesmo com `Lanczos 4x`, devido ao `space_adv=3.00 px` na fonte original `16 px`.
  - Documentos sintéticos com `degradation=2` continuam sujeitos a troca de dígitos (ex.: `2` -> `9`) pelo Tesseract; nenhum ajuste de OCR elimina a conferência visual humana obrigatória.
- **Proposta para decisão futura (NÃO implementada por exigir alteração do gerador do corpus):**
  - **Proposta:** elevar a escala/tamanho de fonte mínima e espaçamento entre palavras em `render.py` (ex.: `font_size >= 22..24`, em que `space_adv >= 5 px`, ou separação horizontal maior para fontes `16 px`).
  - **Benefício científico:** reduzir erros puramente raster/tipográficos de espaçamento e diacríticos de `1 px` sem acoplar o motor ao gerador.
  - **Custo:** altera `RASTERIZER_VERSION` e os hashes de documentos gerados, exigindo regeneração e revalidação do pacote piloto antes de qualquer avaliação oficial.
