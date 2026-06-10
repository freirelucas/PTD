# Balanço de Consistência — Corpus PTD-BR

**Data da auditoria:** 2026-06-10 · **Snapshot auditado:** `manifest.json`
`data_execucao=2026-05-12`, commit do pipeline `0d14ecd4` · **Branch:**
`claude/focused-keller-rsptib`

## 1. Contexto e método

Três fontes descrevem o mesmo corpus e foram confrontadas linha a linha:

1. **Handout de sessão** (`HANDOUT_CLAUDE_CODE.md`, jun/2026) — estado alegado
   do código, correções pendentes e "números canônicos";
2. **Nota Técnica** (`NT_PTDBR_Corpus_NT_4.docx`, rascunho) — texto a publicar;
3. **Repositório** — código (`notebook_cells/`) e dados (`output/*.csv|json`),
   tratados como verdade-terreno do snapshot.

Toda métrica contestada foi recomputada diretamente de `deliveries.csv`
(4.574 × 19), `risks.csv` (619 × 18) e `coverage_summary.csv` com a stdlib
do Python (sem dependência de pandas), e as definições foram fixadas por
escrito. O recomputo agora é executável por qualquer pessoa:
`python notebook_cells/11e_nt_insumos.py output`.

**Diagnóstico central:** as três fontes refletem **pelo menos dois — provavelmente
três — runs distintos** do pipeline. Totais e distribuição de entregas eram
sólidos; as analíticas de risco e a taxa de padronização divergiam porque
`nota_tecnica_insumos.md` (a "fonte autoritativa" da NT) **não tinha gerador
versionado** — era editado à mão e ficava para trás a cada run. Essa causa-raiz
foi corrigida nesta entrega (célula `11e`).

## 2. Reconciliação numérica (valores verificados no snapshot)

Legenda: ✅ confere · ⚠️ mesma medida com definição/denominador diferente ·
❌ stale ou erro.

### 2.1 Entregas

| Métrica | **Dados (CSV)** | insumos.md antigo / handout | Nota Técnica (docx) |
|---|---|---|---|
| Total | **4.574** | 4.574 ✅ | sinopse 4.574 / Tab.5 e Ap.D.1 **4.573** ❌ |
| Eixos | **2.418 · 1.241 · 644 · 148 · 123** | idem ✅ | Tab.5: 2.414/654/140 ❌ · D.1: Governança 124 ❌ |
| Top 3 produtos | **694 · 685 · 677** | idem ✅ | idem ✅ |
| Integração à base de dados (legado) | **109** | 110 ❌ | 110 ❌ |
| Padronização | **exato 73,4% · alias 15,0% · fuzzy 11,6% · 0 UNMATCHED** (via `produto_method`) | "90,7% / 9,3%" ❌ não-reprodutível | "93,2% / 6,8%" ❌ não-reprodutível |
| Média/mediana/máx/mín | **80,2 / 57 / ANVISA 348 / CONAB 7** | idem ✅ | idem ✅ |
| Concentração top-20% | **49,3%** (11 maiores órgãos) | "mais da metade" ❌ | — |
| Datas em dezembro | **27,6%** (de 2.903 parseáveis) | 30% ⚠️ | 30% ⚠️ |
| needs_review | **2.679 (58,6%)**, cross-validation 2.209 | 2.679; "~2.095" ⚠️ | — |
| Produto "Outros" | **148** (29 fragmentos <10 chars) | 148; fragmentos "43" ❌ (são 29) | Tab.5 140 ❌ / D.1 148 ✅ |
| Produtos com pactuação | **16 canônicos de 44 + 5 legados** | "20 dos 44 canônicos" ❌ (mistura legados) | idem ❌ |
| Cobertura | **79/91 (86,8%)** = 57+22 | 87% ✅ | 87% ✅ |
| PDFs (manifest) | **61+65 = 126 · 58 únicos** | "86+91=177 · 98 únicos" ❌ (run antigo) | "177" ❌ |

### 2.2 Riscos

