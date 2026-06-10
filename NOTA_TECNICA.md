# Nota Técnica — Corpus dos Planos de Transformação Digital

> **Versão**: 0.1.0-preview (maio/2026)
> **Status**: Versão preliminar. Conteúdo de domínio marcado `TODO:` ainda a preencher pelos autores.
> **Como citar**: ver [`CITATION.cff`](CITATION.cff)

---

## Resumo

> TODO: 2 parágrafos resumindo (i) o que é o corpus, (ii) como foi construído, (iii) achados principais, (iv) limites. Estilo abstract de paper.

---

## 1. Marco legal e institucional

O Plano de Transformação Digital (PTD) é instrumento de planejamento e pactuação instituído pelo **Decreto nº 12.198, de 24 de setembro de 2024**, no âmbito da **Estratégia Federal de Governo Digital (EFGD) 2024-2027**. A regulamentação operacional é dada pela **Portaria SGD/MGI nº 6.618/2024**, que padroniza o template do PTD em duas peças:

1. **Documento Diretivo** — declaração da estratégia digital do órgão, contendo tabela de gestão de riscos (probabilidade × impacto × tratamento + ações de mitigação).
2. **Anexo de Entregas** — tabela com serviços/ações pactuados, classificados por *produto* e *eixo* da EFGD 2024-2027.

A SGD/MGI publica os PTDs vigentes no portal `gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital`, em URLs estáveis por sigla.

---

## 2. Frame amostral e população

**Universo populacional**: órgãos da administração pública federal direta, autarquias e fundações com PTD vigente publicado no portal SGD/MGI.

**Frame amostral**: lista de URLs `ptds-vigentes/{a..z}` no portal gov.br, varrida via scraping (cell `04b_scraping.py`). O frame é **dinâmico** — o portal pode adicionar/remover órgãos.

**Procedimento de coleta**: censo, não amostragem. O pipeline busca todos os PTDs listados no portal na data de execução, sem critério de exclusão a priori.

**Data de referência da coleta**: registrada no `output/manifest.json` (campo `data_execucao`). O snapshot atual cobre **91 órgãos** signatários.

**Estabilidade temporal**: alguns PDFs no portal têm sufixos de versão (`(v2)`, `(v3)`). O pipeline pega a versão atualmente linkada — re-execuções futuras podem capturar versões diferentes. Limitação documentada na Seção 6.

---

## 3. Operacionalização das variáveis

### 3.1 Entrega pactuada (`DeliveryEntry`)

Extraída da tabela "Anexo de Entregas" do PDF de entregas, contendo:

| Campo | Definição operacional | Origem na tabela |
|---|---|---|
| `orgao_sigla` | Sigla do órgão emissor | URL do PDF |
| `tabela_tipo` | `pactuada` / `concluida` / `cancelada` | Detecção por estrutura de colunas + opcional coluna "Status" |
| `servico_acao` | Texto livre do serviço ou ação a entregar | Coluna "Serviço/Ação" |
| `produto_original` / `produto_normalizado` | Categoria de produto (escolha entre 44 canônicos) | Coluna "Produto" + canonização (Seção 4) |
| `eixo_original` / `eixo_normalizado` | Um dos 5 eixos da EFGD 2024-2027 | Coluna "Eixo" + canonização |
| `data_pactuada` | Mês/ano prometido para entrega | Coluna "Data Pactuada" / "Prazo" / "DtPactuada" |
| `data_entrega` / `pactuado` / `justificativa` | Campos para futuras tabelas concluídas/canceladas | Especulativo — ver Seção 6.3 |

### 3.2 Risco (`RiskEntry`)

Extraído da tabela de gestão de riscos do Documento Diretivo:

