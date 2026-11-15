# Experimentos offline

Da pasta `comprova-lattes-api/`, com o ambiente instalado ativo:

```powershell
python -m comprova_lattes.experiments --help
python -m comprova_lattes.experiments generate --seed 42 --pilot-families 10 --final-families 20 --output corpus.json
python -m comprova_lattes.experiments calibrate --corpus corpus.json --candidates candidates.json --output calibration.json
python -m comprova_lattes.experiments freeze --corpus corpus.json --calibration calibration.json --artifacts artifacts.json --output freeze.json
python -m comprova_lattes.experiments exp1 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --extractions runs.json --baseline ocr.json --output exp1.json
python -m comprova_lattes.experiments exp2 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --seed 42 --replicates 2000 --confidence 0.95 --output exp2.json
python -m comprova_lattes.experiments exp3 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --extractions runs.json --output exp3.json
```

AD-016: 150 cenários aprovados, 10 famílias piloto e 20 finais.
Cada família contém cinco casos de uma categoria: identidade, variação
legítima, `factual_mutation`, omissão e sem comprovante (`identity`, `legitimate`,
`factual_mutation`, `omission`, `no_document`). O antigo `year_mutation` foi
substituído por `factual_mutation`; regenere corpus e manifesto, sem reutilizar
hashes de artefatos antigos. Qualquer corpus, manifesto ou hash gerado pelo
antigo rasterizador bitmap 5x7 em stdlib também é **inválido** após a adoção da
renderização Pillow (`RASTERIZER_VERSION = "pillow-aileron-gray-v1"`) e deve ser
integralmente regenerado antes de calibrar ou congelar artefatos.
Categorias alternam separadamente em cada partição: 10 casos/categoria no piloto
e 20 no final. Famílias têm identidades/emissores exclusivos e permutação de campos,
margens e espaçamento determinísticos. Isso amplia diversidade, sem provar independência
estatística ou realismo documental. Corpus e manifestos anteriores devem ser regenerados.

## Renderização documental (Pillow grayscale, PNG e PDF equivalentes)

- **Dependência opcional de experimentos:** `pillow>=11.0.0` em
  `[project.optional-dependencies].experiments` (e incluída em `.[dev]`), compatível
  com Python 3.11–3.13 (Pillow 11+) e Python 3.14 (Pillow 12+/13+; ambiente `.venv`
  local verificado com `pillow 13.0.0` e `freetype 2.14.3`). O import do `parser`
  (M1) e do `matcher` (M2) não requer nem carrega Pillow.
- **Método (`render.py`):** `raster(text, *, seed, degradation, layout) -> (width, height, bytes)`
  renderiza matriz grayscale de 8 bits (`mode="L"`, `len(pixels) == width * height`)
  usando a fonte TrueType embarcada do próprio Pillow (`ImageFont.load_default(size=...)`,
  família `Aileron Regular`), sem consultar fontes do sistema operacional nem baixar
  arquivos TTF externos. `png(width, height, pixels)` (PNG grayscale 8 bits, `ColorType=0`,
  filtro `0`) e `pdf(width, height, pixels)` (PDF 1.4 `/DeviceGray /BitsPerComponent 8 /Filter /FlateDecode`)
  empacotam exatamente os mesmos bytes da matriz raster degradada.
- **Limite real da fonte embarcada e suporte a acentos pt-BR/parênteses:** a tabela
  `cmap` nativa da `Aileron Regular` embarcada no Pillow é um subconjunto enxuto que
  contém ASCII imprimível (`0x20..0x7E`, incluindo parênteses `()`, colchetes e pontuação)
  e sete símbolos (`©«°±´·»`), mas omite pontos de código Latin-1 pré-compostos
  (`Á`, `Ã`, `Ç`, etc.), que seriam desenhados como caixa `.notdef` se passados diretamente
  ao FreeType. Para evitar apagamento silencioso ou colisão em `.notdef` sem depender de
  fontes do host, `render.py` normaliza a entrada (`NFC`/`NFD`), desenha a letra-base
  ASCII com `Aileron Regular` e compõe deterministicamente os diacríticos do português
  (agudo, grave, circunflexo, til, trema e cedilha, além de `º`, `ª`, `–`, `—`, `§`) sobre
  a caixa delimitadora do glifo. Caracteres fora do repertório suportado (`SUPPORTED_CHARS`)
  ou caracteres de controle levantam `ValueError` explicitamente. `_GLYPHS` permanece
  exportado por compatibilidade com testes legados.
