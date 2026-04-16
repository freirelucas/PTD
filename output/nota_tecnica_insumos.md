# Insumos para Nota Técnica IPEA
# Corpus dos Planos de Transformação Digital: coleta, padronização e análise

## Formato padrão de Nota Técnica do IPEA

### Elementos de capa
- Logotipo Ipea
- Série: "NOTA TÉCNICA"
- Número: Nº XX (Diretoria — ex: Diest)
- Título completo
- Autores com filiação
- Mês/Ano (ex: Abril de 2026)

### Estrutura típica (10-30 páginas)
1. SINOPSE (parágrafo único, ~150 palavras)
2. INTRODUÇÃO
3. Seções numeradas de desenvolvimento (2-5 seções)
4. CONSIDERAÇÕES FINAIS
5. REFERÊNCIAS
6. Apêndices (opcional)

### Formatação
- Fonte: Times New Roman 12pt (corpo), 10pt (notas de rodapé)
- Espaçamento: 1,5
- Margens: 3cm (sup/esq), 2cm (inf/dir)
- Citações ABNT
- Notas de rodapé numeradas
- Tabelas e figuras numeradas e com fonte

---

## ESTRUTURA PROPOSTA PARA ESTA NT

**NOTA TÉCNICA Nº XX/2026/Diest**

**Título:** Corpus dos Planos de Transformação Digital: coleta automatizada, padronização e análise dos PTDs de 91 órgãos federais

**Autores:** Denise Direito, Lucas Silva, Sérgio Queiroz

---

### SINOPSE

Esta nota técnica apresenta a construção e análise de um corpus abrangente dos Planos de Transformação Digital (PTDs) vigentes de 91 órgãos da administração pública federal brasileira. Os PTDs, instituídos pelo Decreto nº 12.198/2024 no âmbito da Estratégia Federal de Governo Digital (EFGD) 2024-2027, foram coletados automaticamente do portal gov.br, com extração estruturada de tabelas de entregas pactuadas (4.530 registros) e gestão de riscos (931 registros). Órgãos que compartilham um mesmo PTD ministerial são contados uma única vez, evitando dupla contagem. O corpus resultante permite análises transversais inéditas sobre o estado da transformação digital no governo federal, revelando padrões de concentração setorial, lacunas de governança de dados e características sistêmicas da gestão de riscos.

---

### 1 INTRODUÇÃO

**Insumos para redigir:**

- O Decreto nº 12.198/2024 institui a EFGD 2024-2027, estruturada em 6 princípios, 16 objetivos e 100 iniciativas
- A Portaria SGD/MGI nº 6.618/2024 regulamenta a elaboração dos PTDs
- 91 órgãos da administração federal direta e indireta publicaram PTDs vigentes no portal gov.br
- Os PTDs são compostos por Documento Diretivo (contexto + riscos) e Anexo de Entregas (pactuações)
- O template evoluiu ao longo do tempo: EGD 2020-2022 → transição v2.x → EFGD 2024 v4.0
- Não existe, até o momento, análise transversal sistematizada desses documentos
- **Gap de pesquisa:** os PTDs são publicados individualmente como PDFs; não há base consolidada que permita comparação entre órgãos

---

### 2 METODOLOGIA

**2.1 Coleta dos dados**

| Etapa | Método | Resultado |
|-------|--------|-----------|
| Scraping da página gov.br | BeautifulSoup4 + requests | 91 órgãos, 177 URLs de PDFs |
| Download dos PDFs | requests com rate-limiting (1.5s), verificação %PDF | 86 Diretivos + 91 Entregas = 177 PDFs |
| Extração de tabelas de entregas | Docling (IBM) + matching fuzzy de produtos | 4.530 registros de 79 órgãos (57 próprios + 22 compartilhados) |
| Extração de tabelas de riscos | Docling com merge multi-página + recuperação header-as-data + resolução de ações numéricas | 931 registros de 71 órgãos (50 próprios + 21 compartilhados) |
| Resolução de ações numéricas | Parsing da lista "Referencial para ações de tratamento" | 35 órgãos com referências resolvidas |

