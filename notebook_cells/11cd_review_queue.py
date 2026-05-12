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


# Critical: precisam de julgamento humano (canonização falhou ou foi marginal).
# Curation: já canonizaram bem (score ≥ 0.85) mas via fuzzy — opcionalmente
# viram alias determinístico. Painel default mostra apenas critical.
_CRITICAL_METHODS = {"unmatched", "fuzzy_low"}
_CURATION_METHODS = {"fuzzy_high"}


def _alias_snippet_line(original: str, suggested: str) -> str:
    """Gera a linha Python pra colar em PROBABILIDADE/IMPACTO/etc._ALIASES."""
    if not original or not suggested:
        return ""
    key = strip_accents(normalize_text(original).lower().strip())
    return f'"{key}": "{suggested}",'


def _build_field_review(entries, field_name, original_attr, normalized_attr,
                        score_attr, method_attr, suggester, scale_label,
                        context_attr, methods_filter):
    """Agrega casos atípicos para um campo específico, restritos a `methods_filter`.

    suggester(text) -> (canonical_value, score)
    methods_filter: set de método ∈ {exact, alias, fuzzy_high, fuzzy_low, unmatched}
                    a incluir no resultado.
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

        score = float(getattr(e, score_attr, 0.0) or 0.0)
        normalized = getattr(e, normalized_attr, "") or ""

        # Compute method on the fly if missing (legacy entries sem *_method).
        if not method:
            if score <= 0.0:
                method = "unmatched"
            elif score >= 0.999:
                method = "exact"
            elif score >= 0.85:
                method = "fuzzy_high"
            elif score >= 0.70:
                method = "fuzzy_low"
            else:
                method = "unmatched"

        if method not in methods_filter:
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


def _collect_all_fields(methods_filter):
    """Roda _build_field_review pra todos os 5 campos canonizáveis com o filtro."""
    items = []
    if all_risks:
        items += _build_field_review(
            all_risks, "probabilidade", "probabilidade_original",
            "probabilidade_normalizada", "probabilidade_score", "probabilidade_method",
            _suggest_prob, "probabilidade", "risco_texto", methods_filter,
        )
        items += _build_field_review(
            all_risks, "impacto", "impacto_original",
            "impacto_normalizado", "impacto_score", "impacto_method",
            _suggest_imp, "impacto", "risco_texto", methods_filter,
        )
        items += _build_field_review(
            all_risks, "tratamento", "tratamento_original",
            "tratamento_normalizado", "tratamento_score", "tratamento_method",
            _suggest_trat, "tratamento", "risco_texto", methods_filter,
        )
    if all_deliveries:
        items += _build_field_review(
            all_deliveries, "produto", "produto_original",
            "produto_normalizado", "produto_score", "produto_method",
            _suggest_produto, "produto", "servico_acao", methods_filter,
        )
        items += _build_field_review(
            all_deliveries, "eixo", "eixo_original",
            "eixo_normalizado", "eixo_score", "eixo_method",
            _suggest_eixo, "eixo", "servico_acao", methods_filter,
        )
    items.sort(key=lambda x: (-x["impact"], -x["count"], x["field"], x["original"]))
    return items


def _build_summaries(items):
    """Agrega items por field e por method."""
    by_field = defaultdict(lambda: {"cases": 0, "uniques": 0, "impact_total": 0.0})
    by_method = Counter()
    for item in items:
        fs = by_field[item["field"]]
        fs["cases"] += item["count"]
        fs["uniques"] += 1
        fs["impact_total"] += item["impact"]
        by_method[item["method"]] += item["count"]
    return (
        {k: {**v, "impact_total": round(v["impact_total"], 2)} for k, v in by_field.items()},
        dict(by_method),
    )


# 1) Casos críticos — unmatched + fuzzy_low. Default da tab "Revisão".
review_items = _collect_all_fields(_CRITICAL_METHODS)
review_by_field, review_by_method = _build_summaries(review_items)

# 2) Curadoria opcional — fuzzy_high que poderiam virar alias determinístico.
#    Geralmente dominado por bugs de extração (truncamento de coluna, prefixo
#    de char de IBAMA, etc) — não vale adicionar como alias.
curation_items = _collect_all_fields(_CURATION_METHODS)
curation_by_field, curation_by_method = _build_summaries(curation_items)


ptd_review = {
    "items": review_items,
    "summary_by_field": review_by_field,
    "summary_by_method": review_by_method,
    "total_cases": sum(item["count"] for item in review_items),
    "total_uniques": len(review_items),
    # Bloco secundário, separado pra UI poder renderizar em accordion
    "curation": {
        "items": curation_items,
        "summary_by_field": curation_by_field,
        "summary_by_method": curation_by_method,
        "total_cases": sum(item["count"] for item in curation_items),
        "total_uniques": len(curation_items),
    },
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
print(f"  Críticos: {ptd_review['total_uniques']} originais únicos | "
      f"{ptd_review['total_cases']} casos | "
      f"métodos {ptd_review['summary_by_method']}")
for field, fs in sorted(review_by_field.items(), key=lambda kv: -kv[1]["impact_total"]):
    print(f"    {field:<14s} {fs['uniques']:>3d} únicos | {fs['cases']:>4d} casos | impact={fs['impact_total']:.1f}")
print(f"  Curadoria opcional: {ptd_review['curation']['total_uniques']} originais únicos | "
      f"{ptd_review['curation']['total_cases']} casos (fuzzy_high)")
print(f"  Arquivo: {review_path}")
print("=" * 60)
