# PTD Scraper - Planos de Transformação Digital (Gov.br)

Notebook para coleta, extração e análise dos Planos de Transformação Digital dos órgãos federais brasileiros.

**Fonte:** [gov.br/governodigital - Planos de Transformação Digital](https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital)

**Pipeline:**
1. Scraping da lista de órgãos signatários e URLs dos PDFs
2. Download dos PDFs (Documento Diretivo + Anexo de Entregas)
3. Extração de tabelas com Docling (IBM)
4. Padronização de vocabulário
5. Exportação CSV/JSON + relatório de erros
6. Análises estatísticas do corpus