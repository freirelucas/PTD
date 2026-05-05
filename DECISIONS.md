# Histórico de Decisões Técnicas

Este documento registra as escolhas e correções feitas durante a construção do corpus,
para referência de desenvolvedores e pesquisadores interessados no processo.

## 1. Evolução da ferramenta de extração

**Decisão inicial:** Docling (IBM) — deep learning para detecção de tabelas, OCR integrado.
Implementado no notebook Colab (`notebook_cells/06b_docling_setup.py`).

**Problema:** Docling exige ~2 GB de modelos, GPU recomendada, instalação instável em
alguns ambientes. Não instala no ambiente de desenvolvimento local.

**Decisão final:** PyMuPDF `find_tables()` (v1.23+) para a extração de produção.
Rápido (~1s/PDF), sem dependências pesadas, detecção nativa de estrutura tabelar.

**Status:** Os dados em `output/` foram gerados 100% com PyMuPDF. O notebook Colab
mantém Docling como alternativa (especialmente para OCR dos 12 PDFs escaneados).

## 2. Bugs de extração corrigidos iterativamente

### 2.1 Tabelas multi-página (fix crítico)
- **Descoberta:** entregas 6.292→7.664 (+22%), riscos 670→929 (+39%)
- **Causa:** o extrator original pegava apenas a primeira tabela classificada como risco/entrega,
  ignorando continuações nas páginas seguintes
- **Fix:** após encontrar header, coletar TODAS as tabelas com mesmo nº de colunas
  que contenham valores de escala (prob/impacto/tratamento)

### 2.2 Primeira linha como header de coluna (fix de 17 PDFs)
- **Descoberta:** `find_tables()` interpreta a 1ª linha de dados de tabelas de continuação
  como nomes de coluna (ex: "Descontinuidade do serviço" virava header, não dado)
- **Fix:** `_cols_are_data()` detecta quando nomes de coluna parecem dados de risco
  e os recupera como entrada

### 2.3 Referências numéricas de ações (resolução semântica)
- **Descoberta:** coluna "Ações de tratamento" contém "1, 2, 9" — referências a uma
  lista numerada que aparece DEPOIS da tabela no mesmo PDF
- **Fix:** extração automática da lista "Referencial para ações de tratamento" e
  substituição dos números pelo texto completo

### 2.4 Desduplicação de órgãos agrupados (versionada no notebook)
- **Descoberta:** 7 grupos ministeriais compartilham PDFs (mesmo conteúdo publicado por
  múltiplas siglas). Sem dedup, o corpus inflava de 4.574 para 7.869 entregas
- **Versão anterior:** dedup era aplicada manualmente nos outputs *após* a execução do
  notebook, criando inconsistência entre código versionado e dados publicados
- **Fix (célula `05c_dedup.py`):** após download, computa MD5 de cada PDF; para cada
  hash duplicado, mantém como "owner" a sigla alfabeticamente menor e zera o `pdf_path`
  dos demais. A extração ignora siglas sem path; a expansão para "compartilhado"
  acontece via `ORGAN_GROUPS` no dashboard

### 2.5 Mapeamento de eixo incorreto
- **Descoberta:** "Integração à base de dados" mapeada para "Projetos Especiais"
  em vez de "Governança e Gestão de Dados" (erro de posição no array)
- **Fix:** mapeamento determinístico `CORRECT_EIXO` com validação cruzada produto→eixo

### 2.6 Tabelas órfãs sem cabeçalho válido (fix de 6 PDFs)
- **Descoberta:** PDFs como IBGE, ANS, FUNARTE, MPO, MPS, MTUR têm tabelas onde
  `find_tables()` retorna headers genéricos `Col0|Col1|Col2|...` em vez do template
  real. O extrator anterior descartava essas tabelas — perda de ~58 riscos
- **Fix:** `_is_orphan_risk_data(df)` detecta tabelas com headers genéricos cujo
  conteúdo passa em `_is_risk_data` (contém valores de escala). Mapeamento posicional
  é aplicado, recuperando os riscos perdidos
- **Bug correlato:** `classify_diretivo_table` retornava "unknown" para qualquer
  `df.empty == True`, descartando templates vazios que serviam de header para a
  continuação na próxima página. Corrigido para `len(df.columns) == 0`

### 2.7 Tabelas multi-linha (consolidação heurística)
- **Descoberta:** PDFs como MMULHERES estruturam cada risco em múltiplas linhas
  visuais (texto quebrado em rows internas da célula). PyMuPDF expande em ~92 rows
  para 18 riscos lógicos, gerando duplicatas
- **Fix (`_consolidate_multiline_cells`):** se col0 (ID) está populado em <40% das
  linhas e há ≥3 IDs distintos, agrupa rows entre IDs concatenando os valores. Inclui
  uma row anterior ao ID quando ela tem texto sem ID (caso onde o texto do risco
  aparece visualmente acima do identificador)
- **Limitação:** o desalinhamento residual de células deixa o texto de
  prob/impacto/tratamento misturado nesses casos. Os registros são marcados como
  `needs_review=True` com `extraction_confidence=low`

## 3. Evolução dos números do corpus

| Versão | Entregas | Riscos | Causa da mudança |
|--------|----------|--------|------------------|
| v0 (texto simples) | 5.968 | 10 | Extração por linha, PyMuPDF sem find_tables |
| v1 (find_tables) | 6.292 | 670 | Tabelas estruturadas, merge multi-página parcial |
| v2 (multi-page fix) | 7.664 | 929 | Fix completo multi-página + header-as-data |
| v3 (dedup pós-output) | 4.573 | 595 | Dedup manual aplicada nos arquivos commitados |
| **v4 (atual)** | **4.574** | **619** | Dedup MD5 versionada + detecção de tabelas órfãs + consolidação multi-linha |

A diferença entre v3 e v4 (+1 entrega, +24 riscos) decorre de 8 PDFs atualizados pelo
portal gov.br em 17/abr/2026 (CODEVASF, COAF, MIDR/SUDAM/SUDECO/SUDENE, MPI, SGPR).
CODEVASF, antes escaneado e ilegível, virou texto e contribuiu com +20 riscos.

## 4. Branches experimentais (deletados)

Os branches `claude/scrape-gov-signatories-tnVQa` e `claude/investigate-pdf-features-UiBwv`
serviram como ambientes de desenvolvimento iniciais. Todos os fixes foram portados para
`main`. Os branches foram deletados — nenhuma informação perdida.
