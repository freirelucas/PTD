# PTD — Corpus dos Planos de Transformação Digital

Pipeline para coleta, extração e análise dos **Planos de Transformação Digital (PTDs)** dos órgãos federais brasileiros, publicados no portal [gov.br](https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital).

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb)

## Visite e explore: https://freirelucas.github.io/PTD/

## O que o corpus contém

91 órgãos federais signatários (decreto 12.198/2024). Para cada órgão são extraídos dois documentos do portal:

- **Anexo de Entregas** — tabela de produtos pactuados com a SGD/MGI, classificados por eixo da EFGD 2024-2027
- **Documento Diretivo** — tabela de gestão de riscos com probabilidade, impacto e ações de tratamento

Resultado consolidado (corpus atual):

| Métrica | Valor |
|---|---|
| Órgãos signatários | 91 |
| Entregas pactuadas | **4.574** |
| Riscos identificados | **619** |
| Cobertura entregas | 79/91 órgãos (57 próprios + 22 compartilhados) |
| Cobertura riscos | 76/91 órgãos (51 próprios + 25 compartilhados) |
| PDFs com falha de extração (provavelmente escaneados) | 10 |

Sete grupos ministeriais publicam um único PDF para múltiplos órgãos (MD/MEC/MF/MMA/MT/MIDR/MDA). O pipeline detecta isso por **hash MD5** e registra os dados uma única vez sob a sigla alfabeticamente menor; os demais membros são marcados como `compartilhado` na cobertura.

## Saídas

| Arquivo | Descrição |
|---------|-----------|
| `output/deliveries.csv` / `.json` | Entregas pactuadas, concluídas e canceladas |
| `output/risks.csv` / `.json` | Riscos identificados nos Documentos Diretivos |
| `output/organs.csv` | Lista de órgãos com URLs dos PDFs |
| `output/coverage_summary.csv` | Cobertura de extração por órgão |
| `output/error_report.csv` | Erros de processamento por órgão e estágio |
| `output/data.js` | Dados consumidos pelo dashboard interativo |
| `output/statistics_summary.json` | Estatísticas agregadas |
| `output/pdf_metadata.csv` | Metadados dos PDFs (datas, tamanhos) |
| `output/figures/` | Visualizações estatísticas (PNG) |
| `output/nota_tecnica_insumos.md` | Insumos para a nota técnica (estrutura, métricas, achados) |

O dashboard interativo está em [`index.html`](index.html). Ele consome `output/data.js` dinamicamente — não há números hardcoded.

## Como usar

### Google Colab (recomendado)

Clique no badge **Open in Colab** acima e execute as células sequencialmente. O ambiente detecta o Colab automaticamente e instala as dependências. Os PDFs são persistidos no Google Drive (`MyDrive/PTD_Scraper/`) para reutilização entre execuções.

### Execução local

```bash
git clone https://github.com/freirelucas/PTD.git
cd PTD
pip install -r requirements.txt
jupyter notebook ptd_scraper.ipynb
```

Os PDFs ficam em `ptd_output/pdfs/{diretivo,entregas}/` e os outputs em `ptd_output/output/`.

Para visualizar o dashboard:

```bash
python -m http.server
# Abrir http://localhost:8000 no navegador
```

## Pipeline

O notebook executa 13 etapas sequenciais:

1. **Setup** — Detecta ambiente (Colab/local), instala dependências
2. **Configuração** — Vocabulários canônicos, ORGAN_GROUPS, dataclasses
3. **Utilitários** — Rede, normalização, fuzzy matching
4. **Scraping** — Coleta lista de órgãos e URLs dos PDFs no gov.br
5. **Download** — Baixa PDFs com resume automático (skip se já existe)
6. **Dedup MD5** — Identifica PDFs compartilhados entre órgãos do mesmo grupo ministerial e elege um "owner" alfabético
7. **Extração** — Configura PyMuPDF `find_tables()` e detectores auxiliares
8. **Riscos** — Extrai tabelas de risco com merge multi-página, header-as-data, tabelas órfãs e consolidação multi-linha
9. **Entregas** — Extrai tabelas de entregas com mapeamento posicional para multi-página
10. **Padronização** — Normaliza vocabulário com fuzzy match contra produtos canônicos + legados
11. **Exportação** — Gera CSVs e JSONs estruturados
12. **Estatísticas** — Visualizações e dashboard de qualidade
13. **Iteração** — Fila de revisão para correções manuais

