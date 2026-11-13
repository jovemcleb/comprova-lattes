# Gramáticas XML Lattes — proveniência dos artefatos

Artefatos de referência obtidos em **2026-11-13** (data local; cabeçalhos HTTP `Date: Fri, 13 Nov 2026 05:41–05:42 GMT`) a pedido do usuário. Os arquivos originais **não foram editados** (o XSD apenas recebeu o nome de arquivo anunciado pelo servidor em `Content-Disposition`; bytes idênticos aos baixados). Análise: [grammar-analysis.md](../../.specs/features/m1-parser/grammar-analysis.md).

> [!WARNING]
> Os dois artefatos **não são equivalentes** e **não são a mesma fonte**: a DTD é uma revisão **comunitária** (não oficial) e o XSD é um documento **oficial do CNPq** que descreve o XML do **Lattes Extrator**. Nenhum dos dois comprova conformidade do XML exportado pela interface do Lattes.

**Publicação no GitHub:** somente este documento, scripts próprios em `tools/` e saídas sobre fixtures sintéticas em `analysis-output/` são versionados. Diretórios `community-dtd/` e `cnpq-official/` (incluindo downloads, páginas e metadados) são referências locais ignoradas pelo Git. Para reproduzir a validação XSD/DTD, obtenha os artefatos nas fontes abaixo, confira os hashes e mantenha os nomes/caminhos esperados. O pytest padrão do núcleo não depende desses arquivos nem de lxml. Links para esses diretórios descrevem material local, ausente no clone público.

## 1. DTD comunitária — `community-dtd/LMPLCurriculo.DTD`

| Item | Valor |
| :--- | :--- |
| Natureza | Revisão **comunitária** da DTD histórica do CNPq; o README do repositório se declara "trabalho em andamento" (`README.upstream`) |
| Repositório | https://github.com/antoanne/LMPLCurriculo (branch `master`) |
| URL baixada | https://raw.githubusercontent.com/antoanne/LMPLCurriculo/master/LMPLCurriculo.DTD (redirecionamentos: nenhum; HTTP 200; `Content-Type: application/octet-stream`; ver `LMPLCurriculo.DTD.headers.txt`) |
| Revisão (commit) | Último commit que altera o arquivo e `HEAD` de `master` na API pública: `a295d3866715960a1a977ef79c978ff7e71c4ad9` (committer date 2010-10-18T16:49:39Z, "Merge branch 'master' of git://github.com/arademaker/LMPLCurriculo into arademaker-master"). Evidência: `github-commits-DTD.json`, `github-commits-branch-head.json` |
| Blob git do arquivo | `8b78aa7c707c17136a33d8321ca8f21f6927d518` (API `contents`; **recalculado localmente a partir dos bytes baixados: confere**) |
| SHA-256 | `46f76b57d59d87556b442118cd4eb9ad0c12835f51fbe8f814e3adaefbb1c99a` |
| Tamanho | 104 976 bytes, 2 448 linhas, texto com declaração `encoding="ISO-8859-1"` |
| Licença | **Não declarada.** API `/license` → 404, `license: null` em `github-repo-metadata.json`, raiz do repositório contém apenas `LMPLCurriculo.DTD`, `README`, `validate.py` (`github-contents-root.json`). Tratar como "todos os direitos reservados" até esclarecimento. Autoria/propriedade da DTD original: CNPq (README upstream) |
| `validate.py` | **Não baixado nem executado** (script de terceiros) |

## 2. XSD oficial CNPq — `cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd`

