# ============================================================
# CÉLULA 11E — Insumos para a Nota Técnica (gerador reproduzível)
# ============================================================
# Regenera output/nota_tecnica_insumos.md a partir dos CSVs exportados,
# com TODAS as métricas computadas e definições explícitas. Este arquivo
# é a fonte única dos números citados na Nota Técnica — antes deste
# gerador, o .md era editado à mão e derivava dos dados a cada run
# (ex.: zona crítica 141 vs 218 reais no snapshot 2026-05-12).
#
# Uso standalone (recomputa sobre os CSVs commitados, sem rede):
#   python notebook_cells/11e_nt_insumos.py [output_dir]
#
# Determinismo: o conteúdo não embute timestamp de geração — o carimbo
# vem de manifest.json (data_execucao/commit), então regenerar sobre o
# mesmo snapshot produz bytes idênticos.
import csv
import hashlib
import json
import os
import re
import statistics
import unicodedata
from collections import Counter, defaultdict


def _nt_load_csv(path):
    """Lê CSV com BOM (utf-8-sig) como lista de dicts."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _nt_norm(text):
    """Normalização leve para comparação de textos de risco."""
    text = unicodedata.normalize("NFC", str(text or ""))
    return re.sub(r"\s+", " ", text).strip().lower()


def _nt_fmt_int(n):
    """4574 → '4.574' (separador de milhar pt-BR)."""
    return f"{n:,}".replace(",", ".")


def _nt_fmt_pct(x, nd=1):
    """0.529 → '52,9%'."""
    return f"{x * 100:.{nd}f}%".replace(".", ",")


def _nt_month(date_str):
    """Extrai mês (1-12) de data ISO ou dd/mm/aaaa; None se não parseável."""
    s = (date_str or "").strip()
    m = re.search(r"\d{4}-(\d{2})", s)          # ISO aaaa-mm[-dd]
    if not m:
        m = re.match(r"\d{1,2}/(\d{1,2})/\d{4}", s)  # dd/mm/aaaa
    if not m:
        return None
    month = int(m.group(1))
    return month if 1 <= month <= 12 else None


def compute_nt_metrics(output_dir, config):
    """Computa todas as métricas da NT a partir de output/*.csv.

    `config` precisa conter: CANONICAL_PRODUTOS, LEGACY_PRODUTOS,
    PROBABILIDADE_SCALE, IMPACTO_SCALE, TRATAMENTO_OPTIONS,
    PRODUTO_ALIASES, EIXO_ALIASES (símbolos de 02_config.py).
    Cada métrica carrega a definição usada — ver render_nt_insumos.
    """
    D = _nt_load_csv(os.path.join(output_dir, "deliveries.csv"))
    R = _nt_load_csv(os.path.join(output_dir, "risks.csv"))
    C = _nt_load_csv(os.path.join(output_dir, "coverage_summary.csv"))

    prob_scale = list(config["PROBABILIDADE_SCALE"])
    imp_scale = list(config["IMPACTO_SCALE"])
    trat_opts = list(config["TRATAMENTO_OPTIONS"])
    canon_produtos = [p for ps in config["CANONICAL_PRODUTOS"].values() for p in ps]
    legacy_produtos = [p for ps in config["LEGACY_PRODUTOS"].values() for p in ps]
    gov_produtos = config["CANONICAL_PRODUTOS"].get("Governança e Gestão de Dados", [])

    M = {"n_deliveries": len(D), "n_risks": len(R)}

    # ---------------- Cobertura (coverage_summary.csv) ----------------
    st_ent = Counter(r["status_entregas"] for r in C)
    st_ris = Counter(r["status_riscos"] for r in C)
    M["n_signatarios"] = len(C)
    M["ent_proprios"] = st_ent.get("ok", 0)
    M["ent_compartilhados"] = st_ent.get("compartilhado", 0)
    M["ent_sem_dados"] = st_ent.get("sem_dados", 0)
    M["ent_cobertos"] = M["ent_proprios"] + M["ent_compartilhados"]
    M["ris_proprios"] = st_ris.get("ok", 0)
    M["ris_compartilhados"] = st_ris.get("compartilhado", 0)
    M["ris_no_table"] = st_ris.get("no_risk_table", 0)
    M["ris_sem_pdf"] = st_ris.get("sem_pdf", 0)
    M["ris_cobertos"] = M["ris_proprios"] + M["ris_compartilhados"]
    M["orgaos_sem_entregas"] = sorted(
        r["sigla"] for r in C if r["status_entregas"] == "sem_dados")

    # ---------------- Entregas ----------------
    eixo_counts = Counter(r["eixo_normalizado"] for r in D)
    M["eixo_dist"] = eixo_counts.most_common()
    top2 = sum(n for _, n in M["eixo_dist"][:2])
    M["top2_n"], M["top2_pct"] = top2, top2 / len(D)

    prod_counts = Counter(r["produto_normalizado"] for r in D)
    M["top_produtos"] = prod_counts.most_common(6)
    M["prod_method"] = Counter(r["produto_method"] for r in D)
    M["eixo_method"] = Counter(r["eixo_method"] for r in D)

    by_org = Counter(r["orgao_sigla"] for r in D)
    vals = sorted(by_org.values())
    M["n_orgaos_proprios_ent"] = len(by_org)
    M["ent_media"] = sum(vals) / len(vals)
    M["ent_mediana"] = statistics.median(vals)
    M["ent_max"] = max(by_org.items(), key=lambda kv: kv[1])
    M["ent_min"] = min(by_org.items(), key=lambda kv: kv[1])
    # Concentração: share dos 20% maiores órgãos (floor)
    k = max(1, int(len(vals) * 0.2))
    M["lorenz_top20_share"] = sum(sorted(vals, reverse=True)[:k]) / len(D)
    M["lorenz_top20_k"] = k

    M["needs_review_ent"] = sum(
        1 for r in D if (r["needs_review"] or "").strip().lower() in ("true", "1"))
    M["crossval_eixo"] = sum(
        1 for r in D
        if "cross-validation" in (r["review_reason"] or "")
        or "eixo corrigido" in (r["review_reason"] or ""))

    M["outros_n"] = prod_counts.get("Outros", 0)
    M["fragmentos_n"] = sum(
        1 for r in D if r["produto_normalizado"] == "Outros"
        and len((r["servico_acao"] or "").strip()) < 10)

    used = set(prod_counts)
    M["canon_usados"] = sorted(p for p in canon_produtos if p in used)
    M["canon_zero"] = len(canon_produtos) - len(M["canon_usados"])
    M["legacy_usados"] = [(p, prod_counts[p]) for p in legacy_produtos if p in used]
    M["n_canon"], M["n_legacy"] = len(canon_produtos), len(legacy_produtos)
    M["gov_total_prods"] = len(gov_produtos)
    M["gov_canon_usados"] = [(p, prod_counts[p]) for p in gov_produtos if p in used]
    M["n_produto_aliases"] = len(config["PRODUTO_ALIASES"])
    M["n_eixo_aliases"] = len(config["EIXO_ALIASES"])

    ppsi_orgs = {r["orgao_sigla"] for r in D
                 if r["produto_normalizado"] == "Implementação do PPSI"}
    login_orgs = {r["orgao_sigla"] for r in D
                  if r["produto_normalizado"] == "Integração ao Login Único"}
    M["ppsi_orgs"], M["login_orgs"] = len(ppsi_orgs), len(login_orgs)

    months = [_nt_month(r["data_pactuada"]) for r in D]
    months = [m for m in months if m]
    M["datas_parseaveis"] = len(months)
    M["dez_pct"] = (months.count(12) / len(months)) if months else 0.0

    # ---------------- Riscos ----------------
    pc = Counter(r["probabilidade_normalizada"] for r in R
                 if r["probabilidade_normalizada"] in prob_scale)
    ic = Counter(r["impacto_normalizado"] for r in R
                 if r["impacto_normalizado"] in imp_scale)
    M["prob_dist"] = [(lvl, pc.get(lvl, 0)) for lvl in prob_scale]
    M["imp_dist"] = [(lvl, ic.get(lvl, 0)) for lvl in imp_scale]
    M["prob_canon"], M["imp_canon"] = sum(pc.values()), sum(ic.values())

    resid = [r for r in R if not (r["probabilidade_normalizada"] in prob_scale
                                  and r["impacto_normalizado"] in imp_scale)]
    M["both_canon"] = len(R) - len(resid)
    M["residuais_por_orgao"] = sorted(
        Counter(r["orgao_sigla"] for r in resid).items())

    def trat_class(t):
        t = (t or "").strip()
        if not t:
            return "vazio"
        if t in trat_opts:
            return "single"
        parts = [p.strip() for p in t.split(";") if p.strip()]
        return "composto" if parts and all(p in trat_opts for p in parts) else "fora"

    tcls = Counter(trat_class(r["tratamento_normalizado"]) for r in R)
    M["trat_classes"] = tcls
    M["trat_canon"] = tcls["single"] + tcls["composto"]
    M["trat_singles"] = Counter(
        r["tratamento_normalizado"] for r in R
        if trat_class(r["tratamento_normalizado"]) == "single")

    prob_hi = set(prob_scale[2:])     # provável, muito provável, praticamente certo
    imp_hi = set(imp_scale[3:])       # alto, muito alto
    zc = [r for r in R if r["probabilidade_normalizada"] in prob_hi
          and r["impacto_normalizado"] in imp_hi]
    M["zona_critica"] = len(zc)
    sev = [r for r in R if r["probabilidade_normalizada"] == prob_scale[-1]
           and r["impacto_normalizado"] == imp_scale[-1]]
    M["sev_max"] = len(sev)
    M["sev_max_orgaos"] = sorted(Counter(r["orgao_sigla"] for r in sev).items())

    M["sem_acoes"] = sum(1 for r in R if not (r["acoes_tratamento"] or "").strip())

    by_text = defaultdict(set)
    for r in R:
        by_text[_nt_norm(r["risco_texto"])].add(r["orgao_sigla"])
    rep = {t for t, orgs in by_text.items() if t and len(orgs) >= 3}
    M["texto_repetido"] = sum(1 for r in R if _nt_norm(r["risco_texto"]) in rep)

    org_trats = defaultdict(set)
    for r in R:
        if trat_class(r["tratamento_normalizado"]) in ("single", "composto"):
            for p in r["tratamento_normalizado"].split(";"):
                org_trats[r["orgao_sigla"]].add(p.strip())
    M["so_mitigar"] = sorted(o for o, ts in org_trats.items() if ts == {"mitigar"})

    forn = [r for r in R if "fornecedor" in _nt_norm(r["risco_texto"])]
    M["forn_n"] = len(forn)
    M["forn_orgaos"] = len({r["orgao_sigla"] for r in forn})
    M["forn_zc"] = sum(1 for r in forn if r["probabilidade_normalizada"] in prob_hi
                       and r["impacto_normalizado"] in imp_hi)

    pessoal_kw = ("pessoal", "rotatividade", "equipe", "servidor", "capacita")
    orgs_com_risco = {r["orgao_sigla"] for r in R}
    orgs_pessoal = {r["orgao_sigla"] for r in R
                    if any(k in _nt_norm(r["risco_texto"]) for k in pessoal_kw)}
    M["orgs_sem_pessoal"] = len(orgs_com_risco - orgs_pessoal)
    M["n_orgaos_proprios_ris"] = len(orgs_com_risco)

    M["needs_review_ris"] = sum(
        1 for r in R if (r["needs_review"] or "").strip().lower() in ("true", "1"))

    # Schemas reais (cabeçalhos dos CSVs)
    M["cols_deliveries"] = list(D[0].keys()) if D else []
    M["cols_risks"] = list(R[0].keys()) if R else []
    return M


def render_nt_insumos(M, manifest=None):
    """Renderiza o markdown dos insumos a partir das métricas computadas."""
    man = manifest or {}
    fi, fp = _nt_fmt_int, _nt_fmt_pct
    nD, nR = M["n_deliveries"], M["n_risks"]
    nS = M["n_signatarios"]

    eixo_lines = "\n".join(
        f"  - {eixo}: {fi(n)} ({fp(n / nD)})" for eixo, n in M["eixo_dist"])
    top3 = ", ".join(f"{p} ({fi(n)})" for p, n in M["top_produtos"][:3])
    legacy_lines = "\n".join(
        f"  - {p}: {fi(n)} ({fp(n / nD)})" for p, n in M["legacy_usados"])
    prob_lines = ", ".join(f"{lvl} ({n})" for lvl, n in M["prob_dist"] if n)
    imp_lines = ", ".join(f"{lvl} ({n})" for lvl, n in M["imp_dist"] if n)
    ts = M["trat_singles"]
    trat_line = " · ".join(
        f"{k} {fi(v)} ({fp(v / M['trat_classes']['single'])} das simples; "
        f"{fp(v / nR)} do total)"
        for k, v in ts.most_common())
    residuais = ", ".join(f"{o} ({n})" for o, n in M["residuais_por_orgao"])
    sev_orgaos = ", ".join(
        f"{o} ({n})" if n > 1 else o for o, n in M["sev_max_orgaos"])
    gov_usados = ", ".join(f"{p} ({n})" for p, n in M["gov_canon_usados"]) or "nenhum"
    pm = M["prod_method"]
    deterministico = pm.get("exact", 0) + pm.get("alias", 0)
    sem_entregas = ", ".join(M["orgaos_sem_entregas"])

    return f"""# Insumos para Nota Técnica IPEA
# Corpus dos Planos de Transformação Digital: coleta, padronização e análise

<!-- GERADO por notebook_cells/11e_nt_insumos.py — não editar à mão.
     Para atualizar: python notebook_cells/11e_nt_insumos.py [output_dir]
     Snapshot: {man.get("data_execucao", "(rodar pipeline)")} · \
commit do pipeline: {man.get("pipeline_commit", "—")} -->

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
- **Match determinístico**: `produto_method` ∈ {{exact, alias}};
  **fuzzy**: `produto_method` ∈ {{fuzzy_high (≥0,85), fuzzy_low (≥0,70)}}.
- **Dependência de fornecedor**: substring "fornecedor" em `risco_texto`.
- **Risco de pessoal**: `risco_texto` contém pessoal/rotatividade/equipe/
  servidor/capacita.

---

### SINOPSE (números para o parágrafo)

- {nS} órgãos signatários · entregas: {fi(nD)} registros de {M["ent_cobertos"]} \
órgãos · riscos: {fi(nR)} registros de {M["ris_cobertos"]} órgãos
- Instituição: Decreto nº 12.198/2024 (EFGD 2024-2027); regulamentação dos
  PTDs: Portaria SGD/MGI nº 6.618/2024

---

### 2 METODOLOGIA — métricas

**2.1 Coleta dos dados**

| Etapa | Resultado |
|-------|-----------|
| Scraping da página gov.br | {nS} órgãos signatários |
| Download dos PDFs | {man.get("pdfs_diretivo", "—")} Diretivos + \
{man.get("pdfs_entregas", "—")} Entregas = {man.get("pdfs_baixados", "—")} PDFs |
| Desduplicação MD5 (grupos ministeriais) | \
{man.get("pdfs_dedup_owners", "—")} PDFs únicos |
| Extração de entregas | {fi(nD)} registros de {M["ent_cobertos"]} órgãos \
({M["ent_proprios"]} próprios + {M["ent_compartilhados"]} compartilhados) |
| Extração de riscos | {fi(nR)} registros de {M["ris_cobertos"]} órgãos \
({M["ris_proprios"]} próprios + {M["ris_compartilhados"]} compartilhados) |

- Cobertura de entregas: {fp(M["ent_cobertos"] / nS)} ({M["ent_cobertos"]}/{nS});
  {M["ent_sem_dados"]} órgãos sem dados extraíveis: {sem_entregas}
- Cobertura de riscos: {fp(M["ris_cobertos"] / nS)} ({M["ris_cobertos"]}/{nS});
  {M["ris_no_table"]} com PDF Diretivo sem tabela de riscos extraível,
  {M["ris_sem_pdf"]} sem PDF Diretivo publicado

**2.2 Padronização de vocabulário**

- Catálogo: {M["n_canon"]} produtos canônicos (template v4.0, 5 eixos) +
  {M["n_legacy"]} legados (PPSI, Integração à base de dados, "Outros", etc.)
- Aliases determinísticos: {M["n_produto_aliases"]} de produto ·
  {M["n_eixo_aliases"]} de eixo
- Resultado do matching de produto ({fi(nD)} registros):
  exato {fi(pm.get("exact", 0))} ({fp(pm.get("exact", 0) / nD)}) ·
  alias {fi(pm.get("alias", 0))} ({fp(pm.get("alias", 0) / nD)}) ·
  fuzzy ≥0,85 {fi(pm.get("fuzzy_high", 0))} ({fp(pm.get("fuzzy_high", 0) / nD)}) ·
  UNMATCHED {pm.get("unmatched", 0)}
- Determinístico (exato+alias): {fp(deterministico / nD)}
  — nota: rascunhos anteriores citavam "90,7% exato"; esse valor não é
  reprodutível a partir de `produto_method` e não deve ser usado
- Eixo declarado ausente no PDF em {fi(M["eixo_method"].get("unmatched", 0))}
  registros ({fp(M["eixo_method"].get("unmatched", 0) / nD)}) — nesses casos o
  eixo é derivado do produto via cross-validation

**2.6 Estrutura do corpus (schemas reais)**

- `deliveries.csv` — {fi(nD)} linhas × {len(M["cols_deliveries"])} colunas:
  {", ".join(M["cols_deliveries"])}
- `risks.csv` — {fi(nR)} linhas × {len(M["cols_risks"])} colunas:
  {", ".join(M["cols_risks"])}

---

### 3 RESULTADOS

**3.1 Panorama das entregas**

- {fi(nD)} entregas pactuadas por {M["ent_cobertos"]} órgãos
  ({M["ent_proprios"]} próprios + {M["ent_compartilhados"]} via PTD ministerial)
- Distribuição por eixo:
{eixo_lines}
- Top 2 eixos concentram {fi(M["top2_n"])} entregas ({fp(M["top2_pct"])})
- {len(M["canon_usados"])} dos {M["n_canon"]} produtos canônicos têm ≥1
  pactuação; {M["canon_zero"]} têm zero. Produtos legados com pactuação:
{legacy_lines}
- Top 3 produtos: {top3}
- Média: {str(round(M["ent_media"], 1)).replace(".", ",")} entregas/órgão · \
Mediana: {fi(int(M["ent_mediana"]))} ·
  Máx: {M["ent_max"][0]} ({fi(M["ent_max"][1])}) · Mín: {M["ent_min"][0]} ({M["ent_min"][1]})
- Concentração: os {M["lorenz_top20_k"]} maiores órgãos (20%) detêm
  {fp(M["lorenz_top20_share"])} das entregas
- Produto "Outros" (Projetos Especiais): {fi(M["outros_n"])} registros
  ({fp(M["outros_n"] / nD)}) — texto livre validado pela curadoria;
  {M["fragmentos_n"]} deles são fragmentos (servico_acao <10 chars) que o
  pipeline passa a descartar no próximo run (filter_fragment_deliveries)
- {fp(M["dez_pct"])} das datas pactuadas parseáveis
  ({fi(M["datas_parseaveis"])}) concentram-se em dezembro
- needs_review: {fi(M["needs_review_ent"])} ({fp(M["needs_review_ent"] / nD)}),
  dos quais {fi(M["crossval_eixo"])} são o flag informativo de cross-validation
  produto↔eixo (não indicam erro)

**3.2 Panorama dos riscos**

- {fi(nR)} riscos mapeados por {M["ris_cobertos"]} órgãos
  ({M["ris_proprios"]} próprios + {M["ris_compartilhados"]} via PTD ministerial)
- Probabilidade canônica: {M["prob_canon"]}/{fi(nR)}
  ({fp(M["prob_canon"] / nR)}) — {prob_lines}
- Impacto canônico: {M["imp_canon"]}/{fi(nR)}
  ({fp(M["imp_canon"] / nR)}) — {imp_lines}
- Probabilidade E impacto canônicos: {M["both_canon"]}
  ({fp(M["both_canon"] / nR)}); {nR - M["both_canon"]} residuais: {residuais}
- Tratamento canônico: {M["trat_canon"]}/{fi(nR)} ({fp(M["trat_canon"] / nR)}),
  sendo {M["trat_classes"]["single"]} simples + {M["trat_classes"]["composto"]}
  compostos; {M["trat_classes"].get("vazio", 0)} vazios ·
  {M["trat_classes"].get("fora", 0)} fora da escala
- Distribuição (simples): {trat_line}
- Zona crítica: {fi(M["zona_critica"])} riscos ({fp(M["zona_critica"] / nR)})
- Severidade máxima: {M["sev_max"]} riscos — {sev_orgaos}
- Sem ações de tratamento (campo vazio): {M["sem_acoes"]}
  ({fp(M["sem_acoes"] / nR)})
- Texto repetido em ≥3 órgãos: {fi(M["texto_repetido"])}
  ({fp(M["texto_repetido"] / nR)}) — proxy de reprodução do referencial SGD
- {len(M["so_mitigar"])} órgãos usam exclusivamente "mitigar":
  {", ".join(M["so_mitigar"])}
- needs_review: {M["needs_review_ris"]} ({fp(M["needs_review_ris"] / nR)})

**3.3 Achados transversais (quantitativos)**

- **Governança de Dados residual**: dos {M["gov_total_prods"]} produtos
  canônicos do eixo, com pactuação: {gov_usados}. Os
  {fi(dict(M["eixo_dist"]).get("Governança e Gestão de Dados", 0))} registros
  do eixo vêm de produtos LEGADOS (Integração à base de dados,
  Interoperabilidade de Sistemas)
- **Difusão**: PPSI presente em {M["ppsi_orgs"]}/{M["n_orgaos_proprios_ent"]}
  órgãos próprios ({fp(M["ppsi_orgs"] / M["n_orgaos_proprios_ent"], 0)}),
  Login Único em {M["login_orgs"]}/{M["n_orgaos_proprios_ent"]}
  ({fp(M["login_orgs"] / M["n_orgaos_proprios_ent"], 0)}); nenhum produto é
  universal
- **Dependência de fornecedor**: {M["forn_n"]} riscos em {M["forn_orgaos"]}
  órgãos próprios; {M["forn_zc"]} na zona crítica
- **Risco de pessoal/TI**: {M["orgs_sem_pessoal"]} de
  {M["n_orgaos_proprios_ris"]} órgãos com riscos
  ({fp(M["orgs_sem_pessoal"] / M["n_orgaos_proprios_ris"], 0)}) não mencionam
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
"""


def write_nt_insumos(output_dir, config):
    """Computa, renderiza e grava nota_tecnica_insumos.md; atualiza o
    registro do arquivo em manifest.json (linhas/bytes/sha256) se existir."""
    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    metrics = compute_nt_metrics(output_dir, config)
    content = render_nt_insumos(metrics, manifest)

    out_path = os.path.join(output_dir, "nota_tecnica_insumos.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    if manifest.get("outputs", {}).get("nota_tecnica_insumos.md") is not None:
        raw = content.encode("utf-8")
        manifest["outputs"]["nota_tecnica_insumos.md"] = {
            "linhas": content.count("\n"),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print(f"nota_tecnica_insumos.md regenerado em {out_path} "
          f"({metrics['n_deliveries']} entregas, {metrics['n_risks']} riscos, "
          f"zona crítica {metrics['zona_critica']}, "
          f"severidade máx. {metrics['sev_max']})")
    return out_path


# ---- Execução ----
# No notebook: usa o namespace das células anteriores (DIRS, catálogos).
# Standalone: exec de 02_config.py para obter os catálogos.
if "DIRS" in globals() and "CANONICAL_PRODUTOS" in globals():
    write_nt_insumos(DIRS["output"], globals())
elif __name__ == "__main__":
    import sys
    _out_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    _cfg_ns = {}
    _cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "02_config.py")
    with open(_cfg_path, encoding="utf-8") as _f:
        exec(_f.read(), _cfg_ns)
    write_nt_insumos(_out_dir, _cfg_ns)
