# ============================================================
# CÉLULA 12 — Suporte a Iterações e Correções Manuais
# ============================================================
from datetime import datetime
from dataclasses import asdict


def generate_review_queue() -> pd.DataFrame:
    """
    Coleta todos os itens que necessitam revisão manual (riscos, entregas, erros).

    Prioridades (menor número = maior prioridade):
      1 — extraction_failed (erros de processamento)
      2 — low_confidence
      3 — vocabulary_mismatch / unmatched
      4 — medium_confidence / fuzzy match
    """
    rows = []

    # --- Deliveries needing review ---
    for entry in all_deliveries:
        if not entry.needs_review:
            continue

        reason = (entry.review_reason or "").lower()
        if "não reconhecido" in reason or "unmatched" in reason:
            priority = 2 if entry.extraction_confidence == "low" else 3
        elif "fuzzy" in reason:
            priority = 4
        elif "cross-validation" in reason or "corrigido" in reason:
            priority = 3
        else:
            priority = 4

        rows.append({
            "priority": priority,
            "orgao": entry.orgao_sigla,
            "type": "delivery",
            "issue": entry.review_reason or "needs review",
            "original_value": entry.produto_original,
            "current_value": entry.produto_normalizado,
            "confidence": entry.extraction_confidence,
        })

    # --- Risks needing review ---
    for entry in all_risks:
        if not entry.needs_review:
            continue

        reason = (entry.review_reason or "").lower()
        if "não reconhecid" in reason:
            priority = 2 if entry.extraction_confidence == "low" else 3
        elif "fuzzy" in reason:
            priority = 4
        else:
            priority = 4

        rows.append({
            "priority": priority,
            "orgao": entry.orgao_sigla,
            "type": "risk",
            "issue": entry.review_reason or "needs review",
            "original_value": (
                f"P:{entry.probabilidade_original} | "
                f"I:{entry.impacto_original} | "
                f"T:{entry.tratamento_original}"
            ),
            "current_value": (
                f"P:{entry.probabilidade_normalizada} | "
                f"I:{entry.impacto_normalizado} | "
                f"T:{entry.tratamento_normalizado}"
            ),
            "confidence": entry.extraction_confidence,
        })

    # --- Processing errors ---
    for err in all_errors:
        rows.append({
            "priority": 1,
            "orgao": err.orgao_sigla,
            "type": f"error ({err.document_type})",
            "issue": f"[{err.stage}] {err.error_type}: {err.error_message}",
            "original_value": err.url or "",
            "current_value": "",
            "confidence": "failed",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["priority", "orgao", "type"]).reset_index(drop=True)

    return df


def apply_corrections(corrections_path: str) -> Tuple[int, int]:
    """
    Aplica correções manuais a partir de um CSV.

    Formato do CSV:
      orgao_sigla, entry_type (risk/delivery), field_name, original_value, corrected_value

    Retorna (corrections_applied, corrections_failed).
    """
    if not os.path.exists(corrections_path):
        print(f"Arquivo de correções não encontrado: {corrections_path}")
        return (0, 0)

    df_corr = pd.read_csv(corrections_path, encoding="utf-8-sig")
    required_cols = {"orgao_sigla", "entry_type", "field_name", "original_value", "corrected_value"}
    if not required_cols.issubset(set(df_corr.columns)):
        missing = required_cols - set(df_corr.columns)
        print(f"Colunas faltando no CSV de correções: {missing}")
        return (0, 0)

    applied = 0
    failed = 0

    for _, row in df_corr.iterrows():
        sigla = str(row["orgao_sigla"]).strip()
        entry_type = str(row["entry_type"]).strip().lower()
        field = str(row["field_name"]).strip()
        orig_val = str(row["original_value"]).strip()
        new_val = str(row["corrected_value"]).strip()

        matched = False

        if entry_type == "delivery":
            for entry in all_deliveries:
                if entry.orgao_sigla != sigla:
                    continue
                current = str(getattr(entry, field, None) or "").strip()
                if current == orig_val or (not orig_val and not current):
                    try:
                        setattr(entry, field, new_val)
                        entry.needs_review = False
                        entry.review_reason = f"corrigido manualmente em {datetime.now().isoformat()}"
                        applied += 1
                        matched = True
                    except AttributeError:
                        failed += 1
                    break

        elif entry_type == "risk":
            for entry in all_risks:
                if entry.orgao_sigla != sigla:
                    continue
                current = str(getattr(entry, field, None) or "").strip()
                if current == orig_val or (not orig_val and not current):
                    try:
                        setattr(entry, field, new_val)
                        entry.needs_review = False
                        entry.review_reason = f"corrigido manualmente em {datetime.now().isoformat()}"
                        applied += 1
                        matched = True
                    except AttributeError:
                        failed += 1
                    break

        if not matched:
            failed += 1
            logger.warning(
                f"Correção não aplicada: {sigla}/{entry_type}/{field} "
                f"(valor original '{orig_val}' não encontrado)"
            )

    print(f"Correções aplicadas: {applied}, falhas: {failed}")
    return (applied, failed)


# ---- Gerar fila de revisão ----
print("=" * 60)
print("FILA DE REVISÃO")
print("=" * 60)

review_queue = generate_review_queue()

if not review_queue.empty:
    print(f"\nTotal de itens para revisão: {len(review_queue)}")

    # Breakdown by issue priority
    print("\n--- Por prioridade ---")
    priority_labels = {1: "extraction_failed", 2: "low_confidence", 3: "vocabulary_mismatch", 4: "medium_confidence"}
    for p in sorted(review_queue["priority"].unique()):
        count = (review_queue["priority"] == p).sum()
        label = priority_labels.get(p, f"priority_{p}")
        print(f"  {p}. {label:<25s} {count:>5d}")

    # Breakdown by type
    print("\n--- Por tipo ---")
    for t, count in review_queue["type"].value_counts().items():
        print(f"  {t:<25s} {count:>5d}")

    # Top 10 organs with most review items
    print("\n--- Top 10 órgãos com mais itens para revisão ---")
    top_organs = review_queue["orgao"].value_counts().head(10)
    for org, count in top_organs.items():
        print(f"  {org:<15s} {count:>5d}")

    # Save review queue
    rq_path = os.path.join(DIRS["output"], "review_queue_prioritized.csv")
    review_queue.to_csv(rq_path, index=False, encoding="utf-8-sig")
    print(f"\nFila de revisão salva: {rq_path}")
else:
    print("\nNenhum item pendente de revisão. Todos os dados estão validados.")

# ---- Instructions for corrections ----
print("\n" + "-" * 60)
print("INSTRUÇÕES PARA CORREÇÕES MANUAIS")
print("-" * 60)
print("""
Para aplicar correções no próximo ciclo:

1. Crie um arquivo CSV com as seguintes colunas:
   orgao_sigla, entry_type, field_name, original_value, corrected_value

   Exemplo:
   orgao_sigla,entry_type,field_name,original_value,corrected_value
   MEC,delivery,produto_normalizado,UNMATCHED,Evolução do Serviço
   ANATEL,risk,probabilidade_normalizada,provavel,provável

2. Salve o arquivo em: {output_dir}/corrections.csv

3. Execute: apply_corrections("{output_dir}/corrections.csv")
""".format(output_dir=DIRS["output"]))


# =========================================================
# RESUMO FINAL DO PIPELINE
# =========================================================
print("\n" + "=" * 60)
print("RESUMO FINAL DO PIPELINE")
print("=" * 60)

n_organs = len(all_organs)
n_pdfs = sum(1 for o in all_organs if o.pdf_path_diretivo) + sum(1 for o in all_organs if o.pdf_path_entregas)
n_risks_total = len(all_risks)
n_del_total = len(all_deliveries)
n_errors = len(all_errors)

# Data quality score: % of entries with high confidence
high_conf_del = sum(1 for d in all_deliveries if d.extraction_confidence == "high")
high_conf_risk = sum(1 for r in all_risks if r.extraction_confidence == "high")
total_entries = n_risks_total + n_del_total
quality_score = ((high_conf_del + high_conf_risk) / total_entries * 100) if total_entries > 0 else 0.0

# Items needing review
n_review = len(review_queue) if not review_queue.empty else 0
n_review_organs = review_queue["orgao"].nunique() if not review_queue.empty else 0

# Exported files
output_dir = DIRS["output"]
exported_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))] if os.path.isdir(output_dir) else []

print(f"""
  Órgãos processados:           {n_organs}
  PDFs baixados:                {n_pdfs}
  Riscos extraídos:             {n_risks_total}
  Entregas extraídas:           {n_del_total}
  Erros de processamento:       {n_errors}

  Qualidade dos dados:          {quality_score:.1f}% com alta confiança
    - Entregas alta confiança:  {high_conf_del}/{n_del_total}
    - Riscos alta confiança:    {high_conf_risk}/{n_risks_total}

  Arquivos exportados:          {len(exported_files)}
  Diretório de saída:           {output_dir}

  Iteração: {n_review} itens necessitam revisão manual em {n_review_organs} órgãos
""")
print("=" * 60)
print("Pipeline concluído com sucesso.")
print("=" * 60)