| Métrica | **Dados (CSV)** | insumos.md antigo / handout | Nota Técnica (docx) |
|---|---|---|---|
| Total | **619** | 619 ✅ | sinopse 619 / Tab.1 e D.1 **595** ❌ |
| Prob. canônica | **604/619 (97,6%)** — raro 37 · pouco 243 · provável 234 · muito 68 · pratic. certo 22 | 599 (96,8%); dist. 244/234/63/37/21 ❌ | "74% (439)" ⚠️ (mede prob∧imp sobre 595) · dist. sobre subconjunto ❌ |
| Impacto canônico | **601/619 (97,1%)** — baixo 46 · médio 155 · alto 262 · muito alto 138 | 597 (96,4%); muito alto 134 ❌ | 601 (97,1%) ✅ · dist. sobre subconjunto ❌ |
| Prob ∧ imp canônicos | **592 (95,6%)**; 27 residuais: CADE 3 · CENSIPAM 3 · CVM 4 · DNOCS 6 · IBAMA 1 · IBGE 1 · MJSP 2 · MMULHERES 1 · MPOR 5 · PRF 1 | "583 (94%) · 36 residuais" ❌ | "439 (74%) · 156 de CENSIPAM/ANTAQ/PRF/SUSEP" ❌ (run antigo, pré-correção de column-shift) |
| Tratamento canônico | **584/619 (94,3%)** = 579 simples + 5 compostos | 582 (94%) ⚠️ | 579 (D.1) ⚠️ |
| Mix de tratamento | **mitigar 487 = 84,1% das simples = 78,7% do total** | "84%" ⚠️ (sem denominador) | Tab.6 "79%" vs D.1 "84,1%" ⚠️ (denominadores distintos não declarados) |
| Zona crítica | **218 (35,2%)** | **141** ❌ | D.1 218 ✅ |
| Severidade máxima | **13** — ANA, ANATEL, CAPES, INSS, MDHC, MESP, MME, MPO (2), MRE (2), SGPR (2) | 10 ❌ (sem MDHC; MPO/SGPR 1) | 11 ❌ (sem MESP; MPO 1) |
| Sem ações de tratamento | **26 (4,2%)** (campo vazio) | "30%" ❌ | "23% ou 26 (4,2%)" ⚠️ (texto confuso; o nº certo está lá) |
| Texto repetido ≥3 órgãos | **311 (50,2%)** | "32%" ❌ | "52%" ⚠️ (definição próxima) |
| Exclusivamente "mitigar" | **22 órgãos** | 12 ❌ | — |
| Dependência de fornecedor | **28 riscos · 26 órgãos · 16 na zona crítica** (keyword "fornecedor") | 23 · 22 · 15 ⚠️ (keyword não documentada) | idem ⚠️ |
| Cobertura | **76/91 (83,5%)** = 51+25 | 76/91 (83%) ✅ | "71 de 86" ❌ (run antigo) |
| needs_review | **86 (13,9%)** | 86 ✅ | — |

### 2.3 Inconsistências internas da Nota Técnica

A NT contradiz a si mesma — sinais claros de tabelas geradas em runs diferentes:

- Entregas **4.574 (sinopse) vs 4.573 (Tab.5, D.1)**; riscos **619 vs 595**.
- Eixos da Tab.5 ≠ Ap.D.1 em 3 de 5 eixos.
- Tratamento Tab.6 (79%) ≠ Ap.D.1 (84,1%) sem declarar denominadores.
- Data de coleta "**abril de 2026**" (3 ocorrências) — o snapshot é de
  **12/05/2026**; o handout pede "maio".
- Placeholder "**NOTA TÉCNICA Nº XX/2026**" e **Declaração de IA duplicada**
  (Seção 4 e seção própria).
- Grafia `SG-PR` (NT) vs `SGPR` (dados) — cosmético, mas vale uniformizar.

A errata completa, item a item com old→new, está em **`NT_CORRECOES.md`**.

## 3. Achados de código (revisão)

| # | Achado | Situação |
|---|---|---|
| C1 | `nota_tecnica_insumos.md` sem gerador versionado — causa-raiz do drift | **Corrigido**: célula `11e_nt_insumos.py` (stdlib, determinística, idempotente; atualiza o registro no `manifest.json`); teste de paridade exige md commitado == gerador(CSVs) |
| C2 | Aliases das seções 3.1/3.2 do handout ausentes | **Corrigido**: +9 `PRODUTO_ALIASES`, +3 `EIXO_ALIASES` em `02_config.py`, com testes |
| C3 | "Aliases duplicados no notebook" | **Não era bug**: `ptd_scraper.ipynb` é GERADO de `notebook_cells/` por `build_notebook.py`, com CI bloqueando drift — bastou rebuild |
| C4 | Handout 3.3 pede `"baixo"→"raro"`, código tem `"baixo"→"pouco provável"` | **Mantido o código** (consistente com `"baixa"` da escala ANTAQ); decidir só após inspecionar o PDF do IBAMA — teste fixa o comportamento atual |
| C5 | Handout 3.5–3.8 (column bleed, MMULHERES, CADE, MJSP) como "pendentes" | **Já existiam** em `07b_extract_risks.py` + aliases; não duplicados. Os residuais atuais são 27 (não 36) e incluem órgãos fora da lista do handout — verificar nos PDFs (Track B) |
| C6 | `13c_publish_helper.py` exigia `review_queue_prioritized.csv` (inexistente: o real é `review_queue.csv`) e zipava só 14 arquivos top-level, omitindo `vocabulary_mapping.csv`, `figures/`, `harmonized/`, `metadata/` — que o dashboard consome | **Corrigido**: valida 16 essenciais (falha listando ausentes) e zipa `output/` inteiro recursivamente; testes novos |
| C7 | README §Publicar prometia "14 artefatos"/"substitui output/ inteira" e omitia `build_metadata.py`/`build_corpus.py` — o fluxo documentado **quebraria o CI** (pytest exige derivados em dia; `build_metadata.py` também regrava `index.html`) | **Corrigido**: seção reescrita com o fluxo real |
| C8 | Threshold de aceite de produto é **0,80** (`03_utils.py`), mas NT/handout documentam "≥0,85" | Esclarecido: 0,85 é o corte de `fuzzy_high` (sem `needs_review`); 0,70–0,85 marca revisão. Corrigir a redação da NT |
| C9 | `.gitignore` bloqueava `run_pipeline.py` (entrada de rascunho antiga) | **Corrigido** (removidas 4 entradas mortas) |
| C10 | 3 PNGs órfãos commitados em `output/figures/` (o 11b atual gera 6, há 9) e `manifest.json#outputs` inclui sobras do Drive | Documentado; o primeiro PR do refresh mensal converge (delete-then-copy do `--sync`) |
| C11 | Print "55 produtos canônicos" em `02_config.py` — são 44 canônicos + 11 legados | Cosmético; não alterado |

