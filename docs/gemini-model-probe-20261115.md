# Sondagem de modelos Gemini — 2026-11-15

Comparação exploratória autorizada de `gemini-3.8-flash`,
`gemini-3.1-flash-lite` e `gemini-3.5-flash-lite`. Não é o estudo oficial nem
define o modelo final. Nenhuma alteração no `.env` ou no modelo padrão.

## Procedimento

Gerador existente com seed 151126, uma família piloto e uma final; somente os
cinco casos `identity` do piloto foram enviados, um de cada categoria. Nenhum
documento final ou pessoal enviado. Mesmos bytes por modelo, três PDFs raster e
dois PNGs, degradações existentes do gerador (0/1/2). Layout com rótulos canônicos
de campos e nomes fictícios: cenário simplificado, sem representatividade comprovada
de certificados reais. Não inclui os novos operadores ainda pendentes nem comprova
a extração da relação explícita nome/sigla (ausente nesses casos).

Extrator real do projeto, `generateContent`, SDK 3.3.0, prompt entities-v2,
JSON Schema/Pydantic, temperatura omitida e thinking não configurado. Uma chamada
por documento/modelo, timeout HTTP de 45 s e sem retentativas em ambos SDK/extrator.
Ordem sequencial: 3.8, 3.1, 3.5. As janelas temporais distintas confundem a comparação
de disponibilidade e latência. Uma repetição por caso; não medir estabilidade com isso.

Campos textuais comparados após `normalize_text`, números comparados pelos valores.
Campos ausentes/extras também verificados, mas não usados para inflar o denominador
de campos presentes. Falhas de serviço separadas da precisão condicional ao sucesso.

## Resultados observados

| Modelo | Sucessos | Falhas | Campos presentes corretos nos sucessos | Documentos sem diferenças nos campos | Latência média só dos sucessos | Tokens informados |
| --- | --- | --- | --- | --- | --- | --- |
| 3.8 Flash | 0/5 | 5 | Não avaliável | Não avaliável | Não avaliável | Não retornados |
| 3.1 Flash-Lite | 4/5 | 1 | 30/30 | 4/4 | 21,92 s | 5160 |
| 3.5 Flash-Lite | 5/5 | 0 | 37/37 | 5/5 | 1,63 s | 6079 |

3.8: um ReadTimeout, dois 503 e dois 504. 3.1: um 503 na formação acadêmica;
demais categorias concluídas. Respostas concluídas de ambos os Lite não
apresentaram diferenças nos campos avaliados, inclusive ausentes, sob a normalização
declarada. Tokens ausentes em falhas não comprovam consumo/custo zero. Contagens
de tokens entre modelos com diferentes números de sucessos não são comparação de custo.

Um timeout escapou como exceção de tipo ReadTimeout e foi registrado como LOCAL_ERROR
pelo coletor, não como resposta de extração. O módulo de origem da exceção não foi
capturado; não atribuir causalidade ou alterar tratamento sem reprodução específica.
Demais erros foram tratados pelo extrator e armazenados como API_ERROR.

## Evidência local

Arquivos em `.tmp-model-probe-20261115/` na raiz, ignorados pelo Git: cinco comprovantes,
`manifest.json` (gabaritos), `results.json` (registros, metadados, diferenças) e
`summary.json`. Artefatos não publicados. Hashes SHA-256:

- Manifesto: `c903014d525be424d41d7b733fda48a480d9b101978c6460f01b38c409fd8856`.
- Resultados: `26c19c7657a8262e87a2788e15a7456ab76bcb03b45f66f0e11baa64daa73791`.

## Encaminhamento proposto

3.5 Flash-Lite é o candidato mais promissor desta sondagem para ampliar o piloto.
Não há evidência suficiente para afirmar equivalência/superioridade de precisão ao
3.8, cuja extração não pôde ser avaliada. Avaliar variações, mutações, omissões e
relação nome/sigla antes de escolher; fixar modelo/configuração antes da avaliação
final. Tamanho/distribuição e protocolo oficial continuam pendentes.
