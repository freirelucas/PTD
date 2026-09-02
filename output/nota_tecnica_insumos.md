# Insumos para Nota Técnica IPEA
# Corpus dos Planos de Transformação Digital: coleta, padronização e análise

<!-- GERADO por notebook_cells/11e_nt_insumos.py — não editar à mão.
     Para atualizar: python notebook_cells/11e_nt_insumos.py [output_dir]
     Snapshot: 2026-09-02 · commit do pipeline: 9f51b7cd812a525a0a60be52fbbd4788c3e7bded -->

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

- 95 órgãos signatários · entregas: 5.168 registros de 84 órgãos · riscos: 704 registros de 79 órgãos
- Instituição: Decreto nº 12.198/2024 (EFGD 2024-2027); regulamentação dos
  PTDs: Portaria SGD/MGI nº 6.618/2024

---

### 2 METODOLOGIA — métricas

**2.1 Coleta dos dados**

| Etapa | Resultado |
|-------|-----------|
| Scraping da página gov.br | 95 órgãos signatários |
| Download dos PDFs | 66 Diretivos + 69 Entregas = 135 PDFs |
| Desduplicação MD5 (grupos ministeriais) | 62 PDFs únicos |
| Extração de entregas | 5.168 registros de 84 órgãos (62 próprios + 22 compartilhados) |
| Extração de riscos | 704 registros de 79 órgãos (56 próprios + 23 compartilhados) |

- Cobertura de entregas: 88,4% (84/95);
  11 órgãos sem dados extraíveis: AGU, CODEVASF, FUNDACENTRO, INCRA, ITI, MCOM, MIDR, SGPR, SUDAM, SUDECO, SUDENE
- Cobertura de riscos: 83,2% (79/95);
  10 com PDF Diretivo sem tabela de riscos extraível,
  2 sem PDF Diretivo publicado

**2.2 Padronização de vocabulário**

- Catálogo: 44 produtos canônicos (template v4.0, 5 eixos) +
  11 legados (PPSI, Integração à base de dados, "Outros", etc.)
- Aliases determinísticos: 29 de produto ·
  14 de eixo
- Resultado do matching de produto (5.168 registros):
  exato 3.917 (75,8%) ·
  alias 800 (15,5%) ·
  fuzzy ≥0,85 451 (8,7%) ·
  UNMATCHED 0
- Determinístico (exato+alias): 91,3%
  — nota: rascunhos anteriores citavam "90,7% exato"; esse valor não é
  reprodutível a partir de `produto_method` e não deve ser usado
- Eixo declarado ausente no PDF em 2.835
  registros (54,9%) — nesses casos o
  eixo é derivado do produto via cross-validation

**2.6 Estrutura do corpus (schemas reais)**

- `deliveries.csv` — 5.168 linhas × 19 colunas:
  orgao_sigla, tabela_tipo, servico_acao, produto_original, produto_normalizado, produto_score, produto_method, eixo_original, eixo_normalizado, eixo_score, eixo_method, area_responsavel, data_pactuada, data_entrega, pactuado, justificativa, extraction_confidence, needs_review, review_reason
- `risks.csv` — 704 linhas × 21 colunas:
  orgao_sigla, risco_texto, probabilidade_original, probabilidade_normalizada, probabilidade_score, probabilidade_method, impacto_original, impacto_normalizado, impacto_score, impacto_method, tratamento_original, tratamento_normalizado, tratamento_score, tratamento_method, acoes_tratamento, extraction_confidence, needs_review, review_reason, orientacao_risco, subtipo_exclusao, orientacao_confidence

---

### 3 RESULTADOS

**3.1 Panorama das entregas**

- 5.168 entregas pactuadas por 84 órgãos
  (62 próprios + 22 via PTD ministerial)
- Distribuição por eixo:
  - Serviços Digitais e Melhoria da Qualidade: 2.783 (53,9%)
  - Unificação de Canais Digitais: 1.374 (26,6%)
  - Segurança e Privacidade: 746 (14,4%)
  - Governança e Gestão de Dados: 146 (2,8%)
  - Projetos Especiais: 119 (2,3%)
