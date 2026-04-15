# ============================================================
# CÉLULA 11c — Geração de Dados para o Dashboard
# ============================================================
# Gera data.js (9 constantes JS), statistics_summary.json,
# coverage_summary.csv e pdf_metadata.csv a partir dos dados
# extraídos pelo pipeline.
#
# Depende de: all_organs, all_deliveries, all_risks, all_errors,
#             DIRS, CANONICAL_EIXOS, PROBABILIDADE_SCALE,
#             IMPACTO_SCALE, fuzzy_match_produto
# ============================================================

from collections import Counter, defaultdict
from datetime import datetime
import statistics as stats_mod

# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------

_MONTH_MAP = {
    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
    "set": "09", "out": "10", "nov": "11", "dez": "12",
}


def _parse_year_month(date_str: str) -> Optional[str]:
    """Extrai 'YYYY-MM' de formatos variados de data_pactuada.

    Formatos suportados:
      - 'mar. 2025 (v2)'   → '2025-03'
      - 'DD/MM/YYYY'       → 'YYYY-MM'
      - 'MM/YYYY'          → 'YYYY-MM'
    """
    if not date_str or not date_str.strip():
        return None
    s = date_str.strip().lower()

    # Formato 'mes. YYYY ...'
    for abbr, num in _MONTH_MAP.items():
        if s.startswith(abbr):
            m_year = re.search(r"(\d{4})", s)
            if m_year:
                return f"{m_year.group(1)}-{num}"

    # Formato DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}"

    # Formato MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(2)}-{m.group(1).zfill(2)}"

    return None


def _read_pdf_metadata(organs: list) -> List[dict]:
    """Lê metadados dos PDFs baixados (tamanho, datas)."""
    rows = []
    for organ in organs:
        for tipo, path in [("diretivo", organ.pdf_path_diretivo),
                           ("entregas", organ.pdf_path_entregas)]:
            if not path or not os.path.exists(path):
                continue
            stat = os.stat(path)
            size_kb = int(stat.st_size / 1024)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

            # Tentar ler data de criação do PDF via pypdf
            creation_date = mtime
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                info = reader.metadata
                if info and info.creation_date:
                    creation_date = info.creation_date.strftime("%Y-%m-%d")
            except Exception:
                pass

            rows.append({
                "sigla": organ.sigla,
                "tipo": tipo,
                "data_criacao_pdf": creation_date,
                "data_modificacao_pdf": mtime,
                "vigencia": "",
                "tamanho_kb": size_kb,
            })
    return rows


# -----------------------------------------------------------------
# 1. PTD_STATS  (espelha statistics_summary.json)
# -----------------------------------------------------------------
organs_with_risks = set(r.orgao_sigla for r in all_risks) if all_risks else set()
organs_with_deliveries = set(d.orgao_sigla for d in all_deliveries) if all_deliveries else set()

# Entregas por eixo
eixo_counter = Counter(d.eixo_normalizado for d in all_deliveries if d.eixo_normalizado)
entregas_por_eixo = {e: eixo_counter.get(e, 0) for e in CANONICAL_EIXOS if eixo_counter.get(e, 0) > 0}

# Top 5 produtos
prod_counter = Counter(d.produto_normalizado for d in all_deliveries if d.produto_normalizado)
top5_produtos = dict(prod_counter.most_common(5))

# Distribuições de riscos (apenas valores canônicos)
prob_counter = Counter(r.probabilidade_normalizada for r in all_risks if r.probabilidade_normalizada)
imp_counter = Counter(r.impacto_normalizado for r in all_risks if r.impacto_normalizado)
trat_counter = Counter()
for r in all_risks:
    for t in str(r.tratamento_normalizado).split(";"):
        t = t.strip()
        if t:
            trat_counter[t] += 1

dist_prob = {p: prob_counter.get(p, 0) for p in PROBABILIDADE_SCALE}
dist_imp = {i: imp_counter.get(i, 0) for i in IMPACTO_SCALE}
dist_trat = {t: c for t, c in trat_counter.most_common()}

# Riscos canônicos (com probabilidade e impacto em escalas canônicas)
n_canonicos = sum(1 for r in all_risks
                  if r.probabilidade_normalizada in PROBABILIDADE_SCALE
                  and r.impacto_normalizado in IMPACTO_SCALE)

# Entregas por órgão (para média/mediana)
del_per_organ = Counter(d.orgao_sigla for d in all_deliveries)
del_counts = [c for c in del_per_organ.values()] if del_per_organ else [0]

# PDFs escaneados pendentes
n_scan = sum(1 for e in all_errors if "scan" in e.error_type.lower() or "ocr" in e.error_message.lower())

