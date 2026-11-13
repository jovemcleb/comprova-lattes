# Proposta — Protocolo experimental reprodutível (TCC 2)

**Status:** PROPOSTA para decisão (2026-11-13). Nada aqui está aprovado, implementado ou medido. Não há resultado, custo, modelo exato ou limiar neste documento; números como 30, ~90 e 3 repetições são os já planejados em [ROADMAP](../../project/ROADMAP.md) e [STATE](../../project/STATE.md), reproduzidos como proposta e não como regra.

**Escopo:** bancada sintética, Experimentos 1–3, gabarito, métricas, estatística, artefatos e riscos de vazamento.
**Fora de escopo:** regras do motor, tabela de decisão, limiares, tabela de siglas e métricas de similaridade (pertencem à proposta M2, `.specs/features/m2-matcher/proposal.md`, não revisada aqui); parser M1; schema e prompt do extrator (M3); texto da monografia.

**Fronteira com M2:** este protocolo só consome do motor uma interface (registro + extração → classe, motivo, evidência por campo) e uma versão congelada. Onde a unidade de análise aqui depender de OPEN-01, a decisão deve ser tomada uma única vez e refletida nos dois documentos.

Numeração dos comentários: sequencial 1–88 de [COMENTARIOS-PROFESSOR-ORIGINAIS](../../../docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md), igual a [PROFESSOR-REQUIREMENTS](../../codebase/PROFESSOR-REQUIREMENTS.md).

---

## 1. Premissas

| Item | Situação | Fonte |
| --- | --- | --- |
| LLM só extrai; motor determinístico decide; `confianca_extracao`/`categoria_sugerida` não entram na decisão | Aprovado | AD-002, #52 |
| Um documento por atividade no MVP | Aprovado | AD-004 |
| Registro sem comprovante → `Inconclusivo` / `SEM_COMPROVANTE` | Aprovado | AD-005 |
| Campo ausente = `None`; carga horária `Decimal`, negativa descartada com aviso | Aprovado (contexto do usuário) | M1/M3 |
| Bancada 100% fictícia, criada do zero; Gemini nunca gera o documento que avaliará | Aprovado | PROJECT, #46 |
| Classes finais: 3 (`Validado`, `Divergente`, `Inconclusivo`); associação avaliada separadamente | Aprovado (contexto do usuário) | #61, #65 |
| 30 casos piloto + ~90 finais; 3 repetições a temperatura 0 | Proposta existente, não regra | ROADMAP, OPEN-03, #45, #53 |
| Órfãos fora da matriz; ambiguidade como Inconclusivo; revisão humana separada | Aprovado (AD-006/007/013); unidade, denominadores e limiares ainda pendentes | #38, #61, #65 |
| Cinco categorias curriculares; três classes de resultado | Escopo aprovado (AD-012); distribuição experimental pendente | STATE |
| Avaliação sem meta arbitrária | **Aprovado:** reportar desempenho observado com IC; meta 0,85 removida | STATE AD-008, PROJECT G3 |

## 2. Rastreabilidade

| # | Exigência do professor | Onde é tratada |
| --- | --- | --- |
| 16 | Dois baselines: exato e só normalização | §3 Exp. 2 |
| 17 | Objetivo "desenvolver e avaliar" ↔ pergunta "em que medida classifica corretamente" | §3 (a pergunta é respondida pelo Exp. 3) |
| 29 | Baseline OCR + regex nos mesmos documentos | §3 Exp. 1 |
| 32, 34, 53 | Modelo/versão/período, zero- vs few-shot, temperatura e ~3 repetições | §3 Exp. 1, §9 |
| 36, 37 | Sigla por regra; comparar Jaro-Winkler/tokens | M2; comparação como opcional (§10) |
| 38, 62 | Fellegi–Sunter, tabela de decisão e limiares | M2; aqui só a regra de congelamento (§5) |
| 44, 45 | Quadro do piloto/final, N definido, IC por bootstrap | §4, §8 |
| 46 | Sem geração por LLM avaliado; templates variados + degradação por script | §4 |
| 47 | Rotulagem independente e Kappa de Cohen | §6 |
| 48 | Justificativa à CTES (30 dias antes da defesa) | Fora deste arquivo: ADMIN-01 |
| 49 | Nenhum XML sintético derivado de Lattes real | §4 |
| 52 | Confiança do LLM fora da decisão | §1, §7 |
| 61 | Unidade de análise; registro sem doc; doc sem registro | §7 |
| 63, 64 | Mutação é analogia; níveis e classe esperada; variação legítima ≠ mutação | §4 |
| 65 | Métrica da associação | §7 |
| 66 | Origem do 0,85 | §11 D3 |
| 67 | McNemar pareado | §8 |
| 68 | Validade de conclusão (amostra pequena, teste estatístico, variação do LLM) | §5, §8 |
| 70, 72 | Resultados reais; README para rodar experimentos | §9 |
| 71 | Teste cronometrado de ~10 casos | Opcional (§10) |

