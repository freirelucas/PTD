# ============================================================
# CÉLULA 9 — Padronização de Vocabulário
# ============================================================
from typing import List, Tuple, Dict
from collections import Counter


def standardize_deliveries(entries: List[DeliveryEntry]) -> Tuple[List[DeliveryEntry], Dict]:
    """
    Normaliza produto e eixo de cada DeliveryEntry usando matching em camadas.

    Retorna a lista atualizada e um relatório de vocabulário.
    """
    produto_mappings: Dict[str, Dict] = {}   # original -> {normalized, score, count}
    eixo_mappings: Dict[str, Dict] = {}
    unmatched_produtos: List[str] = []
    stats = Counter()  # exact, fuzzy, unmatched

    for entry in entries:
        # --- Produto ---
        prod_orig = normalize_text(entry.produto_original)

        if prod_orig in produto_mappings:
            cached = produto_mappings[prod_orig]
            entry.produto_normalizado = cached["normalized"]
            cached["count"] += 1
            score = cached["score"]
        else:
            matched, score = fuzzy_match_produto(entry.produto_original)
            if score >= 0.85:
                entry.produto_normalizado = matched
            elif score >= 0.70:
                entry.produto_normalizado = matched
                entry.needs_review = True
                entry.review_reason = f"fuzzy match baixo ({score:.2f})"
                entry.extraction_confidence = "medium"
            else:
                entry.produto_normalizado = "UNMATCHED"
                entry.needs_review = True
                entry.review_reason = f"produto não reconhecido (melhor score: {score:.2f})"
                entry.extraction_confidence = "low"

            produto_mappings[prod_orig] = {
                "normalized": entry.produto_normalizado,
                "score": score,
                "count": 1,
            }

        # Track stats
        if score == 1.0:
            stats["exact"] += 1
        elif score >= 0.70:
            stats["fuzzy"] += 1
        else:
            stats["unmatched"] += 1

        # --- Eixo ---
        eixo_orig = normalize_text(entry.eixo_original)

        if eixo_orig in eixo_mappings:
            cached_eixo = eixo_mappings[eixo_orig]
            entry.eixo_normalizado = cached_eixo["normalized"]
            cached_eixo["count"] += 1
        else:
            matched_eixo, eixo_score = fuzzy_match_eixo(entry.eixo_original)
            if eixo_score >= 0.70:
                entry.eixo_normalizado = matched_eixo
            else:
                entry.eixo_normalizado = entry.eixo_original  # keep original
            eixo_mappings[eixo_orig] = {
                "normalized": entry.eixo_normalizado,
                "score": eixo_score,
                "count": 1,
            }

        # --- Cross-validation: produto ↔ eixo ---
        if entry.produto_normalizado != "UNMATCHED" and entry.produto_normalizado in PRODUTO_TO_EIXO:
            canonical_eixo = PRODUTO_TO_EIXO[entry.produto_normalizado]
            if entry.eixo_normalizado != canonical_eixo:
                # Prefer the canonical mapping from the product
                old_eixo = entry.eixo_normalizado
                entry.eixo_normalizado = canonical_eixo
                if not entry.needs_review:
                    entry.needs_review = True
                    entry.review_reason = (
                        f"eixo corrigido por cross-validation: "
                        f"'{old_eixo}' → '{canonical_eixo}'"
                    )
                elif entry.review_reason and "eixo corrigido" not in entry.review_reason:
                    entry.review_reason += (
                        f"; eixo corrigido: '{old_eixo}' → '{canonical_eixo}'"
                    )

    # Build unmatched list
    unmatched_produtos = [
        orig for orig, info in produto_mappings.items()
        if info["normalized"] == "UNMATCHED"
    ]

    vocab_report = {
        "produto_mappings": [
            {
                "original": orig,
                "normalized": info["normalized"],
                "score": info["score"],
                "count": info["count"],
            }
            for orig, info in sorted(produto_mappings.items())
        ],
        "eixo_mappings": [
            {
                "original": orig,
                "normalized": info["normalized"],
                "score": info["score"],
                "count": info["count"],
            }
            for orig, info in sorted(eixo_mappings.items())
        ],
        "unmatched_produtos": unmatched_produtos,
        "match_stats": dict(stats),
    }

    return entries, vocab_report