| Campo | Definição operacional | Escala canônica |
|---|---|---|
| `risco_texto` | Texto livre descrevendo o risco | (não-canônico) |
| `probabilidade_original` / `probabilidade_normalizada` | Probabilidade de ocorrência | 5 níveis: raro / pouco provável / provável / muito provável / praticamente certo |
| `impacto_original` / `impacto_normalizado` | Impacto se ocorrer | 5 níveis: muito baixo / baixo / médio / alto / muito alto |
| `tratamento_original` / `tratamento_normalizado` | Opção de tratamento | 4 níveis: mitigar / eliminar / transferir / aceitar |
| `acoes_tratamento` | Texto livre das ações específicas | (não-canônico) |

### 3.3 Unidade de observação e dedup por grupo

Sete grupos ministeriais publicam **um único PDF** para múltiplos órgãos: MD, MEC, MF, MMA, MT, MIDR, MDA (definidos em `ORGAN_GROUPS` em `notebook_cells/02_config.py`). Para evitar dupla contagem:

1. PDFs são deduplicados por hash MD5 do arquivo.
2. Entries são atribuídas ao **owner do dedup** (sigla alfabeticamente menor no grupo).
3. Estatísticas de cobertura **propagam** o status do owner para todos os membros do grupo.

> **Decisão metodológica relevante**: a unidade de observação é o **órgão signatário**, mas a unidade de dados é o **PDF compartilhado**. Análises agregadas tratam membros do grupo como cobertos (87% de cobertura inclui 22 órgãos com dados compartilhados).

---

## 4. Procedimentos de extração e canonização

### 4.1 Pipeline em 13 etapas (cells `00`–`13b`)

```
01 setup → 02 config → 03 utils → 04 scraping →
05 download → 05c dedup MD5 → 06 PyMuPDF setup →
07 extract risks → 08 extract deliveries →
09 standardize (canonização + filtro de fragmentos) →
10 export CSV/JSON →
11 statistics + dashboard data + review queue +
   insumos da NT (11e, gerador reproduzível) →
13 validation report → 13c bundle de publicação
```

Detalhes em [`DECISIONS.md`](DECISIONS.md).

### 4.2 Canonização em camadas

Para reduzir a heterogeneidade do vocabulário usado pelos 91 órgãos, cada campo categórico passa por:

1. **Match exato** (score 1.0) — texto normalizado bate com canônico
2. **Alias determinístico** (score 0.95–0.98) — texto bate com chave conhecida em `*_ALIASES` (mapas em `02_config.py`)
3. **Fuzzy match** via `difflib.SequenceMatcher` (Ratcliff/Obershelp) — score ≥ 0.85 = `fuzzy_high`, 0.70-0.85 = `fuzzy_low`
4. **Fallback**: marca `needs_review=True`, preserva `*_original` para auditoria

**Métodos de classificação** (campo `*_method` de cada entry):
- `exact` | `alias` | `fuzzy_high` | `fuzzy_low` | `unmatched`

Cardinalidade do bucket de método é **fixa em 5** — não cresce com adição de aliases.

### 4.3 Cross-validation produto ↔ eixo

Para entregas, se o produto canonizado existe em `PRODUTO_TO_EIXO` (mapa produto→eixo definido pela SGD), o eixo é **forçado** ao canônico desse produto, mesmo que a coluna eixo original diferisse. No snapshot 2026-05, 2.209 entregas (48,3%) carregam esse flag (needs_review total: 58,6%) — o flag indica "eixo ajustado por cross-validation", não "entrega errada". Em 49,8% dos registros a coluna de eixo nem existe no PDF e o eixo é derivado inteiramente do produto.

> TODO: explicar por que aceitamos essa intervenção (confiabilidade do mapeamento SGD) e qual o risco (perda de eixos não-padrão usados por órgãos específicos).

### 4.4 Thresholds de qualidade (`QUALITY_THRESHOLDS`)

Asserts em `11b_statistics.py` abortam o pipeline se canonization rate cair abaixo de:
- Probabilidade: 85%
- Impacto: 85%
- Tratamento: 80%
- Entregas totais ≤ 4700 (margem de +3% sobre baseline)
- Riscos totais ≤ 700 (margem de +13% sobre baseline)

