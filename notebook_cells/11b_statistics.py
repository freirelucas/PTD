# ============================================================
# CÉLULA 11 — Análises Estatísticas e Visualizações
# ============================================================
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11
sns.set_style("whitegrid")

fig_dir = os.path.join(DIRS["output"], "figures")
os.makedirs(fig_dir, exist_ok=True)


def _save_fig(name):
    """Salva a figura corrente em SVG (vetor, fontes do sistema). A NT do
    corpus padroniza figuras em SVG — todas as figuras deste cell usam este
    helper para manter o formato consistente."""
    plt.savefig(os.path.join(fig_dir, name + ".svg"), bbox_inches="tight")

# Build DataFrames for analysis (reuse if already created in export cell)
if all_deliveries:
    df_del = pd.DataFrame([asdict(e) for e in all_deliveries])
else:
    df_del = pd.DataFrame()

if all_risks:
    df_risk = pd.DataFrame([asdict(e) for e in all_risks])
else:
    df_risk = pd.DataFrame()

if all_organs:
    df_org = pd.DataFrame([asdict(o) for o in all_organs])
else:
    df_org = pd.DataFrame()


# =========================================================
# 1. Coverage Summary (text)
# =========================================================
print("=" * 60)
print("RESUMO DE COBERTURA")
print("=" * 60)

n_total_organs = len(all_organs)
n_with_diretivo = sum(1 for o in all_organs if o.pdf_path_diretivo) if all_organs else 0
n_with_entregas = sum(1 for o in all_organs if o.pdf_path_entregas) if all_organs else 0
n_with_both = sum(1 for o in all_organs if o.pdf_path_diretivo and o.pdf_path_entregas) if all_organs else 0
n_risks = len(all_risks)
n_deliveries = len(all_deliveries)

# Organs that produced data (have at least one risk or delivery)
organs_with_risks = set(r.orgao_sigla for r in all_risks) if all_risks else set()
organs_with_deliveries = set(d.orgao_sigla for d in all_deliveries) if all_deliveries else set()
organs_with_data = organs_with_risks | organs_with_deliveries

print(f"  Total de órgãos:               {n_total_organs}")
print(f"  Com PDF diretivo:              {n_with_diretivo}")
print(f"  Com PDF entregas:              {n_with_entregas}")
print(f"  Com ambos PDFs:                {n_with_both}")
print(f"  Órgãos com riscos extraídos:   {len(organs_with_risks)}")
print(f"  Órgãos com entregas extraídas: {len(organs_with_deliveries)}")
print(f"  Órgãos com algum dado:         {len(organs_with_data)}")
print(f"")
print(f"  Total de riscos extraídos:     {n_risks}")
print(f"  Total de entregas extraídas:   {n_deliveries}")

if n_total_organs > 0:
    risk_rate = len(organs_with_risks) / n_total_organs * 100
    del_rate = len(organs_with_deliveries) / n_total_organs * 100
    print(f"")
    print(f"  Taxa de extração de riscos:    {risk_rate:.1f}% dos órgãos")
    print(f"  Taxa de extração de entregas:  {del_rate:.1f}% dos órgãos")
print(f"  Erros de processamento:        {len(all_errors)}")
print("=" * 60)


# =========================================================
# 2. Bar Chart: Deliveries by Eixo (horizontal, sorted)
# =========================================================
if not df_del.empty and "eixo_normalizado" in df_del.columns:
    eixo_counts = df_del["eixo_normalizado"].value_counts().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(4, len(eixo_counts) * 0.5)))
    bars = ax.barh(eixo_counts.index, eixo_counts.values, color=sns.color_palette("viridis", len(eixo_counts)))
    ax.set_xlabel("Número de Entregas")
    ax.set_title("Entregas por Eixo Estratégico")
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    _save_fig("01_entregas_por_eixo")
    plt.show()
else:
    print("Sem dados de entregas para gráfico de eixos.")