def standardize_risks(entries: List[RiskEntry]) -> Tuple[List[RiskEntry], Dict]:
    """
    Normaliza probabilidade, impacto e tratamento de cada RiskEntry.

    Retorna a lista atualizada e um relatório de normalização.
    """
    prob_mappings: Dict[str, Dict] = {}
    imp_mappings: Dict[str, Dict] = {}
    trat_mappings: Dict[str, Dict] = {}
    stats = {
        "probabilidade": Counter(),  # exact, fuzzy, unmatched
        "impacto": Counter(),
        "tratamento": Counter(),
    }

    for entry in entries:
        review_reasons = []

        # --- Probabilidade ---
        prob_orig = normalize_text(entry.probabilidade_original)
        if prob_orig in prob_mappings:
            cached = prob_mappings[prob_orig]
            entry.probabilidade_normalizada = cached["normalized"]
            cached["count"] += 1
            p_score = cached["score"]
        else:
            matched, p_score = fuzzy_match_scale(entry.probabilidade_original, PROBABILIDADE_SCALE)
            if p_score >= 0.85:
                entry.probabilidade_normalizada = matched
            elif p_score >= 0.70:
                entry.probabilidade_normalizada = matched
                review_reasons.append(f"probabilidade fuzzy ({p_score:.2f})")
            else:
                entry.probabilidade_normalizada = entry.probabilidade_original
                review_reasons.append(f"probabilidade não reconhecida (score: {p_score:.2f})")
            prob_mappings[prob_orig] = {
                "normalized": entry.probabilidade_normalizada,
                "score": p_score,
                "count": 1,
            }

        if p_score == 1.0:
            stats["probabilidade"]["exact"] += 1
        elif p_score >= 0.70:
            stats["probabilidade"]["fuzzy"] += 1
        else:
            stats["probabilidade"]["unmatched"] += 1

        # --- Impacto ---
        imp_orig = normalize_text(entry.impacto_original)
        if imp_orig in imp_mappings:
            cached = imp_mappings[imp_orig]
            entry.impacto_normalizado = cached["normalized"]
            cached["count"] += 1
            i_score = cached["score"]
        else:
            matched, i_score = fuzzy_match_scale(entry.impacto_original, IMPACTO_SCALE)
            if i_score >= 0.85:
                entry.impacto_normalizado = matched
            elif i_score >= 0.70:
                entry.impacto_normalizado = matched
                review_reasons.append(f"impacto fuzzy ({i_score:.2f})")
            else:
                entry.impacto_normalizado = entry.impacto_original
                review_reasons.append(f"impacto não reconhecido (score: {i_score:.2f})")
            imp_mappings[imp_orig] = {
                "normalized": entry.impacto_normalizado,
                "score": i_score,
                "count": 1,
            }

        if i_score == 1.0:
            stats["impacto"]["exact"] += 1
        elif i_score >= 0.70:
            stats["impacto"]["fuzzy"] += 1
        else:
            stats["impacto"]["unmatched"] += 1

        # --- Tratamento (pode ser múltiplo: separado por ; , /) ---
        trat_orig = normalize_text(entry.tratamento_original)
        if trat_orig in trat_mappings:
            cached = trat_mappings[trat_orig]
            entry.tratamento_normalizado = cached["normalized"]
            cached["count"] += 1
            t_score = cached["score"]
        else:
            # Split by multiple separators
            parts = re.split(r"\s*[;,/]\s*", trat_orig) if trat_orig else []
            normalized_parts = []
            worst_score = 1.0

            for part in parts:
                part = part.strip()
                if not part:
                    continue
                matched, t_sc = fuzzy_match_scale(part, TRATAMENTO_OPTIONS)
                if t_sc >= 0.70:
                    normalized_parts.append(matched)
                else:
                    normalized_parts.append(part)
                    review_reasons.append(f"tratamento '{part}' não reconhecido (score: {t_sc:.2f})")
                worst_score = min(worst_score, t_sc)

            entry.tratamento_normalizado = "; ".join(normalized_parts) if normalized_parts else trat_orig
            t_score = worst_score if parts else 0.0
            trat_mappings[trat_orig] = {
                "normalized": entry.tratamento_normalizado,
                "score": t_score,
                "count": 1,
            }

        if t_score == 1.0:
            stats["tratamento"]["exact"] += 1
        elif t_score >= 0.70:
            stats["tratamento"]["fuzzy"] += 1
        else:
            stats["tratamento"]["unmatched"] += 1

        # --- Set confidence and review flags ---
        scores = [p_score, i_score, t_score]
        min_score = min(scores) if scores else 0.0

        if min_score >= 0.85:
            if not entry.needs_review:
                entry.extraction_confidence = "high"
        elif min_score >= 0.70:
            entry.extraction_confidence = "medium"
            entry.needs_review = True
        else:
            entry.extraction_confidence = "low"
            entry.needs_review = True

        if review_reasons:
            existing = entry.review_reason or ""
            new_reasons = "; ".join(review_reasons)
            entry.review_reason = f"{existing}; {new_reasons}".strip("; ") if existing else new_reasons

    risk_report = {
        "probabilidade_mappings": [
            {"original": orig, "normalized": info["normalized"], "score": info["score"], "count": info["count"]}
            for orig, info in sorted(prob_mappings.items())
        ],
        "impacto_mappings": [
            {"original": orig, "normalized": info["normalized"], "score": info["score"], "count": info["count"]}
            for orig, info in sorted(imp_mappings.items())
        ],
        "tratamento_mappings": [
            {"original": orig, "normalized": info["normalized"], "score": info["score"], "count": info["count"]}
            for orig, info in sorted(trat_mappings.items())
        ],
        "stats": {k: dict(v) for k, v in stats.items()},
    }

    return entries, risk_report


