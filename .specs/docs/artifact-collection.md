# Coleta Offline de Artefatos Pré-Congelamento (`experiments/artifacts.py`)

## Objetivo e escopo

O módulo `comprova_lattes.experiments.artifacts` prepara offline os oito artefatos
canônicos obrigatórios exigidos por `freeze()` (`comprova_lattes.experiments.freeze`)
e gera o mapa `artifacts.json` (`nome -> caminho de arquivo`) compatível com a CLI
existente (`python -m comprova_lattes.experiments freeze|exp1|exp2|exp3 --artifacts ...`).

Esta etapa é estritamente preparatória:

- **Não executa** `freeze`, `calibrate`, geração de corpus nem chamadas à API Gemini.
- **Não lê** corpus, anotações humanas, saídas experimentais (`outputs`) nem dados finais.
- **Não carrega** `Settings` nem arquivos `.env`, preservando credenciais e variáveis de ambiente fora dos artefatos.
- **Não aprova** automaticamente templates em rascunho nem anotações.

---

## Uso pré-estudo via CLI

A partir de `comprova-lattes-api/` (com o ambiente Python da `.venv` ativo ou no `PYTHONPATH`):

```powershell
python -m comprova_lattes.experiments.artifacts `
  --output-dir build/pre-freeze `
  --acronyms path/para/acronyms_explicit.json `
  --model gemini-3.5-flash-lite
```

Parâmetros principais:

- `--output-dir` (obrigatório): diretório destino explícito para os 8 arquivos `<nome>.json`, `artifacts.json` e `collection-report.json`.
- `--acronyms` (obrigatório): caminho para arquivo JSON explícito com o dicionário de siglas fornecido pelo usuário (objeto plano `{ "SIGLA": "Nome" }` ou `{ "version": "...", "acronym_table": { ... } }`), nunca derivado do corpus final.
- `--acronyms-version` (opcional): versão explícita da tabela de siglas (sobrescreve ou assume `"explicit-file"`).
- `--model` (opcional, padrão `"gemini-3.5-flash-lite"`): modelo experimental explícito registrado nos metadados de `prompt` e do relatório, sem consultar `Settings`/`.env`.
- `--artifacts-file` (opcional): caminho alternativo para `artifacts.json`.
- `--report-file` (opcional): caminho alternativo para `collection-report.json`.

Após validação humana explícita dos templates e conclusão da calibração piloto, o `artifacts.json` gerado pode ser consumido diretamente pela CLI existente:

```powershell
python -m comprova_lattes.experiments freeze `
  --corpus corpus.json `
  --calibration calibration.json `
  --artifacts build/pre-freeze/artifacts.json `
  --output freeze.json
```

---

## Artefatos coletados e separação de identidade

Todos os 8 arquivos são gravados em JSON canônico determinístico (`sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False`), sem timestamps nem caminhos absolutos pessoais/ambientais:

| Artefato | Conteúdo principal coletado | Fontes inspecionadas |
| --- | --- | --- |
| `schema` | JSON Schema real de `ExtractionPayload` e `ExtractedDocumentRecord` | `extractor/models.py`, `matcher/models.py` |
| `prompt` | `PROMPT`, `PROMPT_VERSION`, `SUPPORTED_MIME_TYPES` (via AST, sem importar `Settings`) e política de temperatura do modelo explícito | `extractor/gemini.py` |
| `regex` | `FIELDS`, `FIELD_LABELS_PT`, `PATTERNS` e flags (`MULTILINE`, `IGNORECASE`) atuais | `experiments/baseline.py` |
| `acronyms` | Tabela explícita fornecida pelo usuário (`acronym_table`), `version`, `input_sha256` e apenas `source_filename` (basename) | Arquivo explícito do usuário |
| `normalization` | Guardas de string vazia, métricas textuais suportadas e `_ROLES` | `matcher/text.py` |
| `generator` | `TEMPLATE_PROVENANCE` (preservando `draft_pending_human_validation`), rótulos, templates por categoria, `RASTERIZER_VERSION` e hash de `SUPPORTED_CHARS` | `experiments/synthetic.py`, `experiments/render.py` |
| `code` | Inventário por caminho relativo (`src/comprova_lattes/...`) e SHA-256 apenas do escopo explícito (`EXPLICIT_CODE_SCOPE`), além de `pyproject.toml` se presente | Escopo explícito (`schemas`, `parser`, `matcher`, `extractor`, `experiments`) |
| `environment` | Versão/plataforma Python, pacotes via `importlib.metadata`, status de `Pillow`/`FreeType` (`render.rasterizer_metadata`) e status sanitizado do `Tesseract` (`experiments.ocr.TesseractOCR().metadata`) | Ambiente local já instalado, offline |

O arquivo `collection-report.json` separa explicitamente:

- `stable_identity`: hashes SHA-256 dos 8 artefatos, `bundle_sha256`, inventário de fontes relativo e resumo do ambiente/modelo (`frozen: false`, `freeze_status: "prepared_not_frozen"`).
- `volatile_metadata`: timestamp UTC da execução (`collected_at_utc`), indicador de deriva entre leitura inicial e fim da coleta (`source_drift_detected`, `changed_sources_during_collection`) e avisos operacionais (`warnings`).

---

## Sanitização e tratamento de ausências

- **Segredos e paths:** não há leitura de `.env`, `os.environ`, `pip config`, `git diff` textual ou argumentos completos de processo. Caminhos absolutos de executável (`executable`) e `tessdata_dir` retornados por `TesseractOCR.metadata()` são omitidos; apenas sinalizadores booleanos (`executable_detected`, `tessdata_dir_configured`) e versões são mantidos, com redação de caminhos em eventuais mensagens de erro.
- **Dependências opcionais:** se `Pillow`/`FreeType` ou `Tesseract`/`por.traineddata`/`pypdfium2` não estiverem disponíveis localmente, a coleta **não** tenta instalar pacotes nem acessar a rede; registra `status: "unavailable"` e `available: false` em `environment.json`.
- **Deriva durante a coleta:** os hashes das fontes do escopo explícito e do arquivo de siglas são verificados no início e ao final da geração; havendo alteração concorrente no intervalo, o relatório sinaliza `source_drift_detected: true` e emite aviso.

---

## Limites metodológicos e operacionais

1. **Preparação não é congelamento oficial:** `artifacts.json` apenas empacota e calcula hashes do estado atual; o selo oficial continua dependendo de `freeze` com corpus e calibração piloto válidos e aprovação humana explícita.
2. **Templates ainda em rascunho:** `generator.json` registra `TEMPLATE_PROVENANCE["status"] == "draft_pending_human_validation"`. Os cabeçalhos e frases em português exigem validação humana antes do congelamento oficial.
3. **Instabilidade pré-integração (OCR e métricas concorrentes):** enquanto adaptações em OCR (`baseline.py`, `ocr.py`) e métricas/estatística estiverem em desenvolvimento concorrente, quaisquer hashes ou snapshots de teste obtidos agora são provisórios e devem ser **regerados após a integração completa**.
4. **Escopo de código explícito:** arquivos fora de `EXPLICIT_CODE_SCOPE` (como `config.py`, `api/`, `worker.py`, `tests/` e diretórios de dados) não entram no artefato `code`.
5. **Determinismo de rasterização:** conforme `experiments/README.md`, a equivalência de bytes do rasterizador vale dentro da mesma combinação de versão de Pillow e FreeType (`same_pillow_freetype_build`).
