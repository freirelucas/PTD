# ============================================================
# CÉLULA 10 — Exportação de Dados
# ============================================================
from datetime import datetime
from dataclasses import asdict


def _file_size_str(path: str) -> str:
    """Retorna tamanho do arquivo em formato legível."""
    size = os.path.getsize(path)
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _build_nested_json(entries: list, key_field: str, metadata_extra: dict = None) -> dict:
    """Agrupa entradas por key_field em um JSON com metadata."""
    grouped = {}
    for entry in entries:
        d = asdict(entry)
        key = d.get(key_field, "UNKNOWN")
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(d)

    metadata = {
        "exported_at": datetime.now().isoformat(),
        "total": len(entries),
        "groups": len(grouped),
    }
    if metadata_extra:
        metadata.update(metadata_extra)

    return {"metadata": metadata, "data": grouped}


export_log = []  # (filename, rows, size_str)

# ---- 1. Entregas: CSV e JSON ----
if all_deliveries:
    df_del = pd.DataFrame([asdict(e) for e in all_deliveries])

    csv_path = os.path.join(DIRS["output"], "deliveries.csv")
    df_del.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("deliveries.csv", len(df_del), _file_size_str(csv_path)))

    json_path = os.path.join(DIRS["output"], "deliveries.json")
    nested = _build_nested_json(all_deliveries, "orgao_sigla")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)
    export_log.append(("deliveries.json", len(all_deliveries), _file_size_str(json_path)))
else:
    print("Nenhuma entrega para exportar.")

# ---- 2. Riscos: CSV e JSON ----
if all_risks:
    df_risk = pd.DataFrame([asdict(e) for e in all_risks])

    csv_path = os.path.join(DIRS["output"], "risks.csv")
    df_risk.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("risks.csv", len(df_risk), _file_size_str(csv_path)))

    json_path = os.path.join(DIRS["output"], "risks.json")
    nested = _build_nested_json(all_risks, "orgao_sigla")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)
    export_log.append(("risks.json", len(all_risks), _file_size_str(json_path)))
else:
    print("Nenhum risco para exportar.")

# ---- 3. Órgãos: CSV ----
if all_organs:
    df_org = pd.DataFrame([asdict(o) for o in all_organs])

    csv_path = os.path.join(DIRS["output"], "organs.csv")
    df_org.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("organs.csv", len(df_org), _file_size_str(csv_path)))
else:
    print("Nenhum órgão para exportar.")

# ---- 4. Relatório de erros: CSV ----
if all_errors:
    df_err = pd.DataFrame([asdict(e) for e in all_errors])

    csv_path = os.path.join(DIRS["output"], "error_report.csv")
    df_err.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("error_report.csv", len(df_err), _file_size_str(csv_path)))
else:
    print("Nenhum erro registrado para exportar.")

# ---- 5. Mapeamento de vocabulário: CSV ----
vocab_rows = []

# Produto mappings
for m in vocab_report.get("produto_mappings", []):
    vocab_rows.append({
        "type": "produto",
        "original": m["original"],
        "normalized": m["normalized"],
        "score": m["score"],
        "count": m["count"],
    })

# Eixo mappings
for m in vocab_report.get("eixo_mappings", []):
    vocab_rows.append({
        "type": "eixo",
        "original": m["original"],
        "normalized": m["normalized"],
        "score": m["score"],
        "count": m["count"],
    })

# Risk field mappings
for field_key in ["probabilidade_mappings", "impacto_mappings", "tratamento_mappings"]:
    field_type = field_key.replace("_mappings", "")
    for m in risk_report.get(field_key, []):
        vocab_rows.append({
            "type": field_type,
            "original": m["original"],
            "normalized": m["normalized"],
            "score": m["score"],
            "count": m["count"],
        })

if vocab_rows:
    df_vocab = pd.DataFrame(vocab_rows)
    csv_path = os.path.join(DIRS["output"], "vocabulary_mapping.csv")
    df_vocab.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("vocabulary_mapping.csv", len(df_vocab), _file_size_str(csv_path)))
else:
    print("Nenhum mapeamento de vocabulário para exportar.")

# ---- 6. Fila de revisão: CSV ----
review_rows = []

for entry in all_deliveries:
    if entry.needs_review:
        review_rows.append({
            "orgao_sigla": entry.orgao_sigla,
            "entry_type": "delivery",
            "field": "produto / eixo",
            "original_value": entry.produto_original,
            "current_value": entry.produto_normalizado,
            "eixo_original": entry.eixo_original,
            "eixo_normalizado": entry.eixo_normalizado,
            "confidence": entry.extraction_confidence,
            "review_reason": entry.review_reason or "",
            "servico_acao": entry.servico_acao,
            "tabela_tipo": entry.tabela_tipo,
        })

for entry in all_risks:
    if entry.needs_review:
        review_rows.append({
            "orgao_sigla": entry.orgao_sigla,
            "entry_type": "risk",
            "field": "probabilidade / impacto / tratamento",
            "original_value": f"P:{entry.probabilidade_original} | I:{entry.impacto_original} | T:{entry.tratamento_original}",
            "current_value": f"P:{entry.probabilidade_normalizada} | I:{entry.impacto_normalizado} | T:{entry.tratamento_normalizado}",
            "eixo_original": "",
            "eixo_normalizado": "",
            "confidence": entry.extraction_confidence,
            "review_reason": entry.review_reason or "",
            "servico_acao": entry.risco_texto[:100] if entry.risco_texto else "",
            "tabela_tipo": "",
        })

if review_rows:
    df_review = pd.DataFrame(review_rows)
    csv_path = os.path.join(DIRS["output"], "review_queue.csv")
    df_review.to_csv(csv_path, index=False, encoding="utf-8-sig")
    export_log.append(("review_queue.csv", len(df_review), _file_size_str(csv_path)))
else:
    print("Nenhum item pendente de revisão.")

# ---- Resumo de exportação ----
print("\n" + "=" * 60)
print("RESUMO DA EXPORTAÇÃO")
print("=" * 60)
print(f"Diretório de saída: {DIRS['output']}\n")
print(f"{'Arquivo':<30s} {'Registros':>10s} {'Tamanho':>10s}")
print("-" * 52)
for fname, rows, size in export_log:
    print(f"{fname:<30s} {rows:>10,d} {size:>10s}")
print("-" * 52)
total_files = len(export_log)
total_rows = sum(r for _, r, _ in export_log)
print(f"{'TOTAL':<30s} {total_rows:>10,d}   ({total_files} arquivos)")
print("=" * 60)