# =========================================================
# 3. Heatmap: Probabilidade x Impacto (risk matrix)
# =========================================================
if not df_risk.empty and "probabilidade_normalizada" in df_risk.columns and "impacto_normalizado" in df_risk.columns:
    # Filter to canonical values only for a clean matrix
    df_risk_clean = df_risk[
        df_risk["probabilidade_normalizada"].isin(PROBABILIDADE_SCALE) &
        df_risk["impacto_normalizado"].isin(IMPACTO_SCALE)
    ].copy()

    if not df_risk_clean.empty:
        pivot = df_risk_clean.groupby(
            ["probabilidade_normalizada", "impacto_normalizado"]
        ).size().unstack(fill_value=0)

        # Reindex to canonical order
        pivot = pivot.reindex(index=PROBABILIDADE_SCALE, columns=IMPACTO_SCALE, fill_value=0)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(
            pivot, annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.5, ax=ax,
            xticklabels=IMPACTO_SCALE,
            yticklabels=PROBABILIDADE_SCALE,
        )
        ax.set_xlabel("Impacto")
        ax.set_ylabel("Probabilidade")
        ax.set_title("Matriz de Riscos: Probabilidade × Impacto")
        plt.tight_layout()
        _save_fig("04_matriz_riscos")
        plt.show()
    else:
        print("Sem riscos com valores canônicos de probabilidade/impacto para heatmap.")
else:
    print("Sem dados de riscos para heatmap.")


# =========================================================
# 4. Top 20 Produtos (horizontal bar chart)
# =========================================================
if not df_del.empty and "produto_normalizado" in df_del.columns:
    prod_counts = df_del["produto_normalizado"].value_counts().head(20).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(5, len(prod_counts) * 0.35)))
    bars = ax.barh(prod_counts.index, prod_counts.values, color=sns.color_palette("mako", len(prod_counts)))
    ax.set_xlabel("Número de Entregas")
    ax.set_title("Top 20 Produtos Mais Frequentes")
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    _save_fig("02_top20_produtos")
    plt.show()
else:
    print("Sem dados de entregas para gráfico de produtos.")


# =========================================================
# 5. Deliveries by Type (pie chart)
# =========================================================
if not df_del.empty and "tabela_tipo" in df_del.columns:
    tipo_counts = df_del["tabela_tipo"].value_counts()

    if not tipo_counts.empty:
        colors = {"pactuada": "#4CAF50", "concluida": "#2196F3", "cancelada": "#F44336"}
        pie_colors = [colors.get(t, "#9E9E9E") for t in tipo_counts.index]

        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            tipo_counts.values,
            labels=tipo_counts.index,
            autopct=lambda pct: f"{pct:.1f}%\n({int(pct/100.*tipo_counts.sum())})",
            colors=pie_colors,
            startangle=90,
            textprops={"fontsize": 12},
        )
        ax.set_title("Distribuição de Entregas por Tipo")
        plt.tight_layout()
        _save_fig("05_distribuicao_tipos")
        plt.show()
    else:
        print("Sem dados de tipo de tabela para gráfico de pizza.")
else:
    print("Sem dados de entregas para gráfico de tipos.")


# =========================================================
# 6. Deliveries per Organ (horizontal bar, top 30)
# =========================================================
if not df_del.empty and "orgao_sigla" in df_del.columns:
    org_counts = df_del["orgao_sigla"].value_counts().head(30).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(6, len(org_counts) * 0.3)))
    bars = ax.barh(org_counts.index, org_counts.values, color=sns.color_palette("crest", len(org_counts)))
    ax.set_xlabel("Número de Entregas")
    ax.set_title("Top 30 Órgãos por Número de Entregas")
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    _save_fig("03_top30_orgaos_entregas")
    plt.show()
else:
    print("Sem dados de entregas para gráfico por órgão.")


