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
    plt.savefig(os.path.join(fig_dir, "01_entregas_por_eixo.png"), dpi=150, bbox_inches="tight")
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
        plt.savefig(os.path.join(fig_dir, "04_matriz_riscos.png"), dpi=150, bbox_inches="tight")
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
    plt.savefig(os.path.join(fig_dir, "02_top20_produtos.png"), dpi=150, bbox_inches="tight")
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
        plt.savefig(os.path.join(fig_dir, "05_distribuicao_tipos.png"), dpi=150, bbox_inches="tight")
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
    plt.savefig(os.path.join(fig_dir, "03_top30_orgaos_entregas.png"), dpi=150, bbox_inches="tight")
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
        plt.savefig(os.path.join(fig_dir, "06_tratamento_riscos.png"), dpi=150, bbox_inches="tight")
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
