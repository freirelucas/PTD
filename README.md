# PTD — Corpus dos Planos de Transformação Digital

Pipeline para coleta, extração e análise dos **Planos de Transformação Digital (PTDs)** dos órgãos federais brasileiros, publicados no portal [gov.br](https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital).

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb)


## Visite e explore:  https://freirelucas.github.io/PTD/

## Resultados

O pipeline extrai dados estruturados de 91 órgãos federais (release 15/04/2026).

| Arquivo | Descrição |
|---------|-----------|
| `output/deliveries.csv` | Entregas pactuadas, concluídas e canceladas |
| `output/deliveries.json` | Entregas agrupadas por órgão (JSON estruturado) |
| `output/risks.csv` | Riscos identificados nos Documentos Diretivos |
| `output/risks.json` | Riscos agrupados por órgão (JSON estruturado) |
| `output/organs.csv` | Lista de órgãos com URLs dos PDFs |
| `output/error_report.csv` | Erros de processamento por órgão e estágio |
| `output/coverage_summary.csv` | Cobertura de extração por órgão |
| `output/vocabulary_mapping.csv` | Mapeamento de normalização de vocabulário |
| `output/data.js` | Dados para o dashboard interativo |
| `output/statistics_summary.json` | Estatísticas agregadas |
| `output/pdf_metadata.csv` | Metadados dos PDFs (datas, tamanhos) |
| `output/figures/` | Visualizações estatísticas (PNG) |

O dashboard interativo pode ser visualizado em [`index.html`](index.html).

## Como usar

### Google Colab (recomendado)

Clique no badge **Open in Colab** acima e execute as células sequencialmente. O ambiente detecta automaticamente o Colab e instala as dependências.

### Execução local

```bash
git clone https://github.com/freirelucas/PTD.git
cd PTD
pip install -r requirements.txt
jupyter notebook ptd_scraper.ipynb
```

> **Nota:** A biblioteca `docling` (extração de tabelas via OCR) requer ~2 GB para download dos modelos. Para uso casual, recomendamos o Google Colab.

Para visualizar o dashboard localmente:

```bash
python -m http.server
# Abrir http://localhost:8000 no navegador
```

## Pipeline

O notebook executa 12 etapas sequenciais:

1. **Setup** — Detecta ambiente (Colab/local), instala dependências
2. **Configuração** — Vocabulários canônicos, estruturas de dados
3. **Utilitários** — Rede, normalização, fuzzy matching
4. **Scraping** — Coleta lista de órgãos e URLs dos PDFs no gov.br
5. **Download** — Baixa PDFs (Documento Diretivo + Anexo de Entregas)
6. **Docling** — Configura extrator de tabelas (IBM Docling)
7. **Riscos** — Extrai tabelas de riscos dos Documentos Diretivos
8. **Entregas** — Extrai tabelas de entregas dos Anexos
9. **Padronização** — Normaliza vocabulário, cross-validation produto↔eixo
10. **Exportação** — Gera CSVs e JSONs estruturados
11. **Estatísticas** — Visualizações e dashboard de qualidade
12. **Iteração** — Fila de revisão para correções manuais

O pipeline possui sistema de **checkpoint/resume**: se interrompido, retoma do último ponto salvo.

## Estrutura do projeto

```
PTD/
  ptd_scraper.ipynb        # Notebook principal (montado automaticamente)
  build_notebook.py        # Monta o notebook a partir das células
  notebook_cells/          # Células individuais (.py e .md)
  index.html               # Dashboard interativo
  output/                  # Dados extraídos e visualizações
  requirements.txt         # Dependências Python
```

## Desenvolvimento

As células do notebook ficam em `notebook_cells/` como arquivos `.py` e `.md` individuais. Após editar, reconstrua o notebook:

```bash
python build_notebook.py
```

## Citação

DIREITO, Denise; SILVA, Lucas; QUEIROZ, Sérgio. *Corpus dos Planos de Transformação Digital: extração, padronização e análise dos PTDs de 91 órgãos federais brasileiros*. Brasília: Ipea, 2026. (Nota Técnica).

## Licença

Este projeto está licenciado sob a [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