- 12 órgãos não processados (PDFs escaneados como imagem, sem camada de texto)
- Taxa de cobertura: 87% para entregas, 83% para riscos

**2.2 Padronização de vocabulário**

- Template v4.0: 44 produtos canônicos em 5 eixos operacionais
- 10 produtos legados adicionados (v1.x/v2.x: PPSI, Integração à base de dados, etc.)
- 19 aliases de produto para variações de texto (truncamentos, acentuação)
- 10 aliases de eixo para nomenclaturas da EGD 2020-2022
- Matching em 4 camadas: alias determinístico → exato accent-insensitive → fuzzy (SequenceMatcher ≥0.85) → UNMATCHED
- Campos preservados: produto_original + produto_normalizado (texto livre + canônico)
- Match exato: 90.7% | Fuzzy: 9.3% (truncamentos do PDF)

**2.3 Estrutura do corpus**

Entregas (deliveries.csv — 4.530 linhas × 9 colunas):
- orgao_sigla, servico_acao, produto_original, produto_normalizado, produto_score
- eixo_original, eixo_normalizado, data_pactuada, confidence

Riscos (risks.csv — 931 linhas × 11 colunas):
- orgao_sigla, id_risco, risco_texto
- probabilidade_original, probabilidade_normalizada
- impacto_original, impacto_normalizado
- tratamento_original, tratamento_normalizado
- acoes_original, acoes_resolvidas

---

### 3 RESULTADOS

**3.1 Panorama das entregas**

- 4.530 entregas pactuadas por 79 órgãos (57 com dados próprios + 22 compartilhando PTD ministerial)
- Distribuição por eixo:
  - Serviços Digitais e Melhoria da Qualidade: 2.109 (46,6%)
  - Unificação de Canais Digitais: 1.206 (26,6%)
  - Segurança e Privacidade: 655 (14,5%)
  - Governança e Gestão de Dados: 112 (2,5%)
  - Projetos Especiais: 0 (0,0%)
- 19 dos 44 produtos canônicos aparecem no corpus; 25 têm zero pactuações
- Top 3 produtos: Integração à ferramenta de avaliação da satisfação dos usuários (790), Integração ao Login Único (699), Evolução do Serviço (676)
- 2 produtos legados concentram 461 entregas (10,2%): PPSI (349), Integração à base de dados (112)
- Média: 79,5 entregas/órgão | Mediana: 53 | Máx: ANVISA (437) | Mín: MDA (6)
- 30% das entregas concentradas em dezembro (final de vigência)

**3.2 Panorama dos riscos**

- 931 riscos mapeados por 71 órgãos (50 com dados próprios + 21 compartilhando PTD ministerial)
- Distribuição de probabilidade: provável (188), pouco provável (174), muito provável (44), raro (28), praticamente certo (20)
- Distribuição de impacto: alto (220), médio (140), muito alto (100), baixo (45)
- Tratamento: mitigar (62%), aceitar (10%), transferir (4%), eliminar (1%)
- 166 riscos na zona crítica (probabilidade ≥ provável × impacto ≥ alto)
- 11 riscos na severidade máxima (praticamente certo × muito alto): ANATEL, ANA, INSS, MDHC, MEC, MME, MPO, MRE (2), SG-PR (2)
- 45% dos riscos sem ações de tratamento detalhadas
- 66% dos textos de risco reproduzem o referencial padrão da SGD
- 23 órgãos usam exclusivamente "mitigar" como estratégia

**3.3 Achados transversais**

