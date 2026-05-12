# ============================================================
# CÉLULA 11d — Fila de Revisão Humana (PTD_REVIEW)
# ============================================================
# Constrói a estrutura `PTD_REVIEW` com casos que precisam de
# atenção humana, agregados por (field, valor original).
#
# Cada item inclui:
#   - field, original, count
#   - normalized (o que canonização atribuiu)
#   - suggested (canônico mais próximo, mesmo abaixo do threshold)
#   - score, method ∈ {exact, alias, fuzzy_high, fuzzy_low, unmatched}
#   - examples: até 5 contextos (sigla + risco_texto/servico_acao)
#   - alias_snippet: linha Python pronta pra colar em 02_config.py
#   - impact_score = count × (1 - score), usado para ordenar
#
# Depende de: all_risks, all_deliveries, fuzzy_match_scale,
#             fuzzy_match_produto, fuzzy_match_eixo, normalize_text,
#             PROBABILIDADE_SCALE, IMPACTO_SCALE, TRATAMENTO_OPTIONS,
#             CANONICAL_EIXOS, ALL_PRODUTOS, DIRS
# ============================================================

from collections import defaultdict


_REVIEW_METHODS_TARGETED = {"unmatched", "fuzzy_low", "fuzzy_high"}
# Não inclui "alias" (já casou) nem "exact" (perfeito).


def _alias_snippet_line(original: str, suggested: str) -> str:
    """Gera a linha Python pra colar em PROBABILIDADE/IMPACTO/etc._ALIASES."""
    if not original or not suggested:
        return ""
    key = strip_accents(normalize_text(original).lower().strip())
    return f'"{key}": "{suggested}",'


def _build_field_review(entries, field_name, original_attr, normalized_attr,
                        score_attr, method_attr, suggester, scale_label,
                        context_attr):
    """Agrega casos atípicos para um campo específico.

    suggester(text) -> (canonical_value, score)
    """
    by_original = defaultdict(lambda: {
        "count": 0,
        "examples": [],
        "siglas": set(),
        "score_min": 1.0,
        "score_max": 0.0,
        "method": "",
        "normalized": "",
    })

    for e in entries:
        original = (getattr(e, original_attr, "") or "").strip()
        method = getattr(e, method_attr, "") or ""
        if not original:
            continue
        if method and method not in _REVIEW_METHODS_TARGETED:
            continue

        score = float(getattr(e, score_attr, 0.0) or 0.0)
        normalized = getattr(e, normalized_attr, "") or ""

        # Compute method on the fly if missing (legacy entries)
        if not method:
            if score <= 0.0:
                method = "unmatched"
            elif score >= 0.85:
                # high score but not exact/alias and we still want it surfaced?
                # Skip — high-confidence matches don't need review.
                continue
            elif score >= 0.70:
                method = "fuzzy_low"
            else:
                method = "unmatched"
            if method not in _REVIEW_METHODS_TARGETED:
                continue

        bucket = by_original[original]
        bucket["count"] += 1
        bucket["siglas"].add(e.orgao_sigla)
        bucket["score_min"] = min(bucket["score_min"], score)
        bucket["score_max"] = max(bucket["score_max"], score)
        bucket["method"] = method   # último vence; consistente p/ mesmo original
        bucket["normalized"] = normalized

        if len(bucket["examples"]) < 5:
            ctx = getattr(e, context_attr, "") or ""
            bucket["examples"].append({
                "sigla": e.orgao_sigla,
                "context": ctx[:140] + ("…" if len(ctx) > 140 else ""),
            })

    items = []
    for original, info in by_original.items():
        suggested, sug_score = suggester(original)
        snippet = _alias_snippet_line(original, suggested) if suggested and sug_score >= 0.50 else ""
        score = info["score_min"]
        items.append({
            "field": field_name,
            "scale_label": scale_label,
            "original": original,
            "normalized": info["normalized"],
            "suggested": suggested,
            "suggested_score": round(sug_score, 2),
            "score": round(score, 2),
            "method": info["method"],
            "count": info["count"],
            "siglas": sorted(info["siglas"]),
            "examples": info["examples"],
            "alias_snippet": snippet,
            "impact": round(info["count"] * (1.0 - score), 2),
        })
    return items