# =========================================================
# 7. Treatment Options Distribution (bar chart)
# =========================================================
if not df_risk.empty and "tratamento_normalizado" in df_risk.columns:
    # Tratamentos podem ter múltiplos valores separados por ";"
    all_treatments = []
    for val in df_risk["tratamento_normalizado"].dropna():
        parts = [p.strip() for p in str(val).split(";") if p.strip()]
        all_treatments.extend(parts)

    if all_treatments:
        trat_counts = pd.Series(all_treatments).value_counts()

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(trat_counts.index, trat_counts.values, color=sns.color_palette("Set2", len(trat_counts)))
        ax.set_xlabel("Tipo de Tratamento")
        ax.set_ylabel("Frequência")
        ax.set_title("Distribuição das Opções de Tratamento de Riscos")
        ax.bar_label(bars, padding=3)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        _save_fig("06_tratamento_riscos")
        plt.show()
    else:
        print("Sem dados de tratamento para gráfico.")
else:
    print("Sem dados de riscos para gráfico de tratamentos.")


# =========================================================
# 8. Data Quality Dashboard (text)
# =========================================================
print("\n" + "=" * 60)
print("DASHBOARD DE QUALIDADE DOS DADOS")
print("=" * 60)

# --- Missing/empty field rates ---
print("\n--- Campos com maiores taxas de ausência ---")

if not df_del.empty:
    print("\n  ENTREGAS:")
    for col in df_del.columns:
        n_missing = df_del[col].isna().sum() + (df_del[col] == "").sum()
        pct = n_missing / len(df_del) * 100
        if pct > 0:
            print(f"    {col:<30s} {n_missing:>5d} ausentes ({pct:.1f}%)")

if not df_risk.empty:
    print("\n  RISCOS:")
    for col in df_risk.columns:
        n_missing = df_risk[col].isna().sum() + (df_risk[col] == "").sum()
        pct = n_missing / len(df_risk) * 100
        if pct > 0:
            print(f"    {col:<30s} {n_missing:>5d} ausentes ({pct:.1f}%)")

# --- Confidence distribution ---
print("\n--- Distribuição de confiança ---")

if not df_del.empty and "extraction_confidence" in df_del.columns:
    del_conf = df_del["extraction_confidence"].value_counts()
    print("\n  ENTREGAS:")
    for level in ["high", "medium", "low"]:
        count = del_conf.get(level, 0)
        pct = count / len(df_del) * 100
        bar = "█" * int(pct / 2)
        print(f"    {level:<8s} {count:>5d} ({pct:>5.1f}%) {bar}")

if not df_risk.empty and "extraction_confidence" in df_risk.columns:
    risk_conf = df_risk["extraction_confidence"].value_counts()
    print("\n  RISCOS:")
    for level in ["high", "medium", "low"]:
        count = risk_conf.get(level, 0)
        pct = count / len(df_risk) * 100
        bar = "█" * int(pct / 2)
        print(f"    {level:<8s} {count:>5d} ({pct:>5.1f}%) {bar}")

# --- Items needing review ---
n_review_del = df_del["needs_review"].sum() if not df_del.empty and "needs_review" in df_del.columns else 0
n_review_risk = df_risk["needs_review"].sum() if not df_risk.empty and "needs_review" in df_risk.columns else 0

print(f"\n--- Itens pendentes de revisão ---")
print(f"  Entregas: {int(n_review_del)}")
print(f"  Riscos:   {int(n_review_risk)}")
print(f"  Total:    {int(n_review_del + n_review_risk)}")
print("=" * 60)

# --- Asserções de regressão ---
# Falham rápido com mensagem que aponta para causa provável (cache stale,
# dedup pulado, novo formato de PDF). Thresholds em QUALITY_THRESHOLDS
# (notebook_cells/02_config.py) — bumpar se o corpus crescer legitimamente.
print("\n--- Verificação de invariantes ---")

_n_del = len(all_deliveries)
_n_risk = len(all_risks)
_max_del = QUALITY_THRESHOLDS["max_entregas"]
_max_risk = QUALITY_THRESHOLDS["max_riscos"]
assert _n_del <= _max_del, (
    f"Regressão: {_n_del} entregas excede threshold {_max_del}. "
    f"Provável dedup MD5 pulado — limpar checkpoints/*_raw.pkl e re-executar a partir de 05c."
)
assert _n_risk <= _max_risk, (
    f"Regressão: {_n_risk} riscos excede threshold {_max_risk}. "
    f"Provável dedup MD5 pulado — limpar checkpoints/*_raw.pkl e re-executar a partir de 05c."
)