O pipeline tem **checkpoint/resume**: se interrompido, retoma do último checkpoint salvo.

## Tratamentos especiais de extração

A extração de tabelas em PDFs governamentais não é trivial — cada órgão usa templates ligeiramente diferentes. As seguintes situações são detectadas e tratadas:

| Situação | Detecção | Tratamento |
|---|---|---|
| Tabela continua na página seguinte | mesmo nº de colunas + scale values | merge automático |
| Primeira linha de continuação virou header | `_cols_are_data()` | recupera linha como dado |
| Headers genéricos `Col0\|Col1\|...` | `_is_orphan_risk_data()` | mapeamento posicional |
| Cabeçalhos parciais (`Col0\|Probabilidade de\|Col2\|...`) | falha em `_map_risk_columns` | fallback posicional |
| Tabela 6-col com ID na 1ª coluna | offset detectado por valores curtos | mapeamento posicional com offset |
| Cada risco ocupa múltiplas linhas | <40% rows com ID populado | consolida entre IDs |
| Escalas alternativas (Baixa/Média/Alta, 1-4) | `PROBABILIDADE_ALIASES`, `IMPACTO_ALIASES` | mapeamento semântico para escala SGD |
| Ações como referências numéricas (`"1, 2, 9"`) | parsing do `Referencial para ações` | substitui pelo texto integral |
| PDF compartilhado entre órgãos do grupo | hash MD5 | um owner por hash |

Resíduos marcados `needs_review=True`:

- 10 PDFs diretivos sem tabela de risco extraível (provavelmente escaneados sem OCR): AGU, ANVISA, FBN, FCP, FUNAI, INCRA, ITI, MAPA, MCOM, PREVIC. Lista completa em `output/error_report.csv`.
- 36 riscos (6%) com probabilidade/impacto fora da escala canônica — casos genuinamente fragmentados em DNOCS, MPOR, CVM, CADE, MJSP. Texto bruto preservado em `*_original`

Detalhes e histórico dos fixes em [`DECISIONS.md`](DECISIONS.md).

## Estrutura do projeto

```
PTD/
  ptd_scraper.ipynb            # Notebook principal (gerado a partir de notebook_cells/)
  build_notebook.py            # Monta o notebook a partir das células
  notebook_cells/              # Células individuais (.py e .md)
    01_setup.py                # Detecta Colab/local, instala deps
    02_config.py               # ORGAN_GROUPS, vocabulários canônicos, dataclasses
    03_utils.py                # safe_request, fuzzy_match, parse_date
    04*_scraping.*             # Lista de órgãos e URLs dos PDFs
    05*_download.*             # Download com resume
    05c_dedup.py               # Dedup MD5
    06*_docling_setup.*        # Classificadores e detectores de tabela
    07*_extract_risks.*        # Extração de riscos
    08*_extract_deliveries.*   # Extração de entregas
    09*_standardization.*      # Normalização de vocabulário
    10*_export.*               # CSV/JSON
    11*_statistics.*           # Visualizações
    11c*_dashboard_data.*      # data.js para o dashboard
    12*_iteration.*            # Review queue
  index.html                   # Dashboard interativo (consome output/data.js)
  output/                      # Dados extraídos e visualizações
  DECISIONS.md                 # Histórico de decisões técnicas e bugs corrigidos
  requirements.txt             # Dependências Python
```

## Desenvolvimento

As células do notebook ficam em `notebook_cells/` como arquivos `.py` e `.md` individuais. Após editar, reconstrua o notebook:

```bash
python build_notebook.py
```

Para validar consistência entre código e dados commitados, rode o notebook do zero e compare:

```bash
rm -rf ptd_output/checkpoints/* ptd_output/output/*
python build_notebook.py
jupyter nbconvert --to notebook --execute ptd_scraper.ipynb
diff <(sort ptd_output/output/risks.csv) <(sort output/risks.csv)
```

Os PDFs são cacheados em `ptd_output/pdfs/`; o segundo run reutiliza-os e termina em ~3-4 minutos.

## Citação

DIREITO, Denise; SILVA, Lucas; QUEIROZ, Sérgio. *Corpus dos Planos de Transformação Digital: extração, padronização e análise dos PTDs de 91 órgãos federais brasileiros*. Brasília: Ipea, 2026. (Nota Técnica).

## Licença

Este projeto está licenciado sob a [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