ptd_stats = {
    "data_execucao": datetime.now().strftime("%Y-%m-%d"),
    "orgaos_total": len(all_organs),
    "entregas_total": len(all_deliveries),
    "entregas_orgaos": len(organs_with_deliveries),
    "riscos_total": len(all_risks),
    "riscos_orgaos": len(organs_with_risks),
    "riscos_canonicos": n_canonicos,
    "pdfs_escaneados_pendentes": n_scan,
    "top5_produtos": top5_produtos,
    "entregas_por_eixo": entregas_por_eixo,
    "distribuicao_probabilidade": dist_prob,
    "distribuicao_impacto": dist_imp,
    "distribuicao_tratamento": dist_trat,
    "media_entregas_por_orgao": round(stats_mod.mean(del_counts), 1) if del_counts else 0,
    "mediana_entregas_por_orgao": int(stats_mod.median(del_counts)) if del_counts else 0,
}

# -----------------------------------------------------------------
# 2. PTD_ORGANS
# -----------------------------------------------------------------
# Pré-computar contagens por órgão
risk_count = Counter(r.orgao_sigla for r in all_risks)
del_count = Counter(d.orgao_sigla for d in all_deliveries)

# Status por órgão
organ_status_map = {}
for e in all_errors:
    key = (e.orgao_sigla, e.document_type)
    if key not in organ_status_map:
        organ_status_map[key] = e.error_type

ptd_organs = []
for organ in sorted(all_organs, key=lambda o: o.sigla):
    # Breakdown de eixo e produto
    organ_deliveries = [d for d in all_deliveries if d.orgao_sigla == organ.sigla]
    eixo_bd = dict(Counter(d.eixo_normalizado for d in organ_deliveries if d.eixo_normalizado))
    prod_bd = dict(Counter(d.produto_normalizado for d in organ_deliveries if d.produto_normalizado))

    # Status
    if del_count.get(organ.sigla, 0) > 0:
        s_entregas = "ok"
    elif not organ.pdf_path_entregas and not organ.url_entregas:
        s_entregas = "sem_pdf"
    else:
        err_key = (organ.sigla, "entregas")
        s_entregas = organ_status_map.get(err_key, "sem_dados")

    if risk_count.get(organ.sigla, 0) > 0:
        s_riscos = "ok"
    elif not organ.pdf_path_diretivo and not organ.url_diretivo:
        s_riscos = "sem_pdf"
    else:
        err_key = (organ.sigla, "diretivo")
        s_riscos = organ_status_map.get(err_key, "sem_dados")

    ptd_organs.append({
        "sigla": organ.sigla,
        "grupo": organ.grupo or "",
        "pdf_diretivo": bool(organ.pdf_path_diretivo or organ.url_diretivo),
        "pdf_entregas": bool(organ.pdf_path_entregas or organ.url_entregas),
        "n_entregas": del_count.get(organ.sigla, 0),
        "n_riscos": risk_count.get(organ.sigla, 0),
        "status_entregas": s_entregas,
        "status_riscos": s_riscos,
        "url_diretivo": organ.url_diretivo or "",
        "url_entregas": organ.url_entregas or "",
        "eixo_breakdown": eixo_bd,
        "produto_breakdown": prod_bd,
    })

# -----------------------------------------------------------------
# 3. PTD_DELIVERIES  (agrupado por sigla)
# -----------------------------------------------------------------
ptd_deliveries = defaultdict(list)
for d in all_deliveries:
    # Recomputar score do produto
    _, pscore = fuzzy_match_produto(d.produto_original) if d.produto_original else ("", 0.0)
    if d.produto_normalizado and d.produto_normalizado == d.produto_original:
        pscore = 1.0

    ptd_deliveries[d.orgao_sigla].append({
        "orgao_sigla": d.orgao_sigla,
        "servico_acao": d.servico_acao or "",
        "produto_original": d.produto_original or "",
        "produto_normalizado": d.produto_normalizado or "",
        "produto_score": round(pscore, 2),
        "eixo_original": d.eixo_original or "",
        "eixo_normalizado": d.eixo_normalizado or "",
        "data_pactuada": d.data_pactuada or "",
        "confidence": d.extraction_confidence or "high",
    })
ptd_deliveries = dict(ptd_deliveries)

# -----------------------------------------------------------------
# 4. PTD_RISKS  (agrupado por sigla, com id_risco sequencial)
# -----------------------------------------------------------------
ptd_risks = defaultdict(list)
for r in all_risks:
    organ_risks = ptd_risks[r.orgao_sigla]
    idx = len(organ_risks)
    id_letter = chr(65 + idx) if idx < 26 else f"R{idx + 1}"

    ptd_risks[r.orgao_sigla].append({
        "orgao_sigla": r.orgao_sigla,
        "id_risco": id_letter,
        "risco_texto": r.risco_texto or "",
        "probabilidade_original": r.probabilidade_original or "",
        "probabilidade_normalizada": r.probabilidade_normalizada or "",
        "impacto_original": r.impacto_original or "",
        "impacto_normalizado": r.impacto_normalizado or "",
        "tratamento_original": r.tratamento_original or "",
        "tratamento_normalizado": r.tratamento_normalizado or "",
        "acoes_original": r.acoes_tratamento or "",
        "acoes_resolvidas": r.acoes_tratamento or "",
    })
ptd_risks = dict(ptd_risks)

# -----------------------------------------------------------------
# 5. PTD_DATES  (sigla → data mais antiga do PDF)
# -----------------------------------------------------------------
pdf_meta_rows = _read_pdf_metadata(all_organs)