if all_risks:
    _n_prob_ok = sum(1 for r in all_risks if r.probabilidade_normalizada in PROBABILIDADE_SCALE)
    _n_imp_ok = sum(1 for r in all_risks if r.impacto_normalizado in IMPACTO_SCALE)
    _n_trat_ok = sum(1 for r in all_risks
                     if r.tratamento_normalizado
                     and all(t.strip() in TRATAMENTO_OPTIONS
                             for t in r.tratamento_normalizado.split(";") if t.strip()))

    _r_prob = _n_prob_ok / _n_risk
    _r_imp = _n_imp_ok / _n_risk
    _r_trat = _n_trat_ok / _n_risk

    print(f"  Canonização probabilidade: {_r_prob:.1%} (mín {QUALITY_THRESHOLDS['min_prob_canonica_ratio']:.0%})")
    print(f"  Canonização impacto:       {_r_imp:.1%} (mín {QUALITY_THRESHOLDS['min_imp_canonica_ratio']:.0%})")
    print(f"  Canonização tratamento:    {_r_trat:.1%} (mín {QUALITY_THRESHOLDS['min_trat_canonica_ratio']:.0%})")

    assert _r_prob >= QUALITY_THRESHOLDS["min_prob_canonica_ratio"], (
        f"Regressão: probabilidade canônica em {_r_prob:.1%} — "
        f"verificar PROBABILIDADE_ALIASES e novos formatos de escala."
    )
    assert _r_imp >= QUALITY_THRESHOLDS["min_imp_canonica_ratio"], (
        f"Regressão: impacto canônico em {_r_imp:.1%} — "
        f"verificar IMPACTO_ALIASES."
    )
    assert _r_trat >= QUALITY_THRESHOLDS["min_trat_canonica_ratio"], (
        f"Regressão: tratamento canônico em {_r_trat:.1%} — "
        f"verificar TRATAMENTO_ALIASES."
    )

print("  Invariantes OK.")

# --- Residuais não-canônicos (auditoria por ciclo) -------------
# Lista valores brutos que escaparam dos aliases para guiar a próxima
# rodada de melhorias. Útil ao adicionar aliases (Camada 1.5) ou
# investigar bugs de extração tabular (Categoria A: column-shift,
# header capturado, fragmentação por quebra de linha).
if all_risks:
    from collections import Counter
    _nc_prob = Counter(r.probabilidade_original for r in all_risks
                       if r.probabilidade_normalizada not in PROBABILIDADE_SCALE
                       and r.probabilidade_original)
    _nc_imp = Counter(r.impacto_original for r in all_risks
                      if r.impacto_normalizado not in IMPACTO_SCALE
                      and r.impacto_original)
    _nc_trat = Counter(r.tratamento_original for r in all_risks
                       if r.tratamento_normalizado
                       and not all(t.strip() in TRATAMENTO_OPTIONS
                                   for t in r.tratamento_normalizado.split(";")
                                   if t.strip())
                       and r.tratamento_original)

    if _nc_prob or _nc_imp or _nc_trat:
        print("\n--- Residuais não-canônicos (top 10 por campo) ---")
        for label, ctr in [("probabilidade", _nc_prob),
                           ("impacto", _nc_imp),
                           ("tratamento", _nc_trat)]:
            if ctr:
                print(f"\n  {label.upper()}:")
                for val, cnt in ctr.most_common(10):
                    print(f"    {cnt:3d}× {val!r}")
        print("\n  Use esta lista para alimentar aliases em 02_config.py")
        print("  ou identificar casos de extração tabular (Categoria A).")
    else:
        print("\n  Sem residuais não-canônicos — corpus 100% mapeado.")


# =========================================================
# 9. Risco de exclusão digital (orientação + subtipo — célula 09c)
# =========================================================
# Sub-análise distributiva: a matriz de risco do PTD é endógena ao Estado
# (fornecedor/equipe/orçamento). Esta seção isola o risco de EXCLUSÃO do
# cidadão e mede a (in)coerência com que o mesmo risco-template é avaliado.
import re as _re_excl
import difflib as _difflib_excl