# ---- Execução ----
print("=" * 60)
print("PADRONIZAÇÃO DE VOCABULÁRIO")
print("=" * 60)

# Standardize deliveries
if all_deliveries:
    print(f"\nPadronizando {len(all_deliveries)} entregas...")
    all_deliveries, vocab_report = standardize_deliveries(all_deliveries)

    d_stats = vocab_report["match_stats"]
    d_total = sum(d_stats.values()) or 1
    print(f"\n  Produtos — Match exato: {d_stats.get('exact', 0)} "
          f"({d_stats.get('exact', 0)/d_total*100:.1f}%) | "
          f"Fuzzy: {d_stats.get('fuzzy', 0)} "
          f"({d_stats.get('fuzzy', 0)/d_total*100:.1f}%) | "
          f"Não reconhecidos: {d_stats.get('unmatched', 0)} "
          f"({d_stats.get('unmatched', 0)/d_total*100:.1f}%)")

    print(f"  Termos únicos de produto: {len(vocab_report['produto_mappings'])}")
    print(f"  Termos únicos de eixo:    {len(vocab_report['eixo_mappings'])}")

    if vocab_report["unmatched_produtos"]:
        print(f"\n  Produtos NÃO RECONHECIDOS ({len(vocab_report['unmatched_produtos'])}):")
        for p in vocab_report["unmatched_produtos"][:20]:
            print(f"    - '{p}'")
        if len(vocab_report["unmatched_produtos"]) > 20:
            print(f"    ... e mais {len(vocab_report['unmatched_produtos']) - 20}")
else:
    print("\nNenhuma entrega para padronizar.")
    vocab_report = {
        "produto_mappings": [],
        "eixo_mappings": [],
        "unmatched_produtos": [],
        "match_stats": {"exact": 0, "fuzzy": 0, "unmatched": 0},
    }

# Standardize risks
if all_risks:
    print(f"\nPadronizando {len(all_risks)} riscos...")
    all_risks, risk_report = standardize_risks(all_risks)

    for field_name in ["probabilidade", "impacto", "tratamento"]:
        fstats = risk_report["stats"].get(field_name, {})
        ftotal = sum(fstats.values()) or 1
        print(f"\n  {field_name.capitalize():<16s} — "
              f"Exato: {fstats.get('exact', 0):4d} ({fstats.get('exact', 0)/ftotal*100:.1f}%) | "
              f"Fuzzy: {fstats.get('fuzzy', 0):4d} ({fstats.get('fuzzy', 0)/ftotal*100:.1f}%) | "
              f"Falhou: {fstats.get('unmatched', 0):4d} ({fstats.get('unmatched', 0)/ftotal*100:.1f}%)")

    print(f"\n  Termos únicos — probabilidade: {len(risk_report['probabilidade_mappings'])}, "
          f"impacto: {len(risk_report['impacto_mappings'])}, "
          f"tratamento: {len(risk_report['tratamento_mappings'])}")
else:
    print("\nNenhum risco para padronizar.")
    risk_report = {
        "probabilidade_mappings": [],
        "impacto_mappings": [],
        "tratamento_mappings": [],
        "stats": {},
    }

# Review summary
n_review_del = sum(1 for d in all_deliveries if d.needs_review)
n_review_risk = sum(1 for r in all_risks if r.needs_review)
print(f"\n{'='*60}")
print(f"RESUMO DA PADRONIZAÇÃO")
print(f"  Entregas para revisão: {n_review_del}/{len(all_deliveries)}")
print(f"  Riscos para revisão:   {n_review_risk}/{len(all_risks)}")
print(f"{'='*60}")

# Save checkpoints
save_checkpoint(all_deliveries, "deliveries_standardized")
save_checkpoint(all_risks, "risks_standardized")
save_checkpoint(vocab_report, "vocab_report")
save_checkpoint(risk_report, "risk_report")
print("\nCheckpoints de padronização salvos.")
