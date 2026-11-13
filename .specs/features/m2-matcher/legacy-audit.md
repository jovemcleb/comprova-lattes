# Auditoria estática do motor legado — 2026-11-13

Referência apenas; código legado não foi executado nem importado. Esta inspeção não é auditoria exaustiva nem aprovação do motor M2.

## Achados confirmados

- `references/legacy-drive/sharing/lattes_validator/motor_cruzamento.py:156`: contenção entre títulos normalizados eleva similaridade a pelo menos 0.90. String vazia está contida em qualquer string; ausência pode virar compatibilidade. M2 deve testar ausência antes da similaridade e nunca tratar vazio como evidência positiva.
- Mesmo arquivo, linhas 296–314: cada registro recebe candidato de maior score sem mínimo de associação, sem detecção de empate e sem consumo do documento. Isso pode forçar associação incorreta, reutilizar comprovante e omitir registros quando não há documento. Não reaproveitar esse fluxo; aplicar AD-004 a AD-007.
- `levenshtein.py:155`: duas strings normalizadas vazias retornam similaridade 1.0. Evita divisão por zero, mas precisa de camada de evidência que distinga ausência de igualdade; testar campos que normalizam para vazio.
- `levenshtein.py:106`: contenção institucional genérica é aceita como equivalência. M2 precisa regra explícita de siglas/identidade; mero fragmento comum não comprova mesma instituição.
- `motor_cruzamento.py:26` e demais constantes: limiares fixos legados não têm evidência de calibração nesta inspeção. Não adotá-los como valores científicos aprovados; calibrar piloto e congelar antes da avaliação final.

## Reaproveitamento possível

- Normalização textual e distância de edição como referência para funções puras novas, com testes independentes.
- Dicionário de siglas somente após verificar entradas e documentar escopo; não herdar regra de contenção irrestrita.
- Evidências por campo como conceito; sem tratar score de similaridade como probabilidade calibrada.

## Regressões obrigatórias propostas

Título ausente; ambos campos vazios após normalização; candidato único incompatível; nenhum documento; documento órfão; empate; dois registros disputando comprovante; instituições distintas com fragmento comum; mutação factual versus variação legítima. Regras ainda não aprovadas da proposta M2 não são implementação.