# Suggesters — retornam (best_canonical_text, score), independentes do threshold
def _suggest_prob(text):
    return fuzzy_match_scale(text, PROBABILIDADE_SCALE)

def _suggest_imp(text):
    return fuzzy_match_scale(text, IMPACTO_SCALE)

def _suggest_trat(text):
    return fuzzy_match_scale(text, TRATAMENTO_OPTIONS)

def _suggest_produto(text):
    return fuzzy_match_produto(text)

def _suggest_eixo(text):
    return fuzzy_match_eixo(text)


review_items = []

if all_risks:
    review_items += _build_field_review(
        all_risks, "probabilidade", "probabilidade_original",
        "probabilidade_normalizada", "probabilidade_score", "probabilidade_method",
        _suggest_prob, "probabilidade", "risco_texto",
    )
    review_items += _build_field_review(
        all_risks, "impacto", "impacto_original",
        "impacto_normalizado", "impacto_score", "impacto_method",
        _suggest_imp, "impacto", "risco_texto",
    )
    review_items += _build_field_review(
        all_risks, "tratamento", "tratamento_original",
        "tratamento_normalizado", "tratamento_score", "tratamento_method",
        _suggest_trat, "tratamento", "risco_texto",
    )

if all_deliveries:
    review_items += _build_field_review(
        all_deliveries, "produto", "produto_original",
        "produto_normalizado", "produto_score", "produto_method",
        _suggest_produto, "produto", "servico_acao",
    )
    review_items += _build_field_review(
        all_deliveries, "eixo", "eixo_original",
        "eixo_normalizado", "eixo_score", "eixo_method",
        _suggest_eixo, "eixo", "servico_acao",
    )

review_items.sort(key=lambda x: (-x["impact"], -x["count"], x["field"], x["original"]))


# Resumo agregado por field — útil pro header do painel
review_summary_by_field = defaultdict(lambda: {"cases": 0, "uniques": 0, "impact_total": 0.0})
for item in review_items:
    fs = review_summary_by_field[item["field"]]
    fs["cases"] += item["count"]
    fs["uniques"] += 1
    fs["impact_total"] += item["impact"]
review_summary_by_field = {k: {**v, "impact_total": round(v["impact_total"], 2)}
                           for k, v in review_summary_by_field.items()}


# Resumo agregado por method — diagnóstico do canon
method_counter = Counter()
for item in review_items:
    method_counter[item["method"]] += item["count"]


ptd_review = {
    "items": review_items,
    "summary_by_field": review_summary_by_field,
    "summary_by_method": dict(method_counter),
    "total_cases": sum(item["count"] for item in review_items),
    "total_uniques": len(review_items),
}


# Apêndice ao data.js
js_path = os.path.join(DIRS["output"], "data.js")
with open(js_path, "a", encoding="utf-8") as f:
    f.write(f"const PTD_REVIEW = {json.dumps(ptd_review, ensure_ascii=False)};\n")

# Standalone JSON para auditoria fora do dashboard
review_path = os.path.join(DIRS["output"], "review_data.json")
with open(review_path, "w", encoding="utf-8") as f:
    json.dump(ptd_review, f, ensure_ascii=False, indent=2)

print("=" * 60)
print("FILA DE REVISÃO (PTD_REVIEW)")
print("=" * 60)
print(f"  {ptd_review['total_uniques']} originais únicos não-canônicos")
print(f"  {ptd_review['total_cases']} casos no total")
for field, fs in sorted(review_summary_by_field.items(), key=lambda kv: -kv[1]["impact_total"]):
    print(f"    {field:<14s} {fs['uniques']:>3d} únicos | {fs['cases']:>4d} casos | impact={fs['impact_total']:.1f}")
print(f"  Por método: {dict(method_counter)}")
print(f"  Arquivo: {review_path}")
print("=" * 60)
