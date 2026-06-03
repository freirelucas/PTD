# Metadados em padrões de dados abertos

O corpus PTD é publicado com um conjunto de descritores em padrões abertos,
gerados de forma reprodutível por [`build_metadata.py`](build_metadata.py) a
partir de fontes únicas da verdade (sem duplicação manual):

| Fonte | Fornece |
|---|---|
| `CITATION.cff` | autoria, licença, versão, keywords, resumo |
| `output/manifest.json` | proveniência: commit do pipeline, data, `sha256` e bytes por arquivo |
| `output/*.csv` | nomes de coluna (schema) |
| `output/vocabulary_mapping.csv` | rótulos canônicos (`prefLabel`) + variantes (`altLabel`) |

Regenerar: `make metadata` (ou `python build_metadata.py`).
Verificar se os artefatos commitados estão em dia: `python build_metadata.py --check`.

## Artefatos gerados

| Arquivo | Padrão | Para quê |
|---|---|---|
| `output/datapackage.json` | **Frictionless Data Package** + Table Schema | Torna os CSVs auto-descritivos (tipos, enums, `primaryKey`, `foreignKeys`) e validáveis com `frictionless validate`. |
| `output/metadata/schema_org_dataset.jsonld` | **schema.org/Dataset** (JSON-LD) | Descoberta pública (Google Dataset Search). Também embutido no `<head>` do `index.html`. |
| `output/metadata/dcat.jsonld` | **DCAT-AP** + tema **VCGE** | Interoperabilidade com o ecossistema gov.br / dados.gov.br. |
| `output/metadata/vocabulary.skos.jsonld` | **SKOS** ConceptScheme | Publica as escalas e produtos canônicos como vocabulário reusável/linkável. |
| `output/metadata/schemas/{risks,deliveries}.schema.json` | **JSON Schema** (2020-12) | Contrato dos `.json` aninhados, validável em CI. |
| `output/metadata/prov.jsonld` | **W3C PROV-O** | Linhagem: PTDs do portal SGD → pipeline → outputs (com `sha256`). |
| `output/metadata/ckan_package.json` | payload **CKAN** | Corpo pronto para publicação no dados.gov.br (ver abaixo). |

### Chaves e integridade referencial

O Table Schema declara `organs.sigla` como `primaryKey` e
`risks.orgao_sigla` / `deliveries.orgao_sigla` como `foreignKeys` para
`organs.sigla` — `frictionless validate` checa a integridade referencial
entre os recursos.

### Vocabulário canônico (SKOS)

`vocabulary.skos.jsonld` expõe cinco `ConceptScheme` (eixos, produtos,
probabilidade, impacto, tratamento). Cada termo canônico vira `skos:prefLabel`
e as variantes capturadas dos PDFs viram `skos:altLabel`. As escalas ordinais
(probabilidade, impacto) recebem `skos:notation` posicional (1…5).

## Validação em CI

A validação roda dentro do `pytest` (workflow `tests.yml`), sem etapa
separada:

- `test_committed_artifacts_are_in_sync` — equivale a `--check`: falha se os
  descritores commitados divergem do gerador.
- `test_datapackage_validates_with_frictionless` — valida o Data Package + dados.
- `test_json_outputs_validate_against_schema` — valida `risks.json`/`deliveries.json`.

## Nota de qualidade: o que a validação revelou

Aplicar enums canônicos via Table Schema **expôs ~43 linhas** com valores não
canônicos vazados para `*_normalizado` em riscos (artefatos de *column-bleed*:
fragmentos como `de de Ocor-`, `1-Alto`, ou listas de ações inteiras). **Todas
já estão marcadas com `needs_review=True`** — confirmando que a fila de revisão
captura esses casos.

Por isso, os campos de escala de risco (`probabilidade_normalizada`,
`impacto_normalizado`, `tratamento_normalizado`) documentam a escala canônica na
descrição **sem** enum rígido: o contrato canônico vale para o subconjunto
`needs_review=False`. Os campos limpos (`eixo_normalizado`, `tabela_tipo`,
`*_method`, `extraction_confidence`) mantêm enum rígido.

## Publicar no dados.gov.br (CKAN)

`output/metadata/ckan_package.json` é o corpo de uma requisição
`package_create` da API CKAN. A publicação **não** é automatizada aqui — exige
credenciais e autorização institucional. Quando autorizado:

1. Ajustar `owner_org` para o slug real da organização no portal.
2. Confirmar os termos VCGE em `extras.tema_vcge`.
3. `POST {PORTAL}/api/3/action/package_create` com header `Authorization: <API_KEY>`
   e o JSON como corpo.

Referências: [Frictionless Data](https://specs.frictionlessdata.io/) ·
[schema.org/Dataset](https://schema.org/Dataset) ·
[DCAT-AP](https://semiceu.github.io/DCAT-AP/releases/3.0.0/) ·
[VCGE](http://vocab.e.gov.br/) ·
[SKOS](https://www.w3.org/TR/skos-reference/) ·
[PROV-O](https://www.w3.org/TR/prov-o/) ·
[JSON Schema](https://json-schema.org/).
