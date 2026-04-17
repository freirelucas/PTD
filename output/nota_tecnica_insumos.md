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

Esta nota técnica apresenta a construção e análise de um corpus abrangente dos Planos de Transformação Digital (PTDs) vigentes de 91 órgãos da administração pública federal brasileira. Os PTDs, instituídos pelo Decreto nº 12.198/2024 no âmbito da Estratégia Federal de Governo Digital (EFGD) 2024-2027, foram coletados automaticamente do portal gov.br, com extração estruturada de tabelas de entregas pactuadas (4.573 registros) e gestão de riscos (595 registros). Órgãos que compartilham um mesmo PTD ministerial são desduplicados por hash MD5, evitando dupla contagem. O corpus resultante permite análises transversais inéditas sobre o estado da transformação digital no governo federal, revelando padrões de concentração setorial, lacunas de governança de dados e características sistêmicas da gestão de riscos.

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
| Extração de tabelas de entregas | PyMuPDF `find_tables()` + matching fuzzy de produtos | 4.573 registros de 79 órgãos (57 próprios + 22 compartilhados) |
| Extração de tabelas de riscos | PyMuPDF `find_tables()` com merge multi-página + recuperação header-as-data + resolução de ações numéricas | 595 registros de 71 órgãos (50 próprios + 21 compartilhados) |
| Desduplicação | Hash MD5 por arquivo PDF (mesmos PDFs de órgãos ministeriais compartilhados) | 177 PDFs → 98 únicos |
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

**2.4 Tratamento de órgãos agrupados**

Sete grupos ministeriais publicam um único PTD para múltiplos órgãos. Os registros são desduplicados por hash MD5 do arquivo PDF, e a cobertura é expandida para todos os membros do grupo:

| Grupo (cabeça) | Órgão com dados | Membros compartilhados |
|----------------|-----------------|------------------------|
| MD | CENSIPAM | MD, CEX, CM, COMAER, FOSORIO, HFA |
| MEC | CAPES | MEC, EBSERH, FNDE, FUNDAJ, IBC, INEP, INES |
| MF | MF, PGFN | RFB, STN |
| MMA | IBAMA | MMA, ICMBIO, JBRJ, SFB |
| MT | ANTT | MT, DNIT |
| MDA | CONAB | MDA |
| MIDR | — (sem dados) | CODEVASF, SUDAM, SUDECO, SUDENE |

Regra: as entregas e riscos extraídos do PDF são registrados uma vez sob o órgão com dados próprios (`status=ok`). Os demais membros recebem `status=compartilhado` e são incluídos nas contagens de cobertura (ex: "79 órgãos com entregas" = 57 próprios + 22 compartilhados), mas sem duplicar os registros no corpus.

**2.5 Desafios de extração e qualidade dos dados**

O extrator PyMuPDF `find_tables()` apresentou cinco desafios técnicos específicos, cada um com tratamento programático:

1. **Tabelas multi-página**: `find_tables()` trata cada página como tabela independente. O merge é feito via rastreamento de `col_order` e `risk_ncols` — quando uma tabela na página N+1 tem a mesma largura (número de colunas) que a tabela da página N e contém dados compatíveis (detecção por `_is_risk_data()`), as linhas são concatenadas à tabela principal.

2. **Header-as-data**: em ~17 PDFs, `find_tables()` interpreta a primeira linha de dados como cabeçalho do DataFrame. A detecção é feita por `_cols_are_data()` (verifica se os supostos cabeçalhos contêm valores compatíveis com riscos ou produtos) e a linha é recuperada como dado.

3. **Mapeamento posicional**: tabelas de continuação multi-página perdem os headers originais — os nomes de coluna são os valores da primeira linha. Um `pos_map` (dicionário posição→campo) permite acesso direto por índice: `{servico: 0, produto: 1, eixo: 2, data: 4}`.

4. **Resolução de ações numéricas**: 35 órgãos referenciam ações de tratamento como "1, 2, 9" ao invés do texto completo, remetendo a uma lista "Referencial para ações de tratamento" incluída no PDF. O extrator faz parsing dessa lista e resolve as referências numéricas para o texto integral.