- **Variação determinística de layout e degradação:** margens horizontais/verticais,
  escala tipográfica de cabeçalho e corpo, espaçamento entre linhas, recuo de corpo,
  centralização/filete de cabeçalho, tom de tinta e estilo de moldura (`frame_style`
  sem moldura, simples fina, simples espessa ou dupla) derivam exclusivamente do inteiro
  `layout`, sem receber categoria, classe esperada ou operador. Os três níveis de
  `degradation` (`0`, `1`, `2`) aplicam cisalhamento horizontal, subamostragem horizontal
  e ruído sal/pimenta controlados por `random.Random(seed)`.
- **Custo computacional e limites de determinismo de ambiente:** a geração offline de
  um documento leva ~1–2 ms em CPU local (~0,15–0,25 s para os 120 documentos dos 150
  cenários), sem chamadas de rede ou LLM. Os bytes raster são estritamente determinísticos
  dentro da mesma combinação de versão do pacote Pillow e binário `libfreetype`
  (`determinism_scope = "same_pillow_freetype_build"`, inspecionável via
  `rasterizer_metadata()`), mas podem divergir entre versões distintas do Pillow/FreeType
  ou compilações nativas de SO/arquitetura devido a rotinas C de rasterização/hinting.
  Por isso, o artefato `environment` do manifesto `freeze` deve registrar a versão exata
  de Python, Pillow e FreeType; testes unitários/focais verificam apenas a integridade
  de software local e **não equivalem à avaliação experimental oficial**.
- XML é fictício consumível por M1; conformidade XSD/DTD não é alegada.

Eventos e produção técnica usam subnós `DADOS-BASICOS-*` e `DETALHAMENTO-*`.
Organização mantém `event_name=None` conforme o parser, sem inferir evento do
título; apresentação traz `participation_role_raw="APRESENTADOR"` no documento.
Variação legítima alterna três estilos determinísticos por `family_id`: espaços no
titular + substituição ASCII no título longo, caixa alta/baixa na instituição, ou
substituição da instituição por sua sigla curta (`institution_acronym`). Todos os
valores humanos (titular, instituição, sigla, título, evento e evidência literal
AD-014) usam nomes fictícios curtos e legíveis em português brasileiro oriundos de
vocabulário controlado e determinístico (sem sufixos hexadecimais, sem marcadores
artificiais e preservando `case_id`, `family_id`, `template_id` e `issuer_id`
internos). `SYNTHETIC_ACRONYMS = {"I": "Instituto", "C": "Centro", "F": "Faculdade",
"E": "Escola"}` define os radicais exportados; `synthetic_acronyms(corpus.cases)`
materializa a tabela explícita `{sigla_3_letras: instituicao}` derivada das
instituições de 3 palavras presentes nas famílias passadas (sem colisões entre
`pilot` e `final` e com `pilot` invariável ao crescimento de `final_families`). Passe
essa tabela em `MatcherConfig.acronym_table`, com versão explícita, e inclua seus
bytes no artefato `acronyms` congelado. Não existe tabela global mutável compartilhando
emissores entre partições; templates de certificado permanecem em rascunho
(`TEMPLATE_PROVENANCE["template_version"] == "ptbr-contract-draft-v2"`, ainda sem
validação humana).

Uma mutação factual por categoria preserva âncoras de associação e usa identidades
alternativas da mesma distribuição legível (`alternative_identity`, sem termos como
`OUTRA`, `DIVERGENTE` ou `MUTADO`): especialização 40→45 horas; extensão 40→400
horas; participação ano inicial/final/atividade +7; apresentação troca o titular por
outro nome completo distinto da família; organização troca a instituição por outra
instituição distinta (gerando sigla distinta do XML e trecho literal AD-014 coerente
com a instituição do documento). Textos rasterizados suportam ASCII imprimível, acentos
pt-BR (`NFC`/`NFD`), parênteses e quebras de linha, rejeitando caracteres fora do
repertório suportado com `ValueError`. A vantagem do proposto sobre A/B nos testes com
siglas configuradas verifica o software nesta bancada construída, sem demonstrar
superioridade em dados independentes.

Pendência S2 identificada pelos testes: `matcher/rules.py:essential_fields`
exige `evento` também em `ORGANIZACAO_EVENTO`, onde o parser preserva ausência.
Assim, identity/legitimate dessa categoria ainda retornam INCONCLUSIVO.
Os testes exigem VALIDADO e permanecem falhando; corrigir essencialidade no
matcher depende de ampliação dos alvos autorizados. O gerador não inventa evento
nem altera o registro parseado para contornar essa inconsistência.