| Item | Valor |
| :--- | :--- |
| Natureza | Documento **oficial do CNPq** listado em "Definições do XML do Extrator Lattes" na página de extração de dados, "atualizado em 12/09/2022" (`extracoes-de-dados-page.html`). O acesso ao serviço Lattes Extrator é institucional (cadastro, IP dedicado, webservice) |
| Página de origem | https://memoria.cnpq.br/web/portal-lattes/extracoes-de-dados |
| URL baixada / efetiva | https://memoria.cnpq.br/documents/313759/1ee5aab5-84eb-4551-8dc2-c99764423c33 — URL efetiva idêntica (sem redirecionamento), HTTP 200, `Content-Type: application/octet-stream` |
| Nome do arquivo (servidor) | `xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd` (`Content-Disposition`, ver `cnpq-xsd-download.headers.txt`) |
| Bytes reais | **Arquivo XML único** (inicia com `<?xml version="1.0" encoding="ISO-8859-1"?>` + `xs:schema`); **não é zip**; nenhum `include`/`import`/`redefine`, sem `DOCTYPE`/`ENTITY` — autocontido |
| Revisão/versão | Sem número de versão no documento; usa-se a data anunciada (12/09/2022) e o hash |
| SHA-256 | `06b3976943f73b4e66f4ece70c5d9358d244fc080704c518a8d533d84eea6214` |
| Tamanho | 278 941 bytes, 6 616 linhas |
| Licença | **Sem termo de licença/uso observado** nem no arquivo nem na página capturada. Status: não declarado |

## 3. Demais arquivos (metadados e ferramentas)

| Arquivo | Conteúdo |
| :--- | :--- |
| `community-dtd/github-*.json`, `README.upstream` | Metadados públicos da API do GitHub e README upstream |
| `cnpq-official/extracoes-de-dados-page.html` | Cópia da página pública que anuncia o XSD |
| `tools/` | `Dockerfile` (imagem descartável com `lxml`) e scripts de análise escritos nesta tarefa (não são código dos repositórios de terceiros) |
| `analysis-output/` | Saídas brutas das análises/validações offline |

Reprodução (a imagem é construída **com** rede só para `pip install lxml`; toda execução usa `--network none` e montagens somente leitura):

```powershell
docker build -t grammar-lxml-scratch:tmp references/xml-grammars/tools
docker run --rm --network none --read-only -v "${PWD}/references/xml-grammars:/g:ro" `
  -v "${PWD}/comprova-lattes-api/tests/fixtures/m1:/f:ro" -v "${PWD}/references/xml-grammars/tools:/s:ro" `
  -v "<pasta-de-saida>:/out" grammar-lxml-scratch:tmp python /s/validate_fixtures.py
```

(`analyze.py`/`closure.py`/`checks.py` esperam `/g` e `/s`; `analyze.py` também grava em `/out`.)

## 4. Hashes SHA-256 de todos os arquivos

```text
06b3976943f73b4e66f4ece70c5d9358d244fc080704c518a8d533d84eea6214  cnpq-official/xml_cvbase_src_main_resources_CurriculoLattes_12_09_2022.xsd
46f76b57d59d87556b442118cd4eb9ad0c12835f51fbe8f814e3adaefbb1c99a  community-dtd/LMPLCurriculo.DTD
5cdb49f725d6fe6162cd76909aa42d4f9a629aa22135c1501c94903cfdc5e101  cnpq-official/extracoes-de-dados-page.html
ee3846fb3793ddb5c6c3b1f661a773d581366dc94ec8ee2c1ff1d8e698c98871  cnpq-official/cnpq-xsd-download.headers.txt
a07d3359b472e9e2ec778b93be8ce492e45ce5015d2b67ff4e5a2fcec259fc3a  community-dtd/LMPLCurriculo.DTD.headers.txt
0593eda88da66901da721db5f76f7a2b9e1b63f34be09dfb6f121e5785c3688d  community-dtd/README.upstream
5ffe5b78a4de118cc2e81fa0dfc805b8d09f975de265ee51a85079db4d7203e9  community-dtd/github-commits-DTD.json
826fe4469265fc4daca7378bdfd780f09560081f58e88a84b43e8345a407da9a  community-dtd/github-commits-branch-head.json
5574857688a8df253c826fd0c139361d2a3a1628503bc8e2dbb21cfdf9bf7c39  community-dtd/github-contents-root.json
6c0109c2ac75f1f264b61da6aff1737f7bc7eac254e6396710ff81a4139f32b1  community-dtd/github-license.json
b4d5fd072d355582429e41b1da1b7bc4f4e5df653247afe72b3f2b5a0ed5dbf1  community-dtd/github-repo-metadata.json
```

## 5. Restrições de uso

- Não publicar nem redistribuir estes arquivos fora do repositório privado sem resolver a licença (decisão pendente no relatório).
- Não usar a DTD/XSD para habilitar resolução de DTD em XML de entrada: `defusedxml` com `forbid_dtd/entities/external` permanece obrigatório.
