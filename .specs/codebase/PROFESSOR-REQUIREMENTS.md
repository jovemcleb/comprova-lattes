# Requisitos Técnicos dos Comentários do Orientador (Código & Experimentos)

> Checklist técnico extraído dos 88 comentários do Prof. Dr. Fabrício Almeida Araújo. Para os comentários relativos à escrita da monografia e ABNT, veja `MONOGRAPH-GUIDE.md`.

## 1. Processamento XML (Comentários #25 e #51)
- [ ] **Segurança (`defusedxml`):** Usar `defusedxml` em vez de `xml.etree.ElementTree` puro (previne ataques de entidades externas / XXE no upload do usuário).
- [ ] **Validação contra DTD Oficial (#25):** Validar os XMLs sintéticos contra a DTD oficial do CNPq sem resolução de rede, garantindo que o parser não seja testado em um formato inexistente.
- [ ] **Mapeamento Explícito (#25):** Documentar em quadro o vínculo exato entre cada tag/atributo do XML (`FORMACAO-ACADEMICA-TITULACAO`, `FORMACAO-COMPLEMENTAR`, `PARTICIPACAO-EM-EVENTOS-CONGRESSOS`, `NOME-INSTITUICAO`, `ANO-DE-CONCLUSAO`, `CARGA-HORARIA`, etc.) e os campos do modelo JSON/Pydantic.
- [ ] **Testes:** Testar arquivos inválidos, tags ausentes, estruturas inesperadas e codificações `ISO-8859-1` e `UTF-8`.

## 2. Extração Multimodal com Gemini (Comentários #29, #32, #34, #52 e #53)
- [ ] **SDK e Multimodalidade:** Usar SDK oficial `google-genai` processando arquivos PDF e Imagem diretamente (não apenas `.txt` ou `.html`).
- [ ] **Validação Estrutural:** Saída estruturada validada por `JSON Schema` e `Pydantic v2`, diferenciando campo ausente (`null`) de string vazia.
- [ ] **Remoção de Viés de Decisão (#52):** **Não usar** `confianca_extracao` nem `categoria_sugerida` como critério decisório no motor. Se mantidos no schema, justificar a finalidade informativa e garantir em código que o motor os ignore.
- [ ] **Reprodutibilidade e Repetições (#32, #34, #53):** Registrar modelo exato, versão, período de execução, estratégia (`zero-shot` ou `few-shot`, com prompt final no apêndice), fixar `temperatura = 0.0` e rodar **3 repetições por documento** para medir a variância da extração.
- [ ] **Separação de Falhas:** Tratar separadamente erros operacionais da API, respostas JSON inválidas e documentos ilegíveis.

## 3. Motor Determinístico e Similaridade (Comentários #16, #36, #37, #38, #59, #60, #61 e #62)
- [ ] **Independência:** Testável isoladamente com JSONs de referência sem chamar a API do Gemini.
- [ ] **Guarda de Divisão por Zero (#60):** Tratar explicitamente na função de Levenshtein normalizado o caso em que ambas as strings normalizadas são vazias ($\max(|N(s_1)|, |N(s_2)|) = 0$).
- [ ] **Equivalência de Siglas Separada (#36):** Levenshtein não resolve sigla (`USP` vs `Universidade de São Paulo` ou `UFRA` vs `Universidade Federal Rural da Amazônia`). Implementar tabela/regra explícita de equivalência de siglas antes do cálculo de distância de edição.
- [ ] **Métricas Adicionais de Similaridade (#37):** Além de Levenshtein normalizado (Navarro, 2001), implementar e comparar **Jaro-Winkler** (para nomes) e uma métrica baseada em **tokens** (conforme Cohen, Ravikumar e Fienberg, 2003).
- [ ] **Unidade Formal de Análise e Casos Órfãos (#61):** Definir formalmente se a unidade é o registro, o documento ou o par registro-documento, e especificar o resultado para: (a) registro Lattes sem comprovante, (b) documento sem registro correspondente e (c) múltiplas correspondências ambíguas.
- [ ] **Tabela de Decisão e Limiares (#38 e #62):** Fundamentar as 3 regiões de decisão (`Validado`, `Inconclusivo`, `Divergente`) no modelo de **Fellegi e Sunter (1969)**, deixando explícito que `Divergente` pressupõe associação prévia com conflito factual. Documentar tabela com atributos essenciais, regras por campo e limiares calibrados nos 30 casos piloto e congelados antes dos ~90 finais.

## 4. Bancada Sintética e Experimentos (Comentários #16, #29, #44, #45, #46, #47, #63, #64, #65, #67 e #71)
- [ ] **Geração Não-Circular com Degradação Visual (#46):** **Não usar o Gemini** para gerar os documentos que ele vai avaliar. Gerar certificados a partir de templates HTML/DOCX variados (fontes, layouts, logos fictícios) convertidos para PDF/imagem e aplicar **script de degradação** (simular escaneamento, rotação leve, ruído, baixa resolução, carimbo).
- [ ] **Variação Legítima vs. Mutação Factual (#63 e #64):** Separar variações legítimas de escrita/sigla (que devem resultar em `Validado`) das mutações factuais de dados (troca de titular, divergência de carga horária/ano/instituição, que devem resultar em `Divergente`) e omissões (que levam a `Inconclusivo`). Especificar níveis de perturbação (ex.: `40h -> 45h` vs `40h -> 400h`).
- [ ] **Concordância do Gabarito — Kappa de Cohen (#47):** Caleb e Elivanilso rotulam os gabaritos independentemente e calculam o **Kappa de Cohen** para comprovar validade de construto sem viés individual.
- [ ] **Experimento 1 (Extração):** Comparar **Gemini Multimodal** vs. **Baseline OCR (`Tesseract`) + RegEx (#29)** sobre os mesmos documentos (3 repetições no Gemini).
- [ ] **Experimento 2 (Motor Isolado):** Alimentar o motor com o gabarito perfeito e comparar **Baseline A (Exact Match)**, **Baseline B (Só Normalização, sem Levenshtein — #16)** e **Método Proposto**.
- [ ] **Experimento 3 (Fluxo Integrado):** Avaliar do XML + PDF/Imagem até a classificação final, reportando matriz $3 \times 3$, precisão, recall, F1 por classe, Macro-F1, métricas de associação (#65), tempo, custo da API e análise dos erros.
- [ ] **Rigor Estatístico (#45, #67 e #71):** Calcular **Intervalo de Confiança por Bootstrap** (#45), **Teste de McNemar** (`statsmodels`) para comparar classificadores pareados (#67) e, se viável, cronometrar um teste pequeno (10 casos) de conferência manual vs. sistema (#71).
