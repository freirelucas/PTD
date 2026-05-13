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
09 standardize (canonização) → 10 export CSV/JSON →
11 statistics + dashboard data + review queue →
13 validation report
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

Para entregas, se o produto canonizado existe em `PRODUTO_TO_EIXO` (mapa produto→eixo definido pela SGD), o eixo é **forçado** ao canônico desse produto, mesmo que a coluna eixo original diferisse. Cerca de 58% das entregas têm `needs_review=True` por essa correção — flag indica "eixo ajustado por cross-validation", não "entrega errada".

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

---

## 5. Reprodutibilidade

### 5.1 Determinismo

- Pipeline é **determinístico**: mesmo conjunto de PDFs → mesmo output, bit-exact via MD5.
- `output/validation_report.json` registra MD5 de todos os CSVs/JSONs publicáveis a cada execução.
- `manifest.json` registra o commit hash do pipeline (`pipeline_commit`).
- Re-execução em máquina diferente com mesmo commit + mesmos PDFs no Drive produz mesmo output.

### 5.2 Como reproduzir

```bash
# Opção A: Google Colab (recomendado)
# 1. Abrir o link 1-clique no README → ptd_scraper.ipynb
# 2. Run All → coleta tudo no MyDrive/PTD_Scraper/
# 3. Cell 13c gera output_TIMESTAMP.zip pra download

# Opção B: Local
git clone https://github.com/freirelucas/PTD
cd PTD
pip install -r requirements.txt
jupyter execute ptd_scraper.ipynb
```

### 5.3 Versionamento

- Versões de Python: 3.11+ (CI testa em 3.11)
- Dependências com bounds bilaterais em `requirements.txt` (ver Seção 6.4)
- Snapshots versionados por tag git + DOI Zenodo (a partir da v1.0)

---

## 6. Limitações declaradas

### 6.1 Extração tabular incompleta

**11 PDFs não foram extraídos** por estarem escaneados sem OCR ou usarem template não reconhecido: AGU, ANVISA, CODEVASF, FBN, FCP, FUNAI, INCRA, ITI, MAPA, MCOM, PREVIC. Equivale a ~12% dos diretivos. Esses órgãos aparecem no dashboard com tag `⚠ extração falhou (riscos)`.

### 6.2 Tail de canonização não-resolvido

**~38 entries têm bugs de extração tabular conhecidos** (column-shift, header capturado, fragmentação por quebra de página) concentrados em DNOCS, MMULHERES, CADE. Visíveis na tab "Revisão" do dashboard, classificados como `method=unmatched`.

**~1262 entries têm canonização via `fuzzy_high`** — score alto mas não exato. Em geral são variações de redação ou pequenos truncamentos; ferramenta da tab "Revisão" → "Curadoria" permite converter em aliases determinísticos.

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