## 3. Experimentos

| | Exp. 1 — Extração | Exp. 2 — Motor isolado | Exp. 3 — Fluxo integrado |
| --- | --- | --- | --- |
| Pergunta | O Gemini extrai melhor que OCR+regex, e quanto a extração varia entre repetições? | O que a similaridade acrescenta além de exato e normalização? | Em que medida o fluxo XML + documento classifica corretamente? |
| Entrada | Documentos PDF/imagem degradados | Registros XML + **gabarito de extração** (valores impressos no documento, sem passar por LLM) | XML + documentos, sem gabarito |
| Métodos | Gemini multimodal (3 execuções) × Tesseract + regex | Baseline A (exato) × Baseline B (só normalização, sem Levenshtein) × Método proposto (M2) | Gemini + motor proposto; comparações secundárias na §10 |
| Saída | Métricas por campo e por documento; variância entre execuções | Matriz 3×3, P/R/F1, Macro-F1; associação | Idem Exp. 2 + tempo, tokens/custo, análise de erros |

Regras comuns:
- **Mesmo conjunto de documentos e mesmos campos** para todos os métodos comparados (pareamento exigido por #67).
- **Exp. 3 reaproveita as extrações do Exp. 1** (uma execução de Exp. 3 por repetição do Gemini), sem novas chamadas à API. Perda de Exp. 2 → Exp. 3 é atribuída a extração/associação na análise de erros.
- **Temperatura 0 é configuração, não garantia de determinismo**; sujeito a suporte do modelo escolhido. Se o modelo não aceitar ou não honrar o valor, registrar e decidir antes do piloto (D6). As 3 repetições medem a variação residual.
- **Baselines em pé de igualdade:** regex do OCR e prompt do Gemini ajustados no piloto, com esforço comparável e registrado (D9). Regex ajustada à aparência dos templates do piloto favorece o baseline se esses templates reaparecerem no final.
- **Associação:** baselines A/B precisam de regra de associação. Proposta: avaliar (a) classificação com pares verdadeiros fornecidos (isola a regra de decisão) e (b) associação de cada método separadamente. Decisão em D9.
- Falhas separadas em: erro operacional de API, JSON inválido, documento ilegível. Nunca descartar caso em silêncio (tratamento no denominador: D7).

## 4. Bancada sintética

**Termos.** *Registro-base*: registro fictício a partir do qual se derivam variações e mutações. *Família*: conjunto de casos que compartilham registro-base e/ou template/emissor fictício. *Caso*: um registro curricular do XML, com 0 ou 1 documento (AD-004).

**Geração (#46, #49).**
- Gerador determinístico com semente registrada; templates HTML/DOCX variados (fonte, layout, logos fictícios) → PDF/imagem → script de degradação (escaneamento, rotação leve, ruído, baixa resolução, carimbo).
- Nenhum LLM gera documento avaliado. Se IA generativa for usada em qualquer etapa auxiliar, deve ser de outra família e documentada (#46); recomenda-se não usar.
- Nenhum XML ou nome vindo de Lattes ou documento real; nenhum XML obtido editando Lattes real (#49). Uso de documentos reais fica fora e exige decisão explícita.
- AD-011 adota XSD oficial do Extrator como referência estrutural principal e DTD comunitária como comparação histórica. O requisito DTD do professor continua pendente; conformidade XSD não comprova equivalência com exportação da interface. Verificação estrutural pertence ao M1.

**Variação legítima ≠ mutação factual (#63, #64).** Cada operador declara classe esperada e níveis. Categorias, sem fixar operadores nem limiares:

| Categoria | Exemplo do professor | Classe esperada |
| --- | --- | --- |
| Variação legítima (nome abreviado, sem acento, sigla) | "USP" ↔ "Universidade de São Paulo" | `Validado` |
| Mutação factual (titular, instituição, ano, carga) | troca de titular; 40h → 400h | `Divergente` |
| Mutação factual de menor magnitude | 40h → 45h | `CONFLICT` no campo carga em par associado (AD-009); classe final depende da agregação por categoria, ainda pendente |
| Omissão de campo essencial | campo `None` | `Inconclusivo` |
| Sem comprovante / ambiguidade | AD-005 / AD-007 | `Inconclusivo` |
| Documento órfão (sem registro) | AD-006 | Fora da matriz 3×3; relatado à parte |

A classe esperada de casos próximos da fronteira não pode ser derivada do limiar do motor (circularidade). Proposta: separar **casos nítidos** de **casos de fronteira**, com classe esperada definida pelo guia de anotação (§6) antes do piloto, e relatá-los separadamente. "Mutação" é analogia ao *mutation testing*, não aplicação dele (#63).

**Controle de confundimento.** Classe, operador, template e nível de degradação devem ser cruzados e balanceados, para o extrator ou o regex não aprenderem pista espúria (ex.: todo `Divergente` no mesmo template).

**Tamanho (#45).** Proposta: piloto de 30 (distribuição 12/10/8 do ROADMAP, aproximada) e final de cerca de 90, **sem cenários adicionais "quando necessário"**. Número final e distribuição por classe: D2. Com ~30 casos por classe e famílias dependentes, o número efetivo de unidades independentes é menor que o de casos: reportar ambos.

**Quadro obrigatório na monografia (#44):** distribuição por classe, operador, tipo de documento, layout, template e nível de degradação, mais 1–2 figuras de documento gerado. O manifesto (§9) gera esse quadro automaticamente.

## 5. Piloto × final e riscos de vazamento

**Partição por família.** Todas as variações de um registro-base e todas as degradações do mesmo documento ficam na mesma partição. Casos da mesma família não são amostras independentes e nunca são distribuídos entre piloto e final. A regra da família (registro-base, template ou ambos) é D1.

| Fase | Pode | Não pode |
| --- | --- | --- |
| Piloto (30) | Depurar gerador e pipeline; ajustar prompt, regex e normalização; calibrar limiares (M2); estimar variância, tempo e tokens | Ser apresentado como desempenho final (otimista por construção) |
| Congelamento | Registrar hash de schema, prompt, regex, tabela de siglas, limiares, normalização, gerador, código e ambiente | Alterar qualquer item depois de gerar/abrir o final |
| Final (~90) | Uma execução oficial por configuração; reportar o que sair | Ajustar qualquer coisa após ver erros finais; omitir resultado ruim; usar a meta como critério de parada |

Qualquer mudança após o congelamento vira nova versão e é declarada como desvio, com o final tratado como já visto.

**Riscos de vazamento e mitigação:**

| Risco | Mitigação proposta |
| --- | --- |
| Mesma família em piloto e final | Partição por família (acima) |
| Regex/prompt ajustados a templates que reaparecem no final | Final com templates não vistos no piloto, ao menos em parte (D1); relatar desempenho por template visto/não visto |
| Tabela de siglas construída com instituições do piloto e reutilizadas no final | Declarar como limite de validade externa ou incluir instituições novas no final (D1) |
| Exemplos de few-shot iguais a casos avaliados | Exemplos fora de piloto e final, ou só do piloto (D6) |
| Rótulo vazando por nome de arquivo, metadados do PDF/EXIF, pasta | IDs neutros; gabarito e manifesto fora do diretório lido pelo extrator |
| Classe esperada derivada do limiar do motor | Casos nítidos × fronteira; guia de anotação independente (§6) |
| Geração circular (LLM gera e extrai) | Vedada (#46) |
| Anotadores veem saída do sistema; correção do gabarito após ver erros | Anotar e fechar gabarito antes de rodar o sistema; regra de correção pré-registrada |
| Geradores sabem a classe pretendida (criadores = anotadores) | Anotar a partir do XML + documento, sem o manifesto; registrar a limitação |
| Resultados do piloto reutilizados como resultado | Relatórios do piloto marcados `pilot`, não agregados ao final |

**Validade de conclusão (#68):** amostra pequena, famílias dependentes, variação do LLM entre execuções, múltiplos testes, ausência de poder estatístico calculado. A monografia deve declará-las.

## 6. Gabarito e Kappa (#47)

- Três gabaritos distintos: **extração** (valores impressos), **associação** (pares corretos) e **classe** (3 classes + motivo).
- Os dois autores rotulam **independentemente** classe e associação, a partir do XML e do documento, com um guia de anotação escrito antes e sem uso do limiar do motor. As duas anotações são guardadas antes do consenso.
- Kappa de Cohen calculado **antes** do consenso, sobre classe de resultado (3 classes) e, se viável, sobre associação; reportar também concordância bruta e matriz de discordância. Kappa é sensível à prevalência e ao viés de marginais.
- Discordâncias resolvidas por regra pré-registrada. Casos não são removidos depois de rodar o sistema.
- Relação entre classe pretendida pelo gerador e anotação independente: D4.

## 7. Métricas, unidade de análise e denominadores

Condicional a D1 (OPEN-01). Sob a proposta atual: unidade de classificação = **registro curricular**; unidade de associação = **par (registro, documento)**.

**Exp. 1 — extração.** Unidade: (documento, campo) do schema, agregada por documento e por família. Por campo, cada célula cai em exatamente uma categoria:

| Gabarito → Saída | Categoria |
| --- | --- |
| valor → mesmo valor | correto |
| valor → outro valor | incorreto |
| valor → `None` | omitido |
| `None` → valor | espúrio |
| `None` → `None` | ausente correto |

Proposta: precisão = correto / (correto + incorreto + espúrio); revocação = correto / (correto + incorreto + omitido); acurácia de campo e F1 derivados. Primária por documento: "todos os campos essenciais corretos" (binário, serve ao McNemar). "Igual" exige critério de normalização mínimo, declarado antes do piloto e igual para os dois métodos (D7). Reportar exato literal e equivalente. Carga horária comparada como `Decimal`.
Falhas (API, JSON inválido, ilegível): taxa por tipo; métricas condicionais a resposta válida **e** com falha contada como omissão (qual é primária: D7).
Variância (#53): para cada documento e campo, concordância entre as 3 execuções; proporção de campos instáveis; métrica por execução com média e amplitude.

**Exp. 2 e 3 — classificação.** Unidade: registro curricular. Denominador: **todos** os registros do XML dos casos avaliados, incluindo `SEM_COMPROVANTE`. Matriz 3×3, precisão/revocação/F1 por classe, Macro-F1 = média simples dos 3 F1. Classe sem exemplos previstos: F1 = 0 com aviso explícito (`zero_division` declarado). Secundária: Inconclusivo com e sem `SEM_COMPROVANTE`, porque esse motivo é trivial e infla a revocação da classe, e quebra por motivo.
**Associação (#65)**, separada da matriz: acurácia por registro (associou ao documento correto ou, corretamente, a nenhum) e precisão/revocação de pares. Par proposto incorreto = falso positivo; par verdadeiro não proposto = falso negativo. Documentos órfãos: contados como falso positivo se associados; também reportados em `DOCUMENTO_NAO_ASSOCIADO`, fora da matriz 3×3.
**Erro propagado (Exp. 3):** classe correta incondicional e condicional a associação correta; erros agrupados por causa (extração, associação, regra). `Divergente` pressupõe associação prévia (#38): registro mal associado que vira `Divergente` é erro de associação, não de regra.
**Revisão humana (AD-013).** Encaminhar todos os inconclusivos; permitir revisão de validados/divergentes por solicitação. Preservar associação, classe, motivos e evidências automáticos originais. Parecer manual, associação corrigida, revisor, data e justificativa ficam separados. Métricas automáticas usam somente o resultado anterior à revisão; eventual avaliação após intervenção é separada e não constitui experimento adicional aprovado. Implementação futura na API/interface.

**Repetições idênticas.** Conforme orientação do usuário, resultados idênticos das três execuções contam como uma observação do caso nas métricas, preservando as três saídas para registrar estabilidade. Não multiplicar a amostra por três. A regra para execuções diferentes permanece pendente em D8.

**Tempo, tokens, custo:** variáveis a medir (§9), não metas.

## 8. Estatística

| Técnica | Unidade e uso proposto | Limites |
| --- | --- | --- |
| **Bootstrap IC** (#45) | Reamostrar por **família** (cluster), nunca por caso nem por repetição. No Exp. 1, a família leva suas 3 execuções. Recalcular Macro-F1/F1/precisão a cada réplica. Nível, número de réplicas, semente e percentil: D8 | Poucas famílias → IC instável e sujeito a viés; classe ausente na réplica exige regra (ex.: estratificar por classe); reportar nº de famílias |
| **McNemar** (#67) | Pares métodos nas mesmas unidades; resposta binária acerto/erro por unidade. Exp. 2: Proposto × A, Proposto × B. Exp. 1: Gemini × OCR+regex (por documento). Reportar contagens discordantes b e c; versão exata com poucas discordâncias | Testa só homogeneidade marginal de acerto, **perde qual classe errou**; não é multiclasse, só reduz o problema a acerto/erro; exige o mesmo conjunto de unidades e saída para todas (falha = erro ou exclusão, regra prévia); assume independência entre unidades, que famílias violam (analisar no nível de família ou declarar); múltiplos testes pedem correção ou declaração (D8) |
| **Kappa** | §6 | Ver §6 |
| **Repetições** | Ver §7 (variância); McNemar usa uma regra pré-definida para colapsar 3 execuções em binário (ex.: maioria, ou todas corretas) | A regra muda o resultado; reportar sensibilidade |

Declarações obrigatórias: efeito de poucos casos por classe; nenhuma afirmação de superioridade sem teste; valor-p não substitui análise de erros. Poder estatístico não foi calculado.

## 9. Artefatos, reprodutibilidade e orçamento

**Estrutura proposta** (lógica; caminhos finais dependem de D10):

```text
data/synthetic/{pilot,final}/{xml,docs}/   # IDs neutros, sem rótulo no nome ou metadados
data/synthetic/manifest.csv                # case_id, partition, family_id, template, operador, nível, degradação, classe/motivo esperados, SHA-256 (fora do diretório lido pelo extrator)
data/annotations/{annotator_a,annotator_b,consensus}.csv
data/ground_truth/{extraction,association,class}.json
experiments/freeze/freeze-manifest.json     # hashes: schema, prompt, regex, siglas, limiares, normalização, gerador, commit
experiments/runs/<run_id>/{config.json,env.json,raw/,predictions.csv,failures.csv,metrics.json}
experiments/README.md                       # como regenerar bancada e rodar Exp. 1–3 (#72)
```

**Registro por execução:** commit, versão de Python e das dependências, SO, semente do gerador, versão do Tesseract e pacote de idioma, ID do modelo conforme retornado pela API, versão do SDK, janela de datas, temperatura, estratégia (zero/few-shot), hash do prompt e do schema, política de retentativas (contadas, não descartadas), respostas brutas.
**Reprodução:** o núcleo (parser, motor, métricas sobre predições salvas) reexecuta sem PostgreSQL, Redis nem Gemini. Chamadas ao Gemini são reproduzidas pelas respostas brutas arquivadas, não por nova chamada (modelo de API muda; #34).
**Pré-requisitos ainda abertos:** lockfile e versão padrão do Python (docs/quality.md); `statsmodels` e `pytesseract`/binário do Tesseract não constam em `pyproject.toml`; instalação não autorizada aqui (D10).

**Orçamento = variáveis a medir** (sem valores estimados): nº de chamadas = documentos × 3 execuções × fases executadas (limite superior; casos sem comprovante não geram chamada); tokens de entrada/saída e latência por chamada; retentativas; tarifa vigente na data da execução (a registrar); tempo de OCR e do motor; esforço humano de anotação e de ajuste de prompt/regex; cotas e limites de taxa da API.

## 10. Plano mínimo e opcionais

**Mínimo** (responde às perguntas; ordem com portões):
1. Decidir D1–D8 (portão: nenhum caso gerado antes de D1–D5).
2. Definir manifesto, família e guia de anotação; gerar piloto (30) com gerador determinístico.
3. Anotação independente do piloto; Kappa; fechar gabarito.
4. Executar Exp. 1–3 no piloto (inclui as 3 execuções); ajustar prompt, regex, normalização e limiares do M2.
5. Congelar (hashes). Gerar, anotar e selar o final.
6. Execução oficial única de Exp. 1–3 no final; salvar tudo.
7. Bootstrap por família, McNemar, matrizes, análise de erros; relatório com README (#70, #72).

Dependências: M1 (parser), M2 (motor/baselines), M3 (extrator) para os passos 4 e 6.

**Opcionais** (só com decisão; não bloqueiam o mínimo):
- Jaro-Winkler e similaridade por tokens como variantes do Exp. 2 (#37; definição no M2).
- Teste cronometrado de ~10 casos, manual × sistema (#71), com limitação declarada.
- Comparações secundárias do Exp. 3: Gemini + A/B, OCR+regex + motor proposto.
- Zero-shot × few-shot; análise por nível de degradação; sensibilidade ao limiar (apenas descritiva, nunca para escolher no final).
- Kappa também sobre extração; execuções extras no final.

## 11. Decisões pendentes (por prioridade)

**Bloqueiam a geração da bancada:**
- **D1. Unidade de análise e família.** Definir unidade formal e denominadores de OPEN-01; órfãos e ambiguidade já seguem AD-006/007 e revisão segue AD-013; definir chave da família (registro-base, template ou ambos); templates e instituições do final todos vistos no piloto, parcialmente novos ou todos novos? *Recomendação:* registro curricular + par, família por registro-base, parte dos templates inéditos no final. Impacto: governa partição, IC e custo de geração.
- **D2. Tamanho e distribuição.** Número fixo do final (~90 → quanto), distribuição pelas cinco categorias (AD-012), classe/operador/nível, sem cenários "quando necessário" (#45). Piloto 12/10/8 é aproximado.
- **D3. Resolvida — meta Macro-F1 (#66, AD-008).** Usuário aprovou remover meta arbitrária e reportar desempenho observado com intervalo de confiança. PROJECT G3 atualizado. Não otimizar conjunto final para atingir resultado desejado. Método e nível do IC permanecem em D8.
- **D4. Gabarito.** Fonte da verdade (classe pretendida pelo gerador × anotação independente), quem anota, subconjunto anotado, guia, regra de discordância (OPEN-04 já propõe rotulagem independente).
- **D5. Congelamento e selagem.** O que congela; se o final é gerado antes ou depois do congelamento; quem pode abri-lo.

**Antes das execuções do piloto:**
- **D6. Modelo e prompt.** Modelo exato, versão e período (OPEN-03 propõe, sem aprovação); suporte a temperatura 0; zero- ou few-shot (e origem dos exemplos); política de retentativas.
- **D7. Extração.** Campos avaliados, critério mínimo de equivalência, tratamento de falhas no denominador, métrica primária.
- **D8. Estatística.** Nível do IC, nº de réplicas, semente, estratificação; colapso das 3 execuções para o McNemar; correção para múltiplos testes; versão exata do McNemar.
- **D9. Baselines.** Regra de associação dos baselines A/B; paridade de esforço do OCR+regex com o prompt.

**Operacionais:**
- **D10. Ambiente e publicação.** Lockfile e Python padrão; dependências `statsmodels` e Tesseract; local dos dados e artefatos; publicação da bancada ou do repositório exige autorização explícita.
- **Externa (ADMIN-01):** justificativa à CTES até 30 dias antes da defesa; prazo não depende deste protocolo.

Cada decisão aprovada deve ser registrada em STATE.md; este arquivo permanece proposta até lá.