Valores atuais (snapshot maio/2026): 97.6% / 97.1% / 94.3% — folga confortável.

> TODO: justificar a escolha de 0.85/0.70 como cutoffs. Mencionar sensitivity analysis como follow-up (Seção 6).

### 4.5 Publicação em padrões abertos e harmonização

Os artefatos de `output/` são publicados com descritores em padrões abertos,
gerados de forma reprodutível por `build_metadata.py` a partir de `CITATION.cff`,
`manifest.json` e os próprios CSVs: **Frictionless Data Package** (Table Schema
com tipos, chaves e integridade referencial), **schema.org/Dataset** (descoberta
via Google Dataset Search), **DCAT-AP** com tema **VCGE**, vocabulário **SKOS**
(escalas e produtos canônicos), **JSON Schema** e **PROV-O** (linhagem). A
validação roda no `pytest` (`frictionless` + `jsonschema` + checagem de
consistência).

Aplicar enums canônicos na validação revelou um resíduo de 43 valores não
canônicos nas colunas `*_normalizado` de riscos (column-bleed e compostos), dos
quais 17 (em `tratamento`) não haviam sido capturados pela fila de revisão. A
**visão harmonizada** (`output/harmonized/`, via `build_corpus.py`) resolve esse
resíduo de forma reversível: as colunas normalizadas ficam estritamente
canônicas, o valor cru permanece em `*_original`, cada alteração é registrada em
`harmonization_report.json`, e as linhas afetadas são re-sinalizadas. É uma
camada de *post-processing* sobre os dados publicados — não substitui a correção
na origem (Seção 6.2), que depende de re-execução do pipeline.

---

## 5. Reprodutibilidade

### 5.1 Determinismo

- Pipeline é **determinístico**: mesmo conjunto de PDFs → mesmo output, bit-exact via MD5.
- `output/validation_report.json` registra MD5 de todos os CSVs/JSONs publicáveis a cada execução.
- `manifest.json` registra o commit hash do pipeline (`pipeline_commit`).
- Re-execução em máquina diferente com mesmo commit + mesmos PDFs no Drive produz mesmo output.
- Os **insumos da Nota Técnica** (`output/nota_tecnica_insumos.md`) são gerados
  pela célula `11e` a partir dos CSVs, sem timestamp embutido (carimbo vem do
  manifest) — regenerar sobre o mesmo snapshot produz bytes idênticos, e o
  teste `test_insumos_commitado_consistente_com_csvs` falha se o arquivo
  commitado divergir dos dados (proíbe edição manual de números).
- O CI valida a cadeia inteira: notebook ≡ células, checksums de `output/`,
  derivados (`build_metadata.py --check` / `build_corpus.py --check`) e a
  paridade dos insumos.

### 5.2 Como reproduzir

O projeto adota **uma única fonte de código** (`notebook_cells/*.py`); o
notebook Colab é **gerado** dela (`build_notebook.py`) e o CI bloqueia
qualquer divergência. As três vias abaixo executam exatamente o mesmo
pipeline:

```bash
# Via A: Google Colab — transparência científica (auditável no navegador,
# sem instalar nada; 1 clique no badge do README → Run All).
# PDFs persistem em MyDrive/PTD_Scraper/; cell 13c gera o bundle.

# Via B: Headless local — mesma execução, fora do Jupyter
git clone https://github.com/freirelucas/PTD
cd PTD
pip install -r requirements.txt
python run_pipeline.py --sync    # roda as células em sequência, aplica o
                                 # gate de qualidade e regenera output/ +
                                 # derivados + index.html

# Via C: CI — o workflow monthly-refresh.yml executa a Via B num runner
# do GitHub todo mês e abre PR com o diff de dados para revisão humana.
```

Métricas derivadas também são reproduzíveis isoladamente, sem rede:

```bash
python notebook_cells/11e_nt_insumos.py output   # insumos da NT ← CSVs
python build_metadata.py && python build_corpus.py  # descritores e harmonizado
```

