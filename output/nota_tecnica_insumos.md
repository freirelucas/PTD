# Insumos para Nota Técnica IPEA
# Corpus dos Planos de Transformação Digital: coleta, padronização e análise

<!-- GERADO por notebook_cells/11e_nt_insumos.py — não editar à mão.
     Para atualizar: python notebook_cells/11e_nt_insumos.py [output_dir]
     Snapshot: 2026-05-12 · commit do pipeline: 0d14ecd4d7e12a68a5c95d298fa6bc4da245e5f0 -->

## 0. PROVENIÊNCIA E DEFINIÇÕES

Todos os números deste documento são computados de `output/deliveries.csv`,
`output/risks.csv` e `output/coverage_summary.csv` pelo gerador
`notebook_cells/11e_nt_insumos.py`. Em caso de divergência com qualquer outra
fonte (rascunhos, handouts, versões anteriores desta NT), **estes valores
prevalecem** para o snapshot indicado acima.

Definições usadas:

- **Canônico (prob./impacto)**: valor normalizado pertence à escala SGD de 5
  níveis. **Canônico (tratamento)**: valor é uma das 4 opções, ou composição
  delas separada por ";" (ex.: "mitigar; transferir").
- **Zona crítica**: probabilidade ≥ provável E impacto ≥ alto (matriz 3×2 do
  canto superior). **Severidade máxima**: praticamente certo × muito alto.
- **Sem ações de tratamento**: campo `acoes_tratamento` vazio.
- **Texto repetido**: `risco_texto` normalizado idêntico em ≥3 órgãos distintos.
- **Match determinístico**: `produto_method` ∈ {exact, alias};
  **fuzzy**: `produto_method` ∈ {fuzzy_high (≥0,85), fuzzy_low (≥0,70)}.
- **Dependência de fornecedor**: substring "fornecedor" em `risco_texto`.
- **Risco de pessoal**: `risco_texto` contém pessoal/rotatividade/equipe/
  servidor/capacita.

---

### SINOPSE (números para o parágrafo)

- 91 órgãos signatários · entregas: 4.574 registros de 79 órgãos · riscos: 619 registros de 76 órgãos
- Instituição: Decreto nº 12.198/2024 (EFGD 2024-2027); regulamentação dos
  PTDs: Portaria SGD/MGI nº 6.618/2024

---

### 2 METODOLOGIA — métricas

**2.1 Coleta dos dados**

| Etapa | Resultado |
|-------|-----------|
| Scraping da página gov.br | 91 órgãos signatários |
| Download dos PDFs | 61 Diretivos + 65 Entregas = 126 PDFs |
| Desduplicação MD5 (grupos ministeriais) | 58 PDFs únicos |
| Extração de entregas | 4.574 registros de 79 órgãos (57 próprios + 22 compartilhados) |
| Extração de riscos | 619 registros de 76 órgãos (51 próprios + 25 compartilhados) |

- Cobertura de entregas: 86,8% (79/91);
  12 órgãos sem dados extraíveis: AGU, CODEVASF, FUNAI, FUNDACENTRO, INCRA, ITI, MCOM, MIDR, SGPR, SUDAM, SUDECO, SUDENE
- Cobertura de riscos: 83,5% (76/91);
  10 com PDF Diretivo sem tabela de riscos extraível,
  5 sem PDF Diretivo publicado

**2.2 Padronização de vocabulário**

- Catálogo: 44 produtos canônicos (template v4.0, 5 eixos) +
  11 legados (PPSI, Integração à base de dados, "Outros", etc.)
- Aliases determinísticos: 29 de produto ·
  14 de eixo
- Resultado do matching de produto (4.574 registros):
  exato 3.358 (73,4%) ·
  alias 685 (15,0%) ·
  fuzzy ≥0,85 531 (11,6%) ·
  UNMATCHED 0
- Determinístico (exato+alias): 88,4%
  — nota: rascunhos anteriores citavam "90,7% exato"; esse valor não é
  reprodutível a partir de `produto_method` e não deve ser usado
- Eixo declarado ausente no PDF em 2.276
  registros (49,8%) — nesses casos o
  eixo é derivado do produto via cross-validation

**2.6 Estrutura do corpus (schemas reais)**

- `deliveries.csv` — 4.574 linhas × 19 colunas:
  orgao_sigla, tabela_tipo, servico_acao, produto_original, produto_normalizado, produto_score, produto_method, eixo_original, eixo_normalizado, eixo_score, eixo_method, area_responsavel, data_pactuada, data_entrega, pactuado, justificativa, extraction_confidence, needs_review, review_reason
- `risks.csv` — 619 linhas × 18 colunas:
  orgao_sigla, risco_texto, probabilidade_original, probabilidade_normalizada, probabilidade_score, probabilidade_method, impacto_original, impacto_normalizado, impacto_score, impacto_method, tratamento_original, tratamento_normalizado, tratamento_score, tratamento_method, acoes_tratamento, extraction_confidence, needs_review, review_reason

---

### 3 RESULTADOS

