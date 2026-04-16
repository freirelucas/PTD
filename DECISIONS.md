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

### 2.4 Desduplicação de órgãos agrupados
- **Descoberta:** 7 grupos ministeriais compartilham PDFs. Replicar entregas inflava
  o corpus de 7.664 para ~4.530 registros únicos
- **Fix:** atribuir dados ao órgão-cabeça, marcar membros como "compartilhado" na
  cobertura. Exceção: MF/PGFN (seções independentes no mesmo PDF)

### 2.5 Mapeamento de eixo incorreto
- **Descoberta:** "Integração à base de dados" mapeada para "Projetos Especiais"
  em vez de "Governança e Gestão de Dados" (erro de posição no array)
- **Fix:** mapeamento determinístico `CORRECT_EIXO` com validação cruzada produto→eixo

## 3. Evolução dos números do corpus

| Versão | Entregas | Riscos | Causa da mudança |
|--------|----------|--------|------------------|
| v0 (texto simples) | 5.968 | 10 | Extração por linha, PyMuPDF sem find_tables |
| v1 (find_tables) | 6.292 | 670 | Tabelas estruturadas, merge multi-página parcial |
| v2 (multi-page fix) | 7.664 | 929 | Fix completo multi-página + header-as-data |
| v3 (desduplicado) | 4.530 | 931 | Remoção de duplicatas de órgãos agrupados |
| **Release** | **4.530** | **931** | Versão final publicada |

## 4. Branch experimental (deletado)

O branch `claude/scrape-gov-signatories-tnVQa` serviu como ambiente de desenvolvimento
inicial. Todos os fixes e melhorias foram portados para `main`. O branch foi deletado
com 0 commits exclusivos — nenhuma informação perdida.