**Governança de Dados como eixo residual:**
- 20 dos 44 produtos canônicos pertencem ao eixo Governança e Gestão de Dados
- Apenas 1 produto deste eixo aparece nas pactuações (Integração à base de dados, com 112 entregas)
- 19 produtos — LGPD, PDTIC, dados abertos, interoperabilidade, inventário de dados — têm zero pactuações
- Quando órgãos executam ações de governança (ex: adequação à LGPD), registram sob outros produtos (PPSI)
- Ressalva: 12 órgãos com PDFs escaneados não foram processados; confirmação definitiva requer OCR

**Tradução incompleta dos princípios da EFGD:**
- O Decreto 12.198/2024 estabelece 6 princípios; o template PTD operacionaliza 5 eixos
- Os princípios V (transparente/participativo) e VI (eficiente/sustentável) carecem de expressão operacional
- Na prática, 3 princípios sustentam as pactuações: cidadão (I), integrado (II), seguro (IV)

**Gestão de riscos como formalidade:**
- 66% dos riscos reproduzem textos do referencial padrão
- 45% não têm ações de tratamento
- 39% dos órgãos não mencionam risco de pessoal/TI — o mais frequente no corpus
- Riscos de pessoal são 2,4× mais frequentes que riscos orçamentários

**Concentração e homogeneidade:**
- PPSI é o produto mais difundido (90% dos órgãos), seguido de Login Único (76%)
- Nenhum produto é universal (presente em todos os órgãos)
- Top 2 eixos concentram 73,2% das entregas

---

### 4 CONSIDERAÇÕES FINAIS

**Pontos para a redação:**

- O corpus construído constitui a primeira base consolidada de PTDs, permitindo análise transversal inédita
- A transformação digital federal concentra-se na digitalização de serviços e unificação de canais, com lacunas significativas em governança de dados e inovação
- A gestão de riscos, embora formalmente cumprida, apresenta características de conformidade mais do que de exercício analítico
- O gap entre os 6 princípios da EFGD e os 5 eixos operacionais merece atenção normativa
- A publicação de PDFs escaneados por 12 órgãos limita a acessibilidade e reprodutibilidade
- Recomendações: publicação em formato aberto, API para dados de PTDs, padronização mais rigorosa do preenchimento de riscos

---

### 5 REFERÊNCIAS

- BRASIL. Decreto nº 12.198, de 24 de setembro de 2024. Institui a Estratégia Federal de Governo Digital para o período de 2024 a 2027.
- BRASIL. Portaria SGD/MGI nº 6.618, de 25 de setembro de 2024. Regulamenta os Planos de Transformação Digital.
- BRASIL. Ministério da Gestão e da Inovação em Serviços Públicos. Estratégia Federal de Governo Digital 2024-2027. Disponível em: https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/EFGD
- BRASIL. SGD/MGI. Planos de Transformação Digital. Disponível em: https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital
- BRASIL. SGD/MGI. Kit de Elaboração do PTD. Disponível em: https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/planos-de-transformacao-digital/kit-de-elaboracao-ptd

---

### APÊNDICE A — Dados e código

- Repositório: https://github.com/freirelucas/PTD
- Dashboard interativo: https://freirelucas.github.io/PTD/
- Notebook Colab: https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb
- Dados (CSV/JSON): https://github.com/freirelucas/PTD/tree/main/output

### APÊNDICE B — Órgãos não processados

| Órgão | Motivo |
|-------|--------|
| AGU | PDF entregas escaneado |
| CODEVASF | PDF entregas formato não-padrão |
| FUNAI | PDF entregas escaneado |
| FUNDACENTRO | PDF entregas escaneado |
| INCRA | PDF entregas escaneado |
| ITI | PDF entregas escaneado |
| MCOM | PDF entregas escaneado |
| MIDR | PDF entregas formato não-padrão |
| SG-PR | PDF entregas escaneado |
| SUDAM | PDF entregas formato não-padrão |
| SUDECO | PDF entregas formato não-padrão |
| SUDENE | PDF entregas formato não-padrão |

### APÊNDICE C — Produtos canônicos vs pactuações

(Tabela completa dos 44 produtos com contagem de entregas e órgãos — disponível no dashboard interativo)