### 5.3 Versionamento

- Versões de Python: 3.11+ (CI testa em 3.11)
- Dependências com bounds bilaterais em `requirements.txt` (ver Seção 6.4)
- Snapshots versionados por tag git + DOI Zenodo (a partir da v1.0)

---

## 6. Limitações declaradas

### 6.1 Extração tabular incompleta

As lacunas diferem por dimensão (snapshot 2026-05, `coverage_summary.csv`):

- **Entregas — 12 órgãos sem dados extraíveis** (PDF escaneado ou layout
  não-padrão): AGU, CODEVASF, FUNAI, FUNDACENTRO, INCRA, ITI, MCOM, MIDR,
  SGPR, SUDAM, SUDECO, SUDENE. Cobertura: 79/91 (86,8%).
- **Riscos — 10 órgãos com Documento Diretivo sem tabela de riscos
  extraível**: AGU, ANVISA, FBN, FCP, FUNAI, INCRA, ITI, MAPA, MCOM, PREVIC;
  **5 sem Documento Diretivo publicado**: ABIN, ANTT, DNIT, MDIC, MT.
  Cobertura: 76/91 (83,5%).

Os casos aparecem no dashboard com a tag `⚠ extração falhou`. Note que as
listas não coincidem (ANVISA tem o máximo de entregas do corpus e nenhuma
tabela de riscos; CODEVASF tem riscos e nenhuma entrega).

### 6.2 Tail de canonização não-resolvido

**27 riscos (4,4%) sem probabilidade∧impacto canônicos** (column-shift,
header capturado, fragmentação por quebra de página): DNOCS (6), MPOR (5),
CVM (4), CADE (3), CENSIPAM (3), MJSP (2), IBAMA (1), IBGE (1),
MMULHERES (1), PRF (1). Tratamento fora da escala em 17 registros. Visíveis
na tab "Revisão" do dashboard.

**531 entregas (11,6%) têm produto canonizado via `fuzzy_high`** — score
alto mas não exato, em geral truncamentos de célula do PDF. Os 12 aliases
determinísticos adicionados em jun/2026 (`02_config.py`) cobrem ~430 desses
casos a partir do próximo run; a ferramenta da tab "Revisão" → "Curadoria"
permite converter os demais.

### 6.3 Tabela_tipo especulativa

Detector de `concluida` / `cancelada` (`_classify_tabela_tipo` em `08b`) foi adicionado defensivamente — todos os PTDs atuais (primeiro ciclo) só têm tabela `pactuada`. Quando o gov.br publicar PTDs com seções de entregas concluídas/canceladas (esperado em 2027), o pipeline deve capturar. **Não validado fim-a-fim com PDFs reais.**

### 6.4 Datas de assinatura por proxy

O pipeline **não captura data de assinatura real do PTD** — o portal gov.br não expõe data de publicação no scraping atual, e `pypdf` falha em ler `creation_date` da metadata dos PDFs gov.br. O gráfico "Cronologia de Adesão" usa **1ª `data_pactuada` parseável por órgão** como proxy. Limitações:

- Apenas **57 de 91 órgãos** têm 1ª data parseável após propagação por grupo. Os outros 34 têm PDF mas zero entries com `data_pactuada` populada — coluna vazia no PDF original.
- 30 órgãos têm 1ª pactuação **anterior ao decreto** (24/09/2024). Investigação caso a caso mostra que vêm de entregas legadas retroativamente incluídas (predominantemente "PPSI Ciclo 1", política que antecede o PTD). Out/2023 tem cluster anômalo de 11 órgãos pela mesma razão.

> TODO: discutir o impacto disso pra interpretação do gráfico. Sugerir como mitigar em v2 (scraping da data de publicação do portal).

### 6.5 Validação externa ausente