- Top 2 eixos concentram 4.157 entregas (80,4%)
- 16 dos 44 produtos canônicos têm ≥1
  pactuação; 28 têm zero. Produtos legados com pactuação:
  - Implementação do PPSI: 401 (7,8%)
  - Auto-avaliação, análise de lacunas e planejamento do PPSI: 344 (6,7%)
  - Integração à base de dados: 131 (2,5%)
  - Interoperabilidade de Sistemas: 15 (0,3%)
  - Outros: 119 (2,3%)
- Top 3 produtos: Integração à ferramenta de avaliação da satisfação dos usuários (816), Integração ao Login Único (809), Evolução do Serviço (709)
- Média: 83,4 entregas/órgão · Mediana: 59 ·
  Máx: ANVISA (348) · Mín: SUSEP (7)
- Concentração: os 12 maiores órgãos (20%) detêm
  48,8% das entregas
- Produto "Outros" (Projetos Especiais): 119 registros
  (2,3%) — texto livre validado pela curadoria;
  0 deles são fragmentos (servico_acao <10 chars) que o
  pipeline passa a descartar no próximo run (filter_fragment_deliveries)
- 26,6% das datas pactuadas parseáveis
  (3.214) concentram-se em dezembro
- needs_review: 3.164 (61,2%),
  dos quais 2.774 são o flag informativo de cross-validation
  produto↔eixo (não indicam erro)

**3.2 Panorama dos riscos**

- 704 riscos mapeados por 79 órgãos
  (56 próprios + 23 via PTD ministerial)
- Probabilidade canônica: 670/704
  (95,2%) — raro (38), pouco provável (271), provável (265), muito provável (71), praticamente certo (25)
- Impacto canônico: 674/704
  (95,7%) — muito baixo (1), baixo (56), médio (183), alto (288), muito alto (146)
- Probabilidade E impacto canônicos: 659
  (93,6%); 45 residuais: CADE (3), CAPES (18), CENSIPAM (1), CVM (4), DNOCS (6), IBAMA (1), IBGE (1), INMETRO (5), MJSP (1), MPOR (5)
- Tratamento canônico: 651/704 (92,5%),
  sendo 644 simples + 7
  compostos; 34 vazios ·
  19 fora da escala
- Distribuição (simples): mitigar 542 (84,2% das simples; 77,0% do total) · aceitar 68 (10,6% das simples; 9,7% do total) · transferir 21 (3,3% das simples; 3,0% do total) · eliminar 13 (2,0% das simples; 1,8% do total)
- Zona crítica: 237 riscos (33,7%)
- Severidade máxima: 15 riscos — ANA, ANATEL, CAPES (2), FUNAI, INSS, MDHC, MESP, MME, MPO (2), MRE (2), SGPR (2)
- Sem ações de tratamento (campo vazio): 37
  (5,3%)
- Texto repetido em ≥3 órgãos: 364
  (51,7%) — proxy de reprodução do referencial SGD
- 25 órgãos usam exclusivamente "mitigar":
  ANAC, ANATEL, ANM, ANS, BCB, CGU, CNPQ, CONAB, CVM, FIOCRUZ, FUNDACENTRO, INMETRO, INPI, IPHAN, MESP, MF, MJSP, MMULHERES, MPA, MPI, MRE, MS, MTUR, PF, PRF
- needs_review: 108 (15,3%)

**3.3 Achados transversais (quantitativos)**

- **Governança de Dados residual**: dos 20 produtos
  canônicos do eixo, com pactuação: nenhum. Os
  146 registros
  do eixo vêm de produtos LEGADOS (Integração à base de dados,
  Interoperabilidade de Sistemas)
- **Difusão**: PPSI presente em 58/62
  órgãos próprios (94%),
  Login Único em 50/62
  (81%); nenhum produto é
  universal
- **Dependência de fornecedor**: 30 riscos em 28
  órgãos próprios; 16 na zona crítica
