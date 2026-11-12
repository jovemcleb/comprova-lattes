# Requisitos dos Comentários do Orientador (Checklist Técnico)

> Guia rápido das exigências do Prof. Dr. Fabrício Almeida Araújo para consulta de desenvolvedores e agentes de IA.

## 1. Processamento XML (Comentários 24 e 50)
- [ ] Usar `defusedxml` no lugar de `xml.etree.ElementTree` puro para evitar vulnerabilidades XXE/entidades externas.
- [ ] Validar XMLs sintéticos contra a DTD oficial do Lattes sem resolução de rede.
- [ ] Mapear tags reais das 3 seções: `Formação Acadêmica/Titulação`, `Formação Complementar` e `Participação em Eventos`.
- [ ] Documentar mapeamento XML → JSON e testar arquivos inválidos/campos ausentes.

## 2. Extração Multimodal com Gemini (Comentários 31, 33, 51 e 52)
- [ ] Usar SDK oficial `google-genai` processando PDF e imagem diretamente.
- [ ] Validar resposta com `JSON Schema` e `Pydantic` v2.
- [ ] Diferenciar explicitamente campo ausente (`null`) de string vazia.
- [ ] Registrar em log: modelo exato, versão, temperatura, parâmetros e versão do prompt (`zero-shot` ou `few-shot`).
- [ ] **Proibido** usar `confianca_extracao` ou `categoria_sugerida` como critério de decisão no motor.
- [ ] Separar falhas operacionais (erro da API, JSON inválido) de documentos ilegíveis (`Inconclusivo`).

## 3. Motor Determinístico (Comentários 35, 59, 60 e 61)
- [ ] Testável isoladamente com JSONs de referência (sem chamar o Gemini).
- [ ] Implementar normalização textual (caixa, acentos, pontuação, espaços).
- [ ] Implementar tabela explícita de equivalência de siglas institucionais (Levenshtein sozinho não resolve `UFRA` ↔ `Universidade Federal Rural da Amazônia`).
- [ ] Implementar regras específicas para números (carga horária) e datas/períodos.
- [ ] Definir Tabela de Decisão formal (atributos essenciais, limiares, regras por classe e casos ambíguos).
- [ ] Calibrar limiares apenas nos 30 casos piloto e congelá-los antes dos ~90 casos finais.

## 4. Bancada Experimental & Métricas (P0 e P1)
- [ ] **Bancada Sintética:** 30 casos piloto (`12 Validados`, `10 Divergentes`, `8 Inconclusivos`) + ~90 casos finais.
- [ ] **Não-circularidade:** Gerar certificados via templates HTML/DOCX convertidos para PDF/imagem (não usar o Gemini para gerar os documentos que ele mesmo vai ler).
- [ ] **5 Operadores de Mutação:** Carga Horária, Temporal, Titularidade, Institucional e Omissão.
- [ ] **Experimento 1:** Extração Gemini isolada vs. gabarito (3 repetições).
- [ ] **Experimento 2:** Motor determinístico com gabarito perfeito comparando Baseline A (Exato), Baseline B (Normalizado) e Método Proposto.
- [ ] **Experimento 3:** Fluxo integrado ponta a ponta (XML + PDF/IMG → Classificação).
- [ ] **Relatórios Calculados (nunca manuais):** Matriz de confusão $3 \times 3$, Acurácia, Precisão, Recall, F1 por classe, Macro-F1, métricas de associação, tempo e custo da API.
- [ ] **Melhorias P1:** Baseline OCR (`Tesseract` + RegEx), Jaro-Winkler/tokens, Kappa de Cohen, IC por bootstrap e teste de McNemar.