Verificações que **passaram** sem ressalva: dedup MD5 por grupos ministeriais;
cross-validation produto↔eixo com `needs_review` informativo (2.209 menções);
`QUALITY_THRESHOLDS` coerentes com o snapshot (4.574 ≤ 4.700; 619 ≤ 700);
`output/` ≡ `output/harmonized/` (620 linhas em ambos os risks.csv);
`validation_report.json` ≡ recomputo independente (604/601/584).

## 4. O que foi implementado nesta entrega

**Código do pipeline**
- `02_config.py` — 12 aliases novos (truncamentos e caractere colado de PDF).
- `09b_standardization.py` — `filter_fragment_deliveries()`: descarta
  `Outros` com `servico_acao` <10 chars (29 registros no snapshot; vale a
  partir do próximo run → corpus ≈ 4.545). Curadoria preservada: texto livre
  substantivo de Projetos Especiais não é tocado.
- `11e_nt_insumos.py` — gerador reproduzível dos insumos da NT (seção 0 com
  proveniência e definições; números pt-BR; carimbo do manifest).
- `13c_publish_helper.py` — reescrito (16 essenciais + zip recursivo).
- `ptd_scraper.ipynb` — reconstruído (31 células) via `build_notebook.py`.

**Automação**
- `run_pipeline.py` — orquestrador headless: exec sequencial das células,
  preflight do portal (testado: HTTP 403 neste ambiente → exit 2 limpo),
  gate de qualidade com **pisos** (órgãos ≥80, entregas ≥3.500, riscos ≥450)
  além dos tetos existentes, e `--sync` (substitui `output/` e regenera
  derivados + `index.html`).
- `.github/workflows/monthly-refresh.yml` — **trigger mensal** (dia 2,
  06:17 UTC + `workflow_dispatch`): roda o pipeline no runner, só abre PR
  `data-refresh/YYYY-MM` se os CSVs sem timestamp mudaram; corpo do PR com
  métricas do `validation_report.json`; log como artifact.

**Dados e documentação**
- `output/nota_tecnica_insumos.md` — regenerado pelo 11e (zona crítica
  141→218, severidade 10→13, etc.); `manifest.json` e `metadata/prov.jsonld`
  atualizados em cadeia; `build_corpus.py --check` OK.
- `README.md` — §Publicar corrigido; nova §Atualização mensal; execução
  headless documentada.
- Testes: `tests/test_nt_insumos.py` (aliases, filtro, gerador, paridade
  md↔CSVs) e `tests/test_publish_helper.py`. Suíte: **228 passed**;
  smoke test 4/4.

## 5. Pendências (fora do alcance deste ambiente)

1. **Secret `DATA_REFRESH_PAT`** (fine-grained: Contents RW + Pull requests RW)
   para os PRs do refresh dispararem o CI; sem ele, fechar/reabrir o PR.
2. **Primeiro run do workflow** (Actions → monthly data refresh → Run
   workflow). Possível bloqueio de IP de runner pelo gov.br — o preflight
   falha com mensagem clara; fallback Colab continua válido. No primeiro PR,
   espere: remoção dos 3 PNGs órfãos, `manifest.json#outputs` enxuto e
   surgimento condicional de `review_queue_prioritized.csv`.
3. **Track B (Colab + PDFs)**: rerun para materializar os aliases (531
   `fuzzy_high` devem cair para ~100) e o filtro (corpus ≈4.545); inspecionar
   PDFs de IBAMA (`"baixo"`), CADE (escala 1-Alto), MMULHERES, MPOR/DNOCS,
   MJSP para os 27 residuais.
4. **Nota Técnica (.docx)**: aplicar `NT_CORRECOES.md` — o arquivo está fora
   do repositório e é editado pelos autores.
5. **Handout §8**: existe um run mais novo "com mais órgãos" ainda não
   commitado; quando entrar, regenerar insumos (`11e`) e revalidar a NT.
