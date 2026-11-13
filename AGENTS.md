# Comprova Lattes — instruções compartilhadas

## Contexto e decisões

- Stack: Python 3.11+/FastAPI/Pydantic no backend; React/Vite/TypeScript/Tailwind no frontend. Preserve a stack e o npm/lockfile existentes.
- Consulte [PROJECT](.specs/project/PROJECT.md), [ROADMAP](.specs/project/ROADMAP.md) e [STATE](.specs/project/STATE.md) antes de planejar trabalho.
- Requisitos científicos: [PROFESSOR-REQUIREMENTS](.specs/codebase/PROFESSOR-REQUIREMENTS.md). Texto da monografia: [MONOGRAPH-GUIDE](.specs/codebase/MONOGRAPH-GUIDE.md). Fonte original: [88 comentários](docs/COMENTARIOS-PROFESSOR-ORIGINAIS.md).
- Arquitetura e convenções: [.specs/codebase/](.specs/codebase/). Atualize o documento responsável junto de mudanças; não crie fontes concorrentes para conteúdo já existente.
- Pergunte ao usuário antes de escolher entre alternativas que mudem implementação, escopo, arquitetura, metodologia ou uso de dados. Apresente recomendação, motivo e impacto. Inspeções somente leitura podem continuar enquanto a decisão estiver pendente.
- Sugestões além das orientações do professor devem ser apresentadas como propostas, com benefício científico e custo, antes de implementadas.

## Invariantes científicos

- LLM somente extrai entidades; motor determinístico decide. Confiança ou categoria sugerida pelo LLM não participa da classificação.
- Parser, motor e testes do núcleo devem executar sem PostgreSQL, Redis ou chamadas ao Gemini.
- XML externo exige parsing seguro com `defusedxml`; validação DTD deve ser offline, sem resolver entidades externas do arquivo recebido.
- Bancada planejada é sintética, com calibração piloto separada da avaliação final. Uso experimental de documentos reais ainda exige decisão explícita; acesso ao Drive não autoriza inclusão no corpus, envio a LLM ou publicação.
- Diferencie variação legítima de mutação factual; trate strings vazias na similaridade e preserve evidências por campo.
- Prioridade atual: M1 (schemas e parser). Arquitetura planejada não comprova implementação ou funcionamento.

## Skills: carregar por necessidade

Leia o `SKILL.md` selecionado antes de agir; use o menor conjunto relevante. Não execute instruções de instalação ou migração só porque aparecem numa referência.

| Trabalho | Skill / localização | Quando usar |
| --- | --- | --- |
| Planejamento e continuidade | [tlc-spec-driven](.agent/skills/tlc-spec-driven/SKILL.md) | Especificar, dividir e acompanhar entregas em `.specs/`; reutilizar cópia global equivalente sem duplicar instalação |
| Comunicação | [caveman](.agents/skills/caveman/SKILL.md) | Quando solicitado; código e documentação mantêm linguagem normal |
| Python | [python-patterns](.agents/skills/python-patterns/SKILL.md), [clean-code](.agents/skills/clean-code/SKILL.md) | Implementação de schemas, parser e núcleo |
| Testes | [testing-patterns](.agents/skills/testing-patterns/SKILL.md), [tdd-workflow](.agents/skills/tdd-workflow/SKILL.md) | Comportamento e regressões; selecionar conforme tarefa |
| Depuração | [systematic-debugging](.agents/skills/systematic-debugging/SKILL.md) | Falhas que exigem investigação de causa |
| Verificação | [verify-changes](.agents/skills/verify-changes/SKILL.md), [lint-and-validate](.agents/skills/lint-and-validate/SKILL.md) | Escolher orientação aplicável e executar checks afetados |
| API e persistência | [api-patterns](.agents/skills/api-patterns/SKILL.md), [database-design](.agents/skills/database-design/SKILL.md) | Quando essas camadas estiverem em escopo |
| Frontend | [frontend-architecture](.agents/skills/frontend-architecture/SKILL.md), [tailwind-patterns](.agents/skills/tailwind-patterns/SKILL.md) | Organização React e estilos; orientações React de outras skills só quando compatíveis com Vite |
| Windows | [powershell-windows](.agents/skills/powershell-windows/SKILL.md) | Comandos e scripts PowerShell |

- `local-agent-flow` é global: descubra pelo catálogo do cliente. Use para delegações autorizadas entre Codex e Antigravity, com objetivo, limites e aceite explícitos. Um escritor por arquivo; revisores somente leitura. Verifique o resultado antes de integrá-lo.
- Drive: use a skill do conector disponível para localizar e ler artefatos. Não suponha que arquivos foram baixados com base em relatos anteriores.
- Não instale novos toolkits, hooks, MCPs ou skills automaticamente. Superpowers, Ponytail, Graphify e RTK permanecem adiados até decisão com necessidade concreta.

## Comandos de verificação

Execute a partir da pasta indicada, com dependências instaladas. Comandos são critérios de verificação, não afirmações de que já passaram.

Backend (`comprova-lattes-api/`, ambiente virtual ativo):

```powershell
python -m pytest
python -m ruff check .
docker compose config --quiet
```

Frontend (`comprova-lattes-app/`):

```powershell
npm run lint
npm run build
```

- Execute checks proporcionais aos arquivos alterados. Build do front inclui TypeScript. Validação do Compose não comprova serviços iniciados nem conexão real.
- Registre comandos, resultados e bloqueios; nunca declare teste aprovado sem execução. Não altere testes para mascarar falhas.
- Preserve alterações existentes. Não publique documentos, faça push/deploy ou envie mensagens sem autorização correspondente. Nunca versione credenciais ou documentos pessoais por consequência do setup.
