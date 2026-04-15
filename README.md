# PTD -- Corpus dos Planos de Transformacao Digital

Pipeline para coleta, extracao e analise dos **Planos de Transformacao Digital (PTDs)** dos orgaos federais brasileiros, publicados no portal [gov.br](https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital).

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb)

## Resultados

O pipeline extrai dados estruturados de 91 orgaos federais:

| Arquivo | Descricao |
|---------|-----------|
| `output/deliveries.csv` | Entregas pactuadas, concluidas e canceladas |
| `output/risks.csv` | Riscos identificados nos Documentos Diretivos |
| `output/organs.csv` | Lista de orgaos com URLs dos PDFs |
| `output/data.js` | Dados para o dashboard interativo |
| `output/statistics_summary.json` | Estatisticas agregadas |
| `output/coverage_summary.csv` | Cobertura de extracao por orgao |
| `output/pdf_metadata.csv` | Metadados dos PDFs (datas, tamanhos) |
| `output/figures/` | Visualizacoes estatisticas (PNG) |

O dashboard interativo pode ser visualizado em [`index.html`](index.html).

## Como usar

### Google Colab (recomendado)

Clique no badge **Open in Colab** acima e execute as celulas sequencialmente. O ambiente detecta automaticamente o Colab e instala as dependencias.

### Execucao local

```bash
git clone https://github.com/freirelucas/PTD.git
cd PTD
pip install -r requirements.txt
jupyter notebook ptd_scraper.ipynb
```

> **Nota:** A biblioteca `docling` (extracao de tabelas via OCR) requer ~2 GB para download dos modelos. Para uso casual, recomendamos o Google Colab.

Para visualizar o dashboard localmente:

```bash
python -m http.server
# Abrir http://localhost:8000 no navegador
```

## Pipeline

O notebook executa 12 etapas sequenciais:

1. **Setup** -- Detecta ambiente (Colab/local), instala dependencias
2. **Configuracao** -- Vocabularios canonicos, estruturas de dados
3. **Utilitarios** -- Rede, normalizacao, fuzzy matching
4. **Scraping** -- Coleta lista de orgaos e URLs dos PDFs no gov.br
5. **Download** -- Baixa PDFs (Documento Diretivo + Anexo de Entregas)
6. **Docling** -- Configura extrator de tabelas (IBM Docling)
7. **Riscos** -- Extrai tabelas de riscos dos Documentos Diretivos
8. **Entregas** -- Extrai tabelas de entregas dos Anexos
9. **Padronizacao** -- Normaliza vocabulario, cross-validation produto-eixo
10. **Exportacao** -- Gera CSVs e JSONs estruturados
11. **Estatisticas** -- Visualizacoes e dashboard de qualidade
12. **Iteracao** -- Fila de revisao para correcoes manuais

O pipeline possui sistema de **checkpoint/resume**: se interrompido, retoma do ultimo ponto salvo.

## Estrutura do projeto

```
PTD/
  ptd_scraper.ipynb        # Notebook principal (montado automaticamente)
  build_notebook.py        # Monta o notebook a partir das celulas
  notebook_cells/          # Celulas individuais (.py e .md)
  index.html               # Dashboard interativo
  output/                  # Dados extraidos e visualizacoes
  requirements.txt         # Dependencias Python
```

## Desenvolvimento

As celulas do notebook ficam em `notebook_cells/` como arquivos `.py` e `.md` individuais. Apos editar, reconstrua o notebook:

```bash
python build_notebook.py
```

## Citacao

DIREITO, Denise; SILVA, Lucas; QUEIROZ, Sergio. *Corpus dos Planos de Transformacao Digital: extracao, padronizacao e analise dos PTDs de 91 orgaos federais brasileiros*. Brasilia: Ipea, 2026. (Nota Tecnica).

## Licenca

Este projeto esta licenciado sob a [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
