# Spike S1 — Texto Diretivo: extração, segmentação e viabilidade

> **Nota histórica**: os NÚMEROS deste README descrevem o spike original
> (jul/2026, corpus de 85 diretivos do snapshot mai/2026). Os dados em
> `data/` são re-gerados a cada refresh do corpus — os números correntes
> canônicos estão em `data/segmentation_report.json` (campo `summary`).

Primeira sessão do plano de análise de **similaridade & discrepância do corpo
em prosa do Documento Diretivo** contra o template oficial da SGD. Este spike
prova a viabilidade da camada de dados; as métricas definitivas, a integração
ao pipeline (`notebook_cells/`) e a aba do dashboard vêm nas sessões S2-S4.

## Resultado — viabilidade COMPROVADA

| Indicador | Valor |
|---|---|
| PDFs diretivos baixados | **85/86** (SUSEP: renomeado no portal, 404) |
| Órgãos sem URL de diretivo | 5 (ABIN, ANTT, DNIT, MDIC, MT — já conhecidos) |
| Escaneados sem OCR (excluídos) | 10 (mesma lista dos riscos) |
| Segmentados com as **6 seções completas** | **75/75 (100%)** |
| Falhas de segmentação | 0 |

## Scripts (rodar nesta ordem)

1. `parse_template.py` — parseia a minuta oficial DOCX v2.2 (baixada do Kit de
   Elaboração PTD) em 6 blocos temáticos canônicos com âncoras de heading:
   `escopo`, `visao`, `eixos`, `acompanhamento`, `riscos`, `papeis`.
2. `download_diretivos.py` — baixa os PDFs diretivos das URLs de
   `output/organs.csv`. **Atenção**: o portal foi reestruturado
   (`planos-de-transformacao-digital` → `planos-transformacao-digital`); o
   script reescreve as URLs. O scraper do pipeline (`02_config.py BASE_URL`)
   precisará do mesmo ajuste no próximo refresh.
3. `extract_and_segment.py` — extrai prosa por linha (PyMuPDF `get_text("dict")`),
   excluindo tabelas de risco/contato por bbox com guardas anti-falso-positivo;
   remove cabeçalho/rodapé repetido; captura "Versão do modelo" do rodapé;
   segmenta por fuzzy-match das âncoras (difflib ≥0.82) com detecção de sumário.
4. `preview_similarity.py` — prévia da métrica: cosseno TF-IDF (Python puro) e
   novidade lexical de cada bloco vs template.

Os PDFs (106 MB) ficam em `ptd_output/pdfs/diretivo/` (gitignored). Os
artefatos JSON são copiados para `spike_s1/data/` para as próximas sessões
não dependerem de rede.

## Dados em `data/`

- `directive_template_blocks.json` — template v2.2 segmentado (referência).
- `directive_text.json` — prosa integral por página, por órgão (+ flag
  escaneado + versão do modelo declarada no rodapé).
- `directive_blocks.json` — prosa segmentada nos 6 blocos temáticos, por órgão.
- `segmentation_report.json` — cobertura por órgão/seção, páginas de sumário.
- `similarity_preview.json` — cosseno TF-IDF + novidade por (órgão, seção).
- `download_report.json` — status por órgão + MD5 (dedup de grupos ministeriais).

## Errata (corrigida na S2)

A primeira versão da segmentação ancorava `eixos` na CAPA (o título "PLANO DE
TRANSFORMAÇÃO DIGITAL DA..." casa fuzzy 0,83 com "EIXOS DA TRANSFORMAÇÃO
DIGITAL" pelo miolo compartilhado), deslocando os blocos. Correção dupla em
`extract_and_segment.py`: o primeiro token do heading precisa casar com o da
âncora, e a seleção de âncoras é gulosa na ordem do template. O relatório
agora inclui a checagem `headings_estranhos` (bloco contendo heading de outra
seção) — 0 ocorrências após o fix.

## Achados que orientam a S2

1. **Assinatura pro forma clara**: `acompanhamento` (cosseno médio 0,86) e
   `papeis` (0,85) são cópia do template; `escopo` (0,72) intermediário.
2. **`visao` é o bloco de ouro**: no template só há rótulos (6 palavras) —
   tudo que o órgão escreve ali é conteúdo próprio (novidade ~1,0). É onde a
   contextualização local mora.
3. **Versão do modelo importa**: 41 órgãos declaram "Versão do modelo: 2.1" no
   rodapé; o bloco `eixos` diverge lexicalmente entre v2.1 e v2.2 (produtos
   renomeados). Na S2, comparar contra referência por versão OU contra o
   medoide de consenso, senão a "discrepância" mede versão de template, não
   originalidade.
4. **`riscos` não deve usar o template como referência** (lá é só instrução);
   comparar contra consenso do corpus.
5. **Grupos ministeriais** (MEC, MD, MF, MMA, MIDR, MDA) compartilham PDF —
   valores idênticos; dedup na exibição (mesma política do Jaccard atual).
6. **SUSEP**: diretivo renomeado no portal → re-scrape necessário; e a
   BASE_URL do pipeline mudou (quebra o refresh mensal — corrigir à parte).