**3.1 Panorama das entregas**

- 4.574 entregas pactuadas por 79 órgãos
  (57 próprios + 22 via PTD ministerial)
- Distribuição por eixo:
  - Serviços Digitais e Melhoria da Qualidade: 2.418 (52,9%)
  - Unificação de Canais Digitais: 1.241 (27,1%)
  - Segurança e Privacidade: 644 (14,1%)
  - Projetos Especiais: 148 (3,2%)
  - Governança e Gestão de Dados: 123 (2,7%)
- Top 2 eixos concentram 3.659 entregas (80,0%)
- 16 dos 44 produtos canônicos têm ≥1
  pactuação; 28 têm zero. Produtos legados com pactuação:
  - Implementação do PPSI: 343 (7,5%)
  - Auto-avaliação, análise de lacunas e planejamento do PPSI: 300 (6,6%)
  - Integração à base de dados: 109 (2,4%)
  - Interoperabilidade de Sistemas: 14 (0,3%)
  - Outros: 148 (3,2%)
- Top 3 produtos: Integração ao Login Único (694), Integração à ferramenta de avaliação da satisfação dos usuários (685), Evolução do Serviço (677)
- Média: 80,2 entregas/órgão · Mediana: 57 ·
  Máx: ANVISA (348) · Mín: CONAB (7)
- Concentração: os 11 maiores órgãos (20%) detêm
  49,3% das entregas
- Produto "Outros" (Projetos Especiais): 148 registros
  (3,2%) — texto livre validado pela curadoria;
  29 deles são fragmentos (servico_acao <10 chars) que o
  pipeline passa a descartar no próximo run (filter_fragment_deliveries)
- 27,6% das datas pactuadas parseáveis
  (2.903) concentram-se em dezembro
- needs_review: 2.679 (58,6%),
  dos quais 2.209 são o flag informativo de cross-validation
  produto↔eixo (não indicam erro)

**3.2 Panorama dos riscos**

- 619 riscos mapeados por 76 órgãos
  (51 próprios + 25 via PTD ministerial)
- Probabilidade canônica: 604/619
  (97,6%) — raro (37), pouco provável (243), provável (234), muito provável (68), praticamente certo (22)
- Impacto canônico: 601/619
  (97,1%) — baixo (46), médio (155), alto (262), muito alto (138)
- Probabilidade E impacto canônicos: 592
  (95,6%); 27 residuais: CADE (3), CENSIPAM (3), CVM (4), DNOCS (6), IBAMA (1), IBGE (1), MJSP (2), MMULHERES (1), MPOR (5), PRF (1)
- Tratamento canônico: 584/619 (94,3%),
  sendo 579 simples + 5
  compostos; 18 vazios ·
  17 fora da escala
- Distribuição (simples): mitigar 487 (84,1% das simples; 78,7% do total) · aceitar 60 (10,4% das simples; 9,7% do total) · transferir 19 (3,3% das simples; 3,1% do total) · eliminar 13 (2,2% das simples; 2,1% do total)
- Zona crítica: 218 riscos (35,2%)
- Severidade máxima: 13 riscos — ANA, ANATEL, CAPES, INSS, MDHC, MESP, MME, MPO (2), MRE (2), SGPR (2)
- Sem ações de tratamento (campo vazio): 26
  (4,2%)
- Texto repetido em ≥3 órgãos: 311
  (50,2%) — proxy de reprodução do referencial SGD
- 22 órgãos usam exclusivamente "mitigar":
  ANAC, ANATEL, ANM, ANS, BCB, CGU, CNPQ, CONAB, CVM, FIOCRUZ, FUNDACENTRO, INPI, IPHAN, MESP, MF, MJSP, MMULHERES, MPI, MRE, MTUR, PF, PRF
- needs_review: 86 (13,9%)

**3.3 Achados transversais (quantitativos)**

- **Governança de Dados residual**: dos 20 produtos
  canônicos do eixo, com pactuação: nenhum. Os
  123 registros
  do eixo vêm de produtos LEGADOS (Integração à base de dados,
  Interoperabilidade de Sistemas)
- **Difusão**: PPSI presente em 52/57
  órgãos próprios (91%),
  Login Único em 46/57
  (81%); nenhum produto é
  universal
- **Dependência de fornecedor**: 28 riscos em 26
  órgãos próprios; 16 na zona crítica
- **Risco de pessoal/TI**: 10 de
  51 órgãos com riscos
  (20%) não mencionam
  risco de pessoal (ver definição na seção 0)
- **Gap EFGD**: o Decreto 12.198/2024 estabelece 6 princípios; o template
  operacionaliza 5 eixos. Princípios V (transparente/participativo) e VI
  (eficiente/sustentável) sem expressão operacional nos produtos pactuados

---

### APÊNDICE — Dados e código

- Repositório: https://github.com/freirelucas/PTD
- Dashboard interativo: https://freirelucas.github.io/PTD/
- Notebook Colab:
  https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb
- Dados (CSV/JSON): https://github.com/freirelucas/PTD/tree/main/output