ptd_dates = {}
for row in pdf_meta_rows:
    sigla = row["sigla"]
    d = row["data_criacao_pdf"]
    if sigla not in ptd_dates or d < ptd_dates[sigla]:
        ptd_dates[sigla] = d

# Garantir todas as siglas presentes
for organ in all_organs:
    if organ.sigla not in ptd_dates:
        ptd_dates[organ.sigla] = ""

# -----------------------------------------------------------------
# 6-7. PTD_TIMELINE / PTD_TIMELINE_ORGANS
# -----------------------------------------------------------------
month_deliveries = defaultdict(int)
month_organs = defaultdict(set)

for d in all_deliveries:
    ym = _parse_year_month(d.data_pactuada or "")
    if ym:
        month_deliveries[ym] += 1
        month_organs[ym].add(d.orgao_sigla)

ptd_timeline = dict(sorted(month_deliveries.items()))
ptd_timeline_organs = {k: len(v) for k, v in sorted(month_organs.items())}

# -----------------------------------------------------------------
# 8-9. PTD_JACCARD_ORGANS / PTD_JACCARD_MATRIX
# -----------------------------------------------------------------
# Similaridade de Jaccard baseada em conjuntos de produtos por órgão
organ_products = {}
for d in all_deliveries:
    if d.produto_normalizado:
        organ_products.setdefault(d.orgao_sigla, set()).add(d.produto_normalizado)

jaccard_organs = sorted(organ_products.keys())
n = len(jaccard_organs)
jaccard_matrix = [[0.0] * n for _ in range(n)]

for i in range(n):
    si = organ_products[jaccard_organs[i]]
    for j in range(i, n):
        sj = organ_products[jaccard_organs[j]]
        union = len(si | sj)
        if union == 0:
            sim = 0.0
        else:
            sim = round(len(si & sj) / union, 3)
        jaccard_matrix[i][j] = sim
        jaccard_matrix[j][i] = sim

# =================================================================
# Gravar arquivos
# =================================================================

out_dir = DIRS["output"]

# --- data.js ---
js_path = os.path.join(out_dir, "data.js")
with open(js_path, "w", encoding="utf-8") as f:
    f.write(f"const PTD_STATS = {json.dumps(ptd_stats, ensure_ascii=False)};\n")
    f.write(f"const PTD_ORGANS = {json.dumps(ptd_organs, ensure_ascii=False)};\n")
    f.write(f"const PTD_DELIVERIES = {json.dumps(ptd_deliveries, ensure_ascii=False)};\n")
    f.write(f"const PTD_RISKS = {json.dumps(ptd_risks, ensure_ascii=False)};\n")
    f.write(f"const PTD_DATES = {json.dumps(ptd_dates, ensure_ascii=False)};\n")
    f.write(f"const PTD_TIMELINE = {json.dumps(ptd_timeline, ensure_ascii=False)};\n")
    f.write(f"const PTD_TIMELINE_ORGANS = {json.dumps(ptd_timeline_organs, ensure_ascii=False)};\n")
    f.write(f"const PTD_JACCARD_ORGANS = {json.dumps(jaccard_organs, ensure_ascii=False)};\n")
    f.write(f"const PTD_JACCARD_MATRIX = {json.dumps(jaccard_matrix)};\n")
print(f"data.js gravado ({os.path.getsize(js_path) / 1024:.0f} KB)")

# --- statistics_summary.json ---
stats_path = os.path.join(out_dir, "statistics_summary.json")
with open(stats_path, "w", encoding="utf-8") as f:
    json.dump(ptd_stats, f, ensure_ascii=False, indent=2)
print(f"statistics_summary.json gravado")

# --- coverage_summary.csv ---
cov_path = os.path.join(out_dir, "coverage_summary.csv")
cov_rows = []
for o in ptd_organs:
    cov_rows.append({
        "sigla": o["sigla"],
        "grupo": o["grupo"],
        "pdf_diretivo": "sim" if o["pdf_diretivo"] else "nao",
        "pdf_entregas": "sim" if o["pdf_entregas"] else "nao",
        "entregas_extraidas": o["n_entregas"],
        "riscos_extraidos": o["n_riscos"],
        "status_entregas": o["status_entregas"],
        "status_riscos": o["status_riscos"],
    })
pd.DataFrame(cov_rows).to_csv(cov_path, index=False, encoding="utf-8-sig")
print(f"coverage_summary.csv gravado ({len(cov_rows)} órgãos)")

# --- pdf_metadata.csv ---
if pdf_meta_rows:
    meta_path = os.path.join(out_dir, "pdf_metadata.csv")
    pd.DataFrame(pdf_meta_rows).to_csv(meta_path, index=False, encoding="utf-8-sig")
    print(f"pdf_metadata.csv gravado ({len(pdf_meta_rows)} PDFs)")
else:
    print("pdf_metadata.csv: nenhum PDF local encontrado (pular)")

print("\nArtefatos do dashboard gerados com sucesso.")