if not df_risk.empty and "subtipo_exclusao" in df_risk.columns:
    print("\n" + "=" * 60)
    print("RISCO DE EXCLUSÃO DIGITAL (orientação distributiva)")
    print("=" * 60)

    # --- Saída 1: contagem por orientacao_risco (esperado: estado ≫ cidadao) ---
    _orient = df_risk["orientacao_risco"].value_counts()
    print("\n--- (1) Riscos por orientação ---")
    for _k in ["estado", "cidadao", "ambos", "indefinido"]:
        _v = int(_orient.get(_k, 0))
        print(f"    {_k:<12s} {_v:>4d} ({_v / len(df_risk) * 100:>4.1f}%)")
    _est, _cid = int(_orient.get("estado", 0)), int(_orient.get("cidadao", 0))
    print(f"    → estado/cidadao = {(_est / _cid):.1f}×" if _cid else "    → sem cidadao")

    # --- Saída 2: contagem por subtipo_exclusao ---
    _subt = df_risk["subtipo_exclusao"].value_counts()
    print("\n--- (2) Riscos por subtipo de exclusão ---")
    for _k in ["digital_only", "acessibilidade", "disponibilidade_uptime", "nenhum"]:
        _v = int(_subt.get(_k, 0))
        print(f"    {_k:<24s} {_v:>4d}")
    print("    (disponibilidade_uptime é o FALSO-AMIGO: uptime técnico, não exclusão)")

    # --- Saída 3: tabela dos órgãos com exclusão real (digital_only|acessibilidade) ---
    _excl = df_risk[df_risk["subtipo_exclusao"].isin(["digital_only", "acessibilidade"])]
    print(f"\n--- (3) Órgãos com risco de exclusão: "
          f"{len(_excl)} riscos em {_excl['orgao_sigla'].nunique()} órgãos ---")
    print(f"    {'SIGLA':<10}{'SUBTIPO':<15}{'PROB':<12}{'IMPACTO':<12}{'TRAT':<10}TEXTO")
    for _, _r in _excl.sort_values(["orgao_sigla"]).iterrows():
        _txt = (_r["risco_texto"] or "")[:48].replace("\n", " ")
        print(f"    {_r['orgao_sigla']:<10}{_r['subtipo_exclusao']:<15}"
              f"{(_r['probabilidade_normalizada'] or '-'):<12}"
              f"{(_r['impacto_normalizado'] or '-'):<12}"
              f"{(_r['tratamento_normalizado'] or '-'):<10}{_txt}")

    # --- Saída 4: ÍNDICE DE INCOERÊNCIA do template "digital only" ---
    # Agrupa os riscos digital_only por texto quase-idêntico (fuzzy ≥0,90) e
    # reporta, por cluster com ≥2 órgãos, o leque de impacto e de tratamento
    # atribuídos ao MESMO risco. É o número-chave da nota técnica.
    def _norm_excl(t):
        return _re_excl.sub(r"\s+", " ", str(t or "").strip().lower())

    _dig = df_risk[df_risk["subtipo_exclusao"] == "digital_only"].to_dict("records")
    _clusters = []
    for _row in _dig:
        _nt = _norm_excl(_row["risco_texto"])
        for _cl in _clusters:
            if _difflib_excl.SequenceMatcher(None, _nt, _cl["rep"]).ratio() >= 0.90:
                _cl["rows"].append(_row)
                break
        else:
            _clusters.append({"rep": _nt, "rows": [_row]})

    print("\n--- (4) Índice de incoerência (mesmo risco-template, avaliações divergentes) ---")
    for _cl in sorted(_clusters, key=lambda c: -len(c["rows"])):
        _orgs = sorted({x["orgao_sigla"] for x in _cl["rows"]})
        if len(_orgs) < 2:
            continue
        _imp = [x["impacto_normalizado"] for x in _cl["rows"]
                if x["impacto_normalizado"] in IMPACTO_SCALE]
        _trat = sorted({x["tratamento_normalizado"] for x in _cl["rows"]
                        if x["tratamento_normalizado"]})
        _imp_ord = sorted(set(_imp), key=lambda v: IMPACTO_SCALE.index(v))
        print(f"    template em {len(_orgs)} órgãos ({', '.join(_orgs)}):")
        print(f"      texto: \"{_cl['rows'][0]['risco_texto'][:70]}...\"")
        print(f"      IMPACTO varia: {' → '.join(_imp_ord) or '(sem canônico)'}")
        print(f"      TRATAMENTO varia: {', '.join(_trat) or '(vazio)'}")
        for _x in sorted(_cl["rows"], key=lambda r: r["orgao_sigla"]):
            print(f"        {_x['orgao_sigla']:<10} impacto={_x['impacto_normalizado'] or '-':<12}"
                  f" tratamento={_x['tratamento_normalizado'] or '-'}")

    # --- Figura 08: orientação do risco (barras horizontais) ---
    _ord_orient = ["estado", "ambos", "cidadao", "indefinido"]
    _vals = [int(_orient.get(k, 0)) for k in _ord_orient]
    _pal = {"estado": "#34495E", "ambos": "#95A5A6", "cidadao": "#C0392B", "indefinido": "#D5DBDB"}
    fig, ax = plt.subplots(figsize=(9, 4))
    _bars = ax.barh(_ord_orient[::-1], _vals[::-1],
                    color=[_pal[k] for k in _ord_orient[::-1]])
    ax.set_xlabel("Número de riscos")
    ax.set_title("Orientação do risco: a matriz do PTD é endógena ao Estado")
    ax.bar_label(_bars, padding=3)
    ax.margins(x=0.12)
    plt.tight_layout()
    _save_fig("08_orientacao_risco")
    plt.show()

    # --- Figura 09: incoerência do risco "digital only" (dot plot) ---
    _dig_clean = [x for x in _dig if x["impacto_normalizado"] in IMPACTO_SCALE]
    if _dig_clean:
        _trat_colors = {"mitigar": "#27AE60", "aceitar": "#C0392B",
                        "transferir": "#E67E22", "eliminar": "#2980B9"}
        fig, ax = plt.subplots(figsize=(9, max(3, len(_dig_clean) * 0.5)))
        _dig_sorted = sorted(_dig_clean,
                             key=lambda r: IMPACTO_SCALE.index(r["impacto_normalizado"]))
        _ylabels = []
        for _i, _x in enumerate(_dig_sorted):
            _xi = IMPACTO_SCALE.index(_x["impacto_normalizado"])
            _t0 = (_x["tratamento_normalizado"] or "").split(";")[0].strip()
            ax.scatter(_xi, _i, s=220, zorder=3,
                       color=_trat_colors.get(_t0, "#7F8C8D"),
                       edgecolor="white", linewidth=1.5)
            _ylabels.append(_x["orgao_sigla"])
        ax.set_yticks(range(len(_dig_sorted)))
        ax.set_yticklabels(_ylabels)
        ax.set_xticks(range(len(IMPACTO_SCALE)))
        ax.set_xticklabels(IMPACTO_SCALE, rotation=20, ha="right")
        ax.set_xlim(-0.5, len(IMPACTO_SCALE) - 0.5)
        ax.set_xlabel("Impacto atribuído (escala ordinal SGD)")
        ax.set_title('Mesmo risco "digital only", severidade e tratamento divergentes')
        _handles = [plt.Line2D([0], [0], marker="o", linestyle="", markersize=10,
                               markerfacecolor=_c, markeredgecolor="white", label=_t)
                    for _t, _c in _trat_colors.items()]
        ax.legend(handles=_handles, title="Tratamento", loc="lower right", framealpha=0.9)
        ax.grid(axis="x", linestyle=":", alpha=0.5)
        plt.tight_layout()
        _save_fig("09_incoerencia_digital_only")
        plt.show()
    print("=" * 60)