`candidates.json` é lista de objetos `MatcherConfig` completos. Não há limiares
embutidos. Calibração maximiza Macro-F1 no piloto, com primeiro candidato nos
empates. Final é rejeitado pela calibração. Rótulos do gerador são intenções,
não anotações humanas. `cohen_kappa` recebe duas anotações independentes antes do
consenso e reporta concordância, matriz e Kappa (indefinido em marginais degeneradas).

`artifacts.json` mapeia nomes para caminhos de arquivos reais: `schema`, `prompt`,
`regex`, `acronyms`, `normalization`, `generator`, `code`, `environment` são
obrigatórios. Inclua arquivos adicionais para cobrir todo o código/configuração.
Manifesto SHA-256 cobre esses bytes, configuração selecionada, piloto e hashes
de XML/documentos/gabaritos. CLI verifica manifesto antes de avaliar. SHA-256 não
é assinatura nem prova de que ninguém viu o final: o gerador materializa ambas
as partições. Controle de acesso ao final e registro cronológico são externos.

`runs.json` contém três mapas `case_id -> ExtractedDocumentRecord`; `ocr.json`
contém um mapa com os mesmos documentos, excluindo casos sem comprovante.
A CLI reproduz saídas previamente capturadas, sem configurar cliente Gemini.
API Python: `experiment1(cases, extractor, baseline)` recebe objetos com método
`extract(id, bytes, mime)`; `OCRRegex(ocr_callable)` injeta OCR real/simulado que
recebe exclusivamente bytes/MIME, sem gabarito. Regex configurável; `OCRRegex()`
ou `OCRRegex.from_tesseract(...)` usa `TesseractOCR` (`experiments/ocr.py`) quando
disponível. Exp 3 reutiliza as três saídas, sem novas chamadas.

## Baseline OCR Real (`TesseractOCR` + `OCRRegex`)

- **Grupo opcional de dependências Python (`[project.optional-dependencies].ocr`):**
  `pillow>=11.0.0` (já instalado na `.venv` local: `13.0.0`) e `pypdfium2>=5.0.0`
  (instalado na `.venv` local: `5.15.2`, `pdfium 159.0.8149.0`, roda sem dependências
  adicionais). O núcleo (`parser`, `matcher`) não importa `pypdfium2` nem exige Tesseract.
- **Instalação local do Tesseract e idioma português (`por`):**
  - Binário Windows oficial documentado pelo projeto Tesseract (`UB-Mannheim.TesseractOCR`
    `v5.4.0.20240606`, licença Apache-2.0, instalador `tesseract-ocr-w64-setup-5.4.0.20240606.exe`,
    SHA-256 `c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9`), instalado
    localmente no perfil do usuário em `%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe`
    sem privilégios de administrador e sem alterar o `PATH` do sistema.
  - Dados de treinamento para português (`por.traineddata`) obtidos do repositório oficial
    `https://github.com/tesseract-ocr/tessdata` (tag `4.1.0`, licença Apache-2.0,
    `15336931` bytes, SHA-256 `016c6a371bb1e4c48fe521908cf3ba3d751fade0ab846ad5d4086b563f5c528c`),
    instalados em `%LOCALAPPDATA%\Programs\Tesseract-OCR\tessdata\por.traineddata`.
- **Adaptador (`comprova_lattes.experiments.ocr.TesseractOCR`):**
  - Callable `(data: bytes, mime_type: str) -> str` para `image/png`, `image/jpeg` e
    `application/pdf`, sem acessar `gold`, `corpus` ou `manifest`.
  - Imagens `PNG`/`JPEG` são validadas com `Pillow` (formato real vs MIME declarado e
    limite `max_image_pixels=25_000_000`).
  - Documentos `PDF` são convertidos exclusivamente por rasterização de página via
    `pypdfium2` (`page.render(scale=dpi / 72.0).to_pil()`, limite `max_pdf_pages=10`),
    sem extrair camada de texto embutida e sem acoplamento ao gerador sintético.
  - Descoberta do executável via parâmetro `executable`, variável `TESSERACT_CMD`, `PATH`
    ou diretórios locais padrão; subprocesso invocado como lista de argumentos com
    `shell=False`, `timeout_seconds` configurável (padrão `30.0` s) e diretório temporário
    (`tempfile.TemporaryDirectory`) limpo automaticamente mesmo em falhas/timeouts.
  - Verifica `--list-langs` antes do OCR e inspeciona `stderr`, levantando
    `TesseractLanguageError` claro se `por` (`por.traineddata`) estiver ausente,
    `TesseractTimeoutError` em timeout, `TesseractExecutionError` em código de saída
    não-zero e `OCRRenderError` em bytes inválidos/corrompidos. Quando injetado em
    `OCRRegex.extract`, falhas operacionais (`OSError`/`SubprocessError`) retornam
    `extraction_status="API_ERROR"` sem falha silenciosa.