- **Risco de pessoal/TI**: 11 de
  56 órgãos com riscos
  (20%) não mencionam
  risco de pessoal (ver definição na seção 0)
- **Gap EFGD**: o Decreto 12.198/2024 estabelece 6 princípios; o template
  operacionaliza 5 eixos. Princípios V (transparente/participativo) e VI
  (eficiente/sustentável) sem expressão operacional nos produtos pactuados

**3.4 Risco de exclusão digital (dimensão distributiva)**

- Orientação dos riscos (sujeito afetado): estado 311, cidadão 35, ambos 2, indefinido 356. Entre os 348 classificáveis, o foco no Estado supera o foco no cidadão em ~9× — a matriz de risco é endógena ao aparato estatal (fornecedor, equipe, orçamento, cronograma), não distributiva.
- Subtipo de exclusão: digital_only 9, acessibilidade 2, disponibilidade_uptime 33 (FALSO-AMIGO — uptime técnico do sistema, frequentemente confundido com exclusão por mencionar o cidadão, mas distributivamente distinto), nenhum 660
- **Exclusão distributiva real** (digital_only | acessibilidade): 11 riscos em 8 órgãos (ANP, IBGE, INSS, MDHC, MGI, MMULHERES, MS, SGPR) — fração marginal de 704 riscos (1,6%).

| Órgão | Subtipo | Prob. | Impacto | Tratamento | Texto (trunc.) |
|---|---|---|---|---|---|
| ANP | digital_only | pouco provável | baixo | mitigar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| IBGE | digital_only | provável | baixo | mitigar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| INSS | digital_only | provável | médio | aceitar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| MDHC | digital_only | pouco provável | alto | mitigar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| MGI | digital_only | pouco provável | alto | mitigar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| MMULHERES | acessibilidade | muito provável | alto | orçamento digita… [nc] | Falta de orçamento Baixa acessibilidade dos |
| MMULHERES | digital_only | muito provável | médio | - Parcerias estr… [nc] | adequada para implementação digital Risco de exclusão digital |
| MMULHERES | digital_only | provável | alto | mitigar | pela via digital (digital only) |
| MS | digital_only | provável | baixo | mitigar | O serviço público terminar sendo oferecido somente pela via digital (digital onl |
| SGPR | acessibilidade | pouco provável | médio | mitigar | O PTD gerar transformações que afetem negativamente a acessibilidade digital. |
| SGPR | digital_only | provável | muito alto | mitigar | O modelo Digital Only ser uma barreira para jovens que não possuem acesso a disp |
- **Incoerência do template "digital only"** (número-chave): em 6 órgãos (ANP, IBGE, INSS, MDHC, MGI, MS), o MESMO risco recebe impacto **baixo → médio → alto** e tratamento **aceitar, mitigar**:
  - ANP: impacto baixo, tratamento mitigar
  - IBGE: impacto baixo, tratamento mitigar
  - INSS: impacto médio, tratamento aceitar
  - MDHC: impacto alto, tratamento mitigar
  - MGI: impacto alto, tratamento mitigar
  - MS: impacto baixo, tratamento mitigar
- **Gancho normativo**: o instrumento PTD PERMITE registrar exclusão, mas não a GOVERNA. O mesmo risco-template recebe severidade e resposta divergentes conforme o órgão — falta norma de preenchimento e escala de severidade padronizada. A EFGD/IN deveria exigir (i) linha OBRIGATÓRIA de risco de exclusão digital em todo PTD, (ii) escala de severidade padronizada para essa linha e (iii) tratamento default = manutenção de canal não-digital alternativo.

---

### APÊNDICE — Dados e código

- Repositório: https://github.com/freirelucas/PTD
- Dashboard interativo: https://freirelucas.github.io/PTD/
- Notebook Colab:
  https://colab.research.google.com/github/freirelucas/PTD/blob/main/ptd_scraper.ipynb
- Dados (CSV/JSON): https://github.com/freirelucas/PTD/tree/main/output
