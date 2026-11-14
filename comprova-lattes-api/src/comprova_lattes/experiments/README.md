# Experimentos offline

Da pasta `comprova-lattes-api/`, com o ambiente instalado ativo:

```powershell
python -m comprova_lattes.experiments --help
python -m comprova_lattes.experiments generate --seed 42 --pilot-families 2 --final-families 4 --output corpus.json
python -m comprova_lattes.experiments calibrate --corpus corpus.json --candidates candidates.json --output calibration.json
python -m comprova_lattes.experiments freeze --corpus corpus.json --calibration calibration.json --artifacts artifacts.json --output freeze.json
python -m comprova_lattes.experiments exp1 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --extractions runs.json --baseline ocr.json --output exp1.json
python -m comprova_lattes.experiments exp2 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --seed 42 --replicates 2000 --confidence 0.95 --output exp2.json
python -m comprova_lattes.experiments exp3 --corpus corpus.json --manifest freeze.json --artifacts artifacts.json --partition final --extractions runs.json --output exp3.json
```

Os números são exemplos de configuração, sem aprovação metodológica implícita.
Cada família contém 25 casos: cinco categorias cruzadas com identidade, variação
legítima, `factual_mutation`, omissão e sem comprovante (`identity`, `legitimate`,
`factual_mutation`, `omission`, `no_document`). O antigo `year_mutation` foi
substituído por `factual_mutation`; regenere corpus e manifesto, sem reutilizar
hashes de artefatos antigos.
PDF raster/PNG são gerados diretamente com stdlib, sem conversão HTML/DOCX.
Inclinação, redução de resolução e ruído têm três níveis determinísticos.
XML é fictício consumível por M1; conformidade XSD/DTD não é alegada.

Eventos e produção técnica usam subnós `DADOS-BASICOS-*` e `DETALHAMENTO-*`.
Organização mantém `event_name=None` conforme o parser, sem inferir evento do
título; apresentação traz `participation_role_raw="APRESENTADOR"` no documento.
Variação legítima combina espaços no titular, uma substituição ASCII no título
longo e sigla institucional. `SYNTHETIC_ACRONYMS = {"IF": "INSTITUTO FICTICIO"}`
define os radicais exportados; `synthetic_acronyms(corpus.cases)` materializa a
tabela explícita `IF{FAMILY_ID} -> INSTITUTO FICTICIO {FAMILY_ID}`. Passe essa tabela
em `MatcherConfig.acronym_table`, com versão explícita, e inclua seus bytes no
artefato `acronyms` congelado. Não existe tabela global mutável compartilhando
emissores entre partições.

Uma mutação factual por categoria preserva âncoras de associação: especialização
40→45 horas; extensão 40→400 horas; participação ano inicial/final/atividade +7;
apresentação troca o titular por `OUTRA PESSOA SINTETICA`; organização troca a
instituição por `INSTITUICAO DIVERGENTE SINTETICA`. Textos rasterizados usam apenas
glifos ASCII suportados após caixa alta, espaços e quebras de linha. A vantagem
do proposto sobre A/B nos testes com siglas configuradas verifica o software
nesta bancada construída, sem demonstrar superioridade em dados independentes.

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
recebe exclusivamente bytes/MIME, sem gabarito. Regex configurável; Tesseract não
é instalado ou presumido. Exp 3 reutiliza as três saídas, sem novas chamadas.

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
