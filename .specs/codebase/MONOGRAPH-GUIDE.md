# Guia de Revisão da Monografia e Pendências Administrativas (TCC 2)

> Resumo dos comentários do Prof. Dr. Fabrício Almeida Araújo sobre estrutura textual, citações, normas ABNT/UFRA e trâmites da CTES.

## 1. Ações Administrativas Imediatas (Com o Orientador / CTES)

- **[ ] Justificativa de Dados Sintéticos para a CTES (Comentário #48):**
  - *Regra (Art. 21, parágrafo único):* Como o TCC 2 mudou de dados reais para dados 100% sintéticos em relação ao pré-projeto aprovado no TCC 1, o orientador precisa enviar justificativa formal à CTES até **30 dias antes da defesa**.
  - *Ação:* Enviar ao Prof. Fabrício um parágrafo curto justificando a mudança (controle experimental das variáveis, prevenção de vazamento de dados pessoais/LGPD e reprodutibilidade pública da bancada).
- **[ ] Relatório de Andamento das Etapas 9 a 13 (Comentário #69):**
  - Informar ao orientador o estado real de cada módulo (bancada sintética, parser XML, extrator Gemini, motor determinístico e experimentos).

## 2. Nova Estrutura da Monografia (Comentários #03, #04, #06, #11, #69, #70 e #88)

O texto deve deixar de ter formato de pré-projeto (verbos no futuro, cronograma, resultados esperados, folha de assinaturas) e assumir formato de **Monografia de TCC 2** (verbos no passado para o que foi implementado):

1. **Elementos Pré-Textuais (#01, #04, #05, #06):**
   - Incluir Brasão da UFRA na capa conforme modelo da Biblioteca/CTES (#01).
   - Enxugar o título (~30 palavras) para algo como: *"Validação semiautomatizada do Currículo Lattes com LLMs: cruzamento entre dados XML e documentos comprobatórios"* e definir logo na introdução o sentido de "validação" como verificação de consistência (#02).
   - Substituir texto da folha de rosto para obtenção do grau de Bacharel em Sistemas de Informação (#04).
   - Incluir Ficha Catalográfica (FICAT), Folha de Aprovação (no lugar de Assinaturas — #06 e #88), Resumo, Abstract, **Lista de Siglas** (`LLM`, `XML`, `JSON`, `OCR`, `IE`, `API`, `DSR`, `DTD`) e Sumário automático do Word sem ponto após o número da seção (`1 INTRODUÇÃO`, não `1. INTRODUÇÃO` — #05).
2. **Capítulos Textuais (#03, #11, #69, #70):**
   - `1 INTRODUÇÃO`: Contexto, problematização, pergunta de pesquisa (incluindo os dois baselines — #16), objetivos (Geral com *"Desenvolver e avaliar..."* — #17; Específicos com marcadores normais, juntando JSON no item 2 e separando interface web da avaliação experimental — #18, #19, #20), justificativa institucional com dado concreto (#21), **principal resultado numérico obtido** e parágrafo de organização do trabalho (#11).
   - `2 REFERENCIAL TEÓRICO`: Cortar repetições de que "o LLM só extrai e o motor decide" (manter apenas na Introdução e Metodologia — #12).
   - `3 TRABALHOS CORRELATOS`: Mudar Quadro 1 para colunas objetivas de **Sim/Não** (*Usa LLM? Entrada multimodal? Cruza com fonte estruturada? Classifica consistência? Domínio acadêmico?* — #40) e discutir Diploma Digital (Portaria MEC nº 554/2019), certificados com QR Code/código SIGAA e o artigo LMDX (#39).
   - `4 MATERIAIS E MÉTODOS`: Incluir figura das 6 etapas da **DSR de Peffers et al. (2007)** ligadas às seções do TCC (#43), quadro detalhado dos 30 casos piloto e dos 90 finais (#44, #45), citação da **Resolução CNS nº 466/2012 (item II.14)** em vez da 510/2016 deixando claro que nenhum XML sintético veio da edição de um Lattes real (#49), e incluir a **Validade de Conclusão** de Wohlin et al. (#68).
   - `5 DESENVOLVIMENTO DO PROTÓTIPO`: Diagrama da arquitetura efetivamente implementada (#50, #54, #55), trecho XML sintético + quadro XML → JSON (#25), Tabela de Decisão completa com limiares (#62) e telas da interface.
   - `6 RESULTADOS E DISCUSSÃO`: Substitui "Resultados Esperados" (#70). Matrizes de confusão, métricas por classe com IC por bootstrap, comparação com baselines (OCR+RegEx, Exact Match, Normalizado) + teste de McNemar, variância nas 3 execuções do Gemini, análise de erros reais, tempo e custo da API.
   - `7 CONCLUSÃO`: Resposta direta à pergunta de pesquisa, ressalva sobre ambiente sintético vs. esforço operacional (#71), link do repositório GitHub com README reprodutível (#72) e trabalhos futuros.

## 3. Correções de Citações e Referências (Comentários #08–#10, #14, #22–#38, #73–#87)

- **Adicionar / Substituir:**
  - **TCU (Acórdão nº 1131/2023 – Plenário, TC 020.025/2022-0):** Usar para sustentar o número de currículos (~7,7 milhões) e auditoria do Lattes, substituindo a citação genérica da página inicial `(CNPq, 2023)` (#08, #14, #76).
  - **Edital institucional real (ex.: UFRA PSS/Bolsas/Progressão):** Citar na Introdução e Problematização para comprovar a conferência documental manual (#09, #13, #21).
  - **W3C (XML 1.0, 5th ed., 2008)** e **Documentação DTD do CNPq:** Citar na seção 5.1 (#24, #25).
  - **Chiticariu, Li e Reiss (2013)** (*EMNLP*) + **Sarawagi (2008):** Usar na seção 5.2 e **remover** `Manning, Raghavan e Schütze (2008)` e `Hearst (1999)` (#27, #28, #83, #85).
  - **Perot et al. (2023) — LMDX (`arXiv:2309.10952`):** Usar na seção 5.3 para extração de campos de documentos via LLM no lugar de `Minaee et al.` e `Gemini 1.5` (#30, #79).
  - **Fellegi e Sunter (1969):** Usar na seção 5.5 para fundamentar os dois limiares e as três regiões de decisão (`Validado`, `Inconclusivo`, `Divergente`) no lugar de `Rahm e Do (2000)` (#38, #86).
  - **Peffers et al. (2007):** Usar na seção 6.1 para as etapas da DSR (#43).
  - **Resolução CNS nº 466/2012:** Substituir a Resolução 510/2016 (#49, #74).
  - **Navarro (2001):** Citar para a versão normalizada da Distância de Levenshtein e numerar a equação como `(1)` (#59, #60).
- **Ajustes de Formatação ABNT/UFRA:**
  - Colocar estrangeirismos e *et al.* em *itálico* em todo o texto (#31, #33).
  - Citar os 3 autores em `(WRIGHT; ANDREWS; HUTTON, 2020)` e atualizar para a especificação oficial `json-schema.org` (2020-12) (#33, #87).
  - Substituir `s.d.` por data de atualização da página ou ano provável entre colchetes `[2026?]` e usar caixa alta dentro dos parênteses `(FASTAPI, [2026?]; CELERY PROJECT, 2026)` (#35, #56, #57, #78, #82).
  - Corrigir títulos atualizados do arXiv: **XGrammar** (v3, maio/2025 — #77) e **JSONSchemaBench** (v3, fev/2025 — #80), ano/capítulo do rascunho de **Jurafsky & Martin** (#84) e local da editora Atlas (`Barueri: Atlas` — #81).
  - Alinhar lista de Referências à esquerda, espaçamento simples, separadas por linha em branco (#73).