A canonização não foi cross-validada contra:
- Relatório oficial SGD/MGI (se existir)
- Amostra revisada manualmente com inter-rater reliability (Cohen's κ)

> TODO: incluir validação cruzada antes de submissão a revista. Amostra de 10-15 PDFs revisados por humano com cálculo de precision/recall por campo é viável em ~4h.

### 6.6 Sensitivity dos thresholds

Os thresholds de canonização (0.85 / 0.70) e os limites de regressão em `QUALITY_THRESHOLDS` foram escolhidos empiricamente. **Não há sensitivity analysis** mostrando como métricas variam com thresholds diferentes.

> TODO: incluir em v2.

### 6.7 Texto livre subutilizado

`risco_texto` (619 instâncias) e `servico_acao` (4574 instâncias) têm conteúdo qualitativo. **Hoje não há análise de NLP, clustering, ou topic modeling** desse texto. A análise é puramente estrutural sobre campos categóricos.

---

## 7. Decisões metodológicas registradas

Detalhes em [`DECISIONS.md`](DECISIONS.md):

- §2.1 Dedup MD5 versionado
- §2.2 Cobertura de grupo por peers
- §2.4 Cross-validation produto ↔ eixo
- §2.5 Aliases de escalas heterogêneas (ANTAQ, SUSEP, CADE)
- §2.7 PyMuPDF vs Docling
- §2.8 Camada 1.5 (aliases preventivos + strip de prefixo enumerativo)
- §2.11 Tabela_tipo especulativa (concluida/cancelada/pactuada)

---

## 8. Artefatos publicados

| Arquivo | Conteúdo |
|---|---|
| `output/deliveries.csv` / `.json` | 4574 entregas com produto+eixo canonizados + scores |
| `output/risks.csv` / `.json` | 619 riscos com prob/impacto/tratamento canonizados |
| `output/organs.csv` | 91 órgãos signatários com URLs e paths de PDF |
| `output/error_report.csv` | Falhas de extração registradas |
| `output/validation_report.json` | Métricas de qualidade, MD5 dos outputs, fingerprints de checkpoint |
| `output/review_data.json` | Fila de revisão humana (críticos + curadoria) |
| `output/manifest.json` | Commit, data de execução, contagens agregadas |
| `output/coverage_summary.csv` | Cobertura por sigla |
| `output/pdf_metadata.csv` | Tamanho dos PDFs |
| `output/vocabulary_mapping.csv` | Mapa original → canônico aprendido na execução |
| `output/review_queue.csv` | Fila de revisão completa (todas as linhas sinalizadas) |
| `output/statistics_summary.json` | Estatísticas agregadas |
| `output/data.js` + `output/figures/` | Dados do dashboard e visualizações PNG |
| `output/nota_tecnica_insumos.md` | Insumos da NT — **gerado** pela célula `11e` (números com definição e proveniência) |
| `output/datapackage.json` + `output/metadata/` | Descritores em padrões abertos (`build_metadata.py`) |
| `output/harmonized/` | Visão estritamente canônica (`build_corpus.py`) |

Dashboard interativo: `https://freirelucas.github.io/PTD`

---

## 9. Citação

Ver [`CITATION.cff`](CITATION.cff) para formato estruturado (compatível com GitHub e Zenodo).

Sugerida (versão preliminar):

> DIREITO, Denise; SILVA, Lucas; QUEIROZ, Sérgio. *Corpus dos Planos de Transformação Digital: extração, padronização e análise dos PTDs de 91 órgãos federais brasileiros*. Brasília: Ipea, 2026. Nota técnica versão preliminar. Disponível em: https://github.com/freirelucas/PTD

Após release v1.0 + DOI Zenodo, atualizar para a forma definitiva.

---

## 10. Como contribuir / reportar erro

- **Erros de extração ou inconsistência**: abrir issue em https://github.com/freirelucas/PTD/issues
- **Endosso/disputa de dado por órgão emissor**: ainda não automatizado; via issue por enquanto
- **Pull requests bem-vindos** com:
  - Aliases novos em `notebook_cells/02_config.py`
  - Casos de teste em `tests/`
  - Correções de bugs de extração tabular
