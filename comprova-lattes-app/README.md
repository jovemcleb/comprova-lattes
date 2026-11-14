# Comprova Lattes — interface React/Vite

SPA React/TypeScript/Tailwind conectada à API FastAPI, usando React Router e TanStack Query existentes. Implementa criação, acompanhamento, auditoria M1 → M3 → M2 e revisão humana AD-013. Estado científico e limites em [STATE](../.specs/project/STATE.md).

## Desenvolvimento

Na pasta `comprova-lattes-app/`, com Node/npm e dependências já instaladas:

```powershell
npm run dev
```

## Verificação

```powershell
npm run lint
npm run build
```

Em 2026-11-13, ambos executados com exit code 0. Build inclui TypeScript e React Compiler. Smoke checks Node executados em memória verificaram base64 binário, validação de configuração/MIME, contratos de POST e recuperação do ID no erro 503; renderização React SSR verificou as três rotas e auditoria concluída com encaminhamento AD-013. Isso não substitui teste visual/interativo em navegador nem integração com serviços reais.

## Conexão e rotas

O padrão é `http://localhost:8000`. Para outra API, defina `VITE_API_BASE_URL` antes de iniciar o Vite (variável pública, nunca uma credencial):

```powershell
$env:VITE_API_BASE_URL = 'http://localhost:8000'
npm run dev
```

- `/`: saúde (`GET /health`), consulta por ID e histórico. A API fornece páginas ascendentes sem total; o serviço percorre páginas de 100 itens, ordena globalmente por data decrescente e a UI pagina em grupos de 20. Atualização a cada 10 s; esse acesso deve ser revisto se o histórico crescer muito.
- `/validacoes/nova`: `POST /validations`, XML de arquivo como `xml_base64` preservando bytes/encoding ou texto como `xml_content` UTF-8. Declaração de outra codificação no texto é rejeitada para evitar interpretação incorreta; prefira arquivo. Até 100 comprovantes PDF/PNG/JPEG/WebP em base64, IDs estáveis por posição do lote enviado. Limites locais: XML 10 MiB e documento 21 MB; o servidor também valida.
- `/validacoes/:validationId`: `GET /validations/{id}`, polling de 2 s em PENDING/PROCESSING e atualização manual. Estados FAILED/DISPATCH_FAILED não são reenviados. Erro 503 na criação oferece link para o ID já persistido, evitando duplicação silenciosa.

O JSON `MatcherConfig` é integralmente editável: thresholds, mode, text_metric, acronym_table, acronym_table_version e calibration_metadata. Os limiares começam como `null` e precisam ser preenchidos explicitamente; não representam calibração aprovada. São validados intervalo, associação positiva, ordem low/high, modos, métrica e estrutura. A API continua sendo a autoridade final de validação.

S2 acrescenta “Preencher exemplo operacional” com parâmetros ilustrativos e aviso explícito de ausência de calibração aprovada. “Limpar limiares (null)” restaura o template completo inicial, inclusive tabela de siglas e metadados. Comprovantes são acumulados a cada seleção, sem duplicatas por nome+tamanho; há remoção individual e “Limpar comprovantes”. Após remover/limpar, o mesmo arquivo pode ser selecionado novamente.

## Auditoria e revisão

Sumários automático e após revisão aparecem separadamente, como contagens operacionais. Registros incluem proveniência M1, evidências brutas/normalizadas, similaridade, diferença numérica, regra e justificativa, candidatos de ambiguidade e entidades M3 completas. Documentos originais têm download e prévia (PDF depende do suporte do navegador). Diagnósticos, encoding, variantes e elementos desconhecidos ficam no painel M1; órfãos `DOCUMENTO_NAO_ASSOCIADO` permanecem fora da matriz 3 × 3.

Inconclusivos com `review_required` abrem o encaminhamento. VALIDADO/DIVERGENTE permitem solicitar revisão. O formulário envia `POST /validations/{id}/records/{record_index}/review`, com revisor e justificativa não vazios, parecer, documento associado de qualquer origem no lote e rejeições sem contradição. Histórico e último parecer são exibidos, preservando resultado/evidências automáticos. Identidade declarada, sem autenticação; não é um registro imutável contra administração do banco.

Ao solicitar nova revisão, parecer, associação e rejeições são restaurados do último estado persistido recebido do servidor; uma associação humana explicitamente nula permanece nula. A mensagem de salvamento anterior é limpa ao reabrir.

## Organização e limites

`src/types/` espelha contratos; `src/lib/` concentra HTTP, conversão binária e validação da configuração; `src/hooks/` concentra consultas/mutações e preparação do upload; `src/components/` apresenta auditoria e formulários; `src/pages/` define telas. Estados de carregamento, vazio, falha e retry são explícitos.

Hospedagem da SPA precisa encaminhar rotas desconhecidas ao `index.html`. CORS da API deve permitir a origem do Vite (padrão localhost/127.0.0.1:5173). `/health` não comprova banco, Redis, worker ou Gemini disponíveis. A submissão de comprovantes pode acionar o Gemini configurado no backend; use dados sintéticos autorizados. Nenhum serviço real ou documento pessoal foi usado nesta entrega; não há alegação de calibração científica nem de avaliação experimental concluída.