5. **Colunas deslocadas**: 156 riscos (26%) de 4 órgãos (CENSIPAM: 26, ANTAQ: 26, PRF: 14, SUSEP: 9) apresentam probabilidade e impacto em campos trocados — o texto do risco aparece na coluna de probabilidade e vice-versa. Essa limitação decorre de templates de tabela não-padrão nesses PDFs. Os 439 riscos canônicos (74%) possuem todas as dimensões corretamente mapeadas.

6. **Produto "Outros"**: 140 entregas que não correspondem a nenhum dos 44 produtos canônicos do template v4.0 são classificadas como produto "Outros" no eixo Projetos Especiais. Correspondem a projetos institucionais específicos de cada órgão (ex: "Modernização do SIAFI" no MF).

**2.6 Estrutura do corpus**

Entregas (`deliveries.csv` — 4.573 linhas × 9 colunas):
- orgao_sigla, servico_acao, produto_original, produto_normalizado, produto_score
- eixo_original, eixo_normalizado, data_pactuada, confidence

Riscos (`risks.csv` — 595 linhas × 11 colunas):
- orgao_sigla, id_risco, risco_texto
- probabilidade_original, probabilidade_normalizada
- impacto_original, impacto_normalizado
- tratamento_original, tratamento_normalizado
- acoes_original, acoes_resolvidas

---

### 3 RESULTADOS

**3.1 Panorama das entregas**

- 4.573 entregas pactuadas por 79 órgãos (57 com dados próprios + 22 compartilhando PTD ministerial)
- Distribuição por eixo:
  - Serviços Digitais e Melhoria da Qualidade: 2.414 (52,8%)
  - Unificação de Canais Digitais: 1.241 (27,1%)
  - Segurança e Privacidade: 654 (14,3%)
  - Projetos Especiais: 140 (3,1%)
  - Governança e Gestão de Dados: 124 (2,7%)
- 20 dos 44 produtos canônicos aparecem no corpus; 24 têm zero pactuações
- Top 3 produtos: Integração ao Login Único (694), Integração à ferramenta de avaliação da satisfação dos usuários (685), Evolução do Serviço (677)
- 2 produtos legados concentram 458 entregas (10,0%): PPSI (348), Integração à base de dados (110)
- Média: 80,2 entregas/órgão | Mediana: 57 | Máx: ANVISA (348) | Mín: CONAB (7)
- 140 entregas em "Projetos Especiais" (produto Outros): projetos de órgão sem correspondência no catálogo canônico

**3.2 Panorama dos riscos**

- 595 riscos mapeados por 71 órgãos (50 com dados próprios + 21 compartilhando PTD ministerial)
- Distribuição de probabilidade (canônica, 443/595): provável (182), pouco provável (173), muito provável (42), raro (26), praticamente certo (20)
- Distribuição de impacto (canônica, 504/595): alto (205), médio (146), muito alto (108), baixo (45)
- Tratamento (canônico): mitigar (79%), aceitar (13%), transferir (5%), eliminar (2%)
- 160 riscos na zona crítica (probabilidade ≥ provável × impacto ≥ alto)
- 11 riscos na severidade máxima (praticamente certo × muito alto): ANATEL, ANA, CAPES, INSS, MDHC, MME, MPO, MRE (2), SGPR (2)
- 23% dos riscos sem ações de tratamento detalhadas
- 52% dos textos de risco reproduzem fraseamento do referencial padrão (texto idêntico em ≥3 órgãos)
- 12 órgãos usam exclusivamente "mitigar" como estratégia
- 156 riscos (26%) com probabilidade e/ou impacto não-canônicos (PDFs com templates variantes de CENSIPAM, ANTAQ, PRF, SUSEP)

**3.3 Achados transversais**

**Governança de Dados como eixo residual:**
- 20 dos 44 produtos canônicos pertencem ao eixo Governança e Gestão de Dados
- Apenas 1 produto deste eixo aparece nas pactuações (Integração à base de dados, com 110 entregas)
- 19 produtos — LGPD, PDTIC, dados abertos, interoperabilidade, inventário de dados — têm zero pactuações
- Quando órgãos executam ações de governança (ex: adequação à LGPD), registram sob outros produtos (PPSI)
- Ressalva: 12 órgãos com PDFs escaneados não foram processados; confirmação definitiva requer OCR