- **Contrato de rótulos em `baseline.py` (`FIELD_LABELS_PT` e `PATTERNS`):**
  - Preserva compatibilidade simultânea com os rótulos técnicos legados (`holder_name`,
    `activity_title`, etc.) e com os rótulos em português do contrato entre workers:
    `holder_name=Titular`, `activity_title=Atividade`, `event_name=Evento`,
    `participation_role_raw=Papel`, `issuer_institution=Instituição emissora`,
    `issuer_acronym=Sigla da instituição`,
    `issuer_name_acronym_evidence=Identificação da instituição`,
    `start_year=Ano de início`, `end_year=Ano de conclusão`,
    `activity_year=Ano da atividade` e `workload_hours=Carga horária`.
  - As expressões regulares ancoram o rótulo completo no início da linha até `:`,
    evitando confundir instituição emissora, sigla e trecho de evidência institucional,
    sem capturar o rótulo como parte do valor e sem atravessar quebras de linha quando um
    rótulo estiver vazio. Nenhuma RegEx é ajustada ad-hoc para corrigir erros de leitura
    do Tesseract no conjunto final.
- **Comandos operacionais (sem alterar `__main__.py`):**
  ```powershell
  python -m comprova_lattes.experiments.ocr --check
  python -m comprova_lattes.experiments.ocr --file caminho\documento.png --dpi 300 --lang por
  python -m comprova_lattes.experiments.ocr --file caminho\documento.pdf --mime application/pdf --dpi 300
  ```
- **Limites técnicos observados:** em PDFs gerados por `render.py` (`/MediaBox` definido
  diretamente nas dimensões em pixels da matriz), `dpi=72` (`scale=1.0`) preserva a matriz
  raster 1:1 idêntica ao PNG, enquanto `dpi=300` (`scale=300/72 ≈ 4,17`) reamostra o
  XObject de 8 bits via PDFium. Sob degradação (especialmente nível `2`, com subamostragem
  horizontal e ruído sal/pimenta) ou em glifos compostos, o Tesseract apresenta erros
  reais de reconhecimento de caracteres (ex.: troca de `0`/`O`, `3`/`B`/`S` ou corrupção
  do rótulo), que se refletem legitimamente como omissões, valores divergentes ou
  `INVALID_JSON` na baseline `OCRRegex`. Smoke tests locais verificam instalação e
  execução de software em texto fixo e amostra piloto, **não** equivalendo à avaliação
  experimental oficial.

Exp 1: cinco estados por campo, literal/equivalente, falhas separadas (API,
JSON e ilegibilidade), contagem condicional a resposta válida e falhas como
omissões. Documento falho conta como erro. Critério de acerto documental é todos
os campos do contrato corretos, mais estrito que apenas essenciais. Saídas,
estabilidade por campo, média/amplitude e N original preservados; repetições
distintas ficam separadas. `extraction_inference` oferece IC por família e
sensibilidade por repetição, além de todas as três corretas.

Exp 2: A/exato, B/normalizado e Levenshtein/Jaro-Winkler/tokens com gabarito.
Exp 3: métricas automáticas anteriores à revisão, associação separada, órfãos
fora da matriz 3x3, erros de associação/extração/regra e metadados disponíveis de
tempo/tokens/custo (ausentes não são estimados). Unidade atual: um XML com um
registro e zero/um comprovante. Concorrência entre múltiplos registros não é
avaliada por esta bancada.

`inference`: bootstrap de famílias inteiras, percentis e parâmetros explícitos,
F1=0 para classe ausente. McNemar binomial exato usa família integralmente correta,
evitando tratar variantes dependentes como independentes; Holm sobre todos os
pares reportados. Poucas famílias produzem IC pouco informativo. Sem meta de F1.

Antes de estudo oficial: fechar desenho/distribuição, anotações independentes,
modelo/prompt e parâmetros; congelar artefatos completos antes de inspecionar o
final; executar OCR/Gemini reais separadamente. Testes offline demonstram software,
não desempenho científico. Arquivos JSON do corpus contêm gabarito e não devem
ser disponibilizados ao extrator; ele recebe somente bytes do documento e MIME.