**Tradução incompleta dos princípios da EFGD:**
- O Decreto 12.198/2024 estabelece 6 princípios; o template PTD operacionaliza 5 eixos
- Os princípios V (transparente/participativo) e VI (eficiente/sustentável) carecem de expressão operacional
- Na prática, 3 princípios sustentam as pactuações: cidadão (I), integrado (II), seguro (IV)

**Gestão de riscos como formalidade:**
- 52% dos riscos reproduzem fraseamento do referencial padrão (texto idêntico em ≥3 órgãos)
- 23% não têm ações de tratamento detalhadas
- 24% dos órgãos não mencionam risco de pessoal/TI — o mais frequente no corpus
- Dependência de fornecedores é o risco mais transversal: 23 riscos em 22 órgãos próprios (33 com compartilhados)

**Concentração e homogeneidade:**
- PPSI é o produto mais difundido (91% dos órgãos próprios), seguido de Login Único (81%)
- Nenhum produto é universal (presente em todos os órgãos)
- Top 2 eixos concentram 79,9% das entregas

**3.4 Análises computadas no dashboard**

O dashboard interativo (disponível em https://freirelucas.github.io/PTD/) implementa as seguintes análises, todas calculadas dinamicamente a partir do corpus:

*Entregas — distribuição e concentração:*

- **Curva de Lorenz e concentração**: mede a desigualdade na distribuição de entregas entre órgãos. Os 20% de órgãos com maior volume concentram mais da metade das entregas pactuadas.
- **Cronologia assinatura × entrega**: cruza a data de criação do PDF (proxy da assinatura do PTD) com as datas pactuadas de entrega. Revela o lag entre adesão formal e execução planejada, e a concentração de entregas nos meses finais da vigência.
- **Diversidade de produtos por órgão**: conta o número de produtos distintos pactuados por cada órgão. Revela que a maioria dos órgãos opera num subconjunto reduzido dos 44 produtos canônicos.
- **Heatmap órgão × eixo**: matriz dos 30 maiores órgãos mostrando a concentração setorial de entregas por eixo estratégico.

*Riscos — padrões e qualidade:*

- **Matriz 5×5 interativa**: probabilidade × impacto com ações de mitigação agregadas por célula. Ao clicar numa célula, exibe as ações de tratamento dos riscos naquela combinação, com órgãos afetados (incluindo membros de grupos compartilhados).
- **Bigramas**: frequência de pares de palavras consecutivas nos textos de risco. Mede a originalidade da redação vs reprodução do template padrão da SGD.
- **Dependência de fornecedores**: 23 riscos em 22 órgãos próprios (36 com membros compartilhados) mencionam dependência de fornecedores — o risco mais transversal. 15 estão na zona crítica (probabilidade ≥ provável × impacto ≥ alto). O tratamento predominante é "mitigar" (32×), embora a literatura recomende "transferir" ou "compartilhar" para riscos de dependência externa.
- **Risco de pessoal/TI**: rotatividade, indisponibilidade de equipes e dependência de fornecedores são mais frequentes que riscos orçamentários. 24% dos órgãos com riscos mapeados não mencionam riscos de pessoal.

*Comparação entre órgãos:*

- **Similaridade de Jaccard**: coeficiente calculado a partir dos perfis de produtos pactuados (conjunto de produtos distintos por órgão). Órgãos de um mesmo grupo ministerial apresentam similaridade 100% (mesmo PTD). Permite identificar clusters de órgãos com estratégias convergentes.
- **Comparação multi-órgão**: seleção de até 3 órgãos para comparação direta de catálogos de produtos, com tabela de sobreposição.

*Tecnologia e inovação:*

- **Detecção por keyword**: busca de termos em textos livres de entregas (serviço/ação + produto original) para categorias: Plataforma Gov.br (login único, design system, pagtesouro), IA e chatbot, Acessibilidade (VLibras), Interoperabilidade, LGPD/Privacidade, Mobile/App, Dados/Analytics.
- **Resultado**: "Governo como Plataforma" domina o portfólio digital federal. IA/automação é incipiente — nenhum órgão pactuou RPA, analytics avançado ou machine learning como produto formal.

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
