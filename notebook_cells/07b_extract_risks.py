# ============================================================
# CÉLULA 7 — Extração de Tabelas de Risco (PyMuPDF find_tables)
# ============================================================
# Inclui: merge multi-página, recuperação header-as-data,
# resolução de referências numéricas de ações.

def _map_risk_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    canonical = {"risco":None,"probabilidade":None,"impacto":None,"tratamento":None,"acoes":None}
    keyword_map = {
        "risco": ["risco","evento","descricao do risco","descricao","id do risco"],
        "probabilidade": ["probabilidade","probabilidade de ocorrer","prob","classificacao de probabilidade"],
        "impacto": ["impacto","severidade","classificacao de impacto"],
        "tratamento": ["opcao de tratamento","tratamento","resposta","tipo de tratamento","estrategia"],
        "acoes": ["acoes de tratamento","descrever acoes","acoes","acao","medidas","plano de acao"],
    }
    headers = {str(c): _normalize_header(str(c)) for c in df.columns}
    for canon_key, keywords in keyword_map.items():
        best_col, best_score = None, 0.0
        for col_name, col_norm in headers.items():
            for kw in keywords:
                if kw in col_norm:
                    score = max(len(kw)/max(len(col_norm),1), 0.85)
                    if score > best_score: best_score, best_col = score, col_name
            if best_col is None:
                for kw in keywords:
                    ratio = difflib.SequenceMatcher(None, col_norm, strip_accents(kw)).ratio()
                    if ratio > best_score and ratio >= 0.65: best_score, best_col = ratio, col_name
        canonical[canon_key] = best_col

    # Fallback posicional: quando o cabeçalho do PDF é genérico (Col0/Col2)
    # ou fragmentado, usa a posição padrão do template SGD (5 colunas).
    # Aplica somente se a coluna posicional estiver livre — não sobrescreve
    # mapeamentos por keyword.
    fallback_pos = {"risco": 0, "probabilidade": 1, "impacto": 2, "tratamento": 3, "acoes": 4}
    used_cols = {v for v in canonical.values() if v is not None}
    cols_list = [str(c) for c in df.columns]
    # Detecta offset por id_risco quando ncols >= 6 e a primeira coluna parece ID
    offset = 1 if len(cols_list) >= 6 and _normalize_header(cols_list[0]) in (
        "id do risco", "id", "n", "no", "num", "numero", "col0") else 0
    for field, pos in fallback_pos.items():
        if canonical[field] is None and pos + offset < len(cols_list):
            cand = cols_list[pos + offset]
            if cand not in used_cols:
                canonical[field] = cand
                used_cols.add(cand)
    return canonical


def extract_risk_table(pdf_path: str, sigla: str) -> Tuple[List[RiskEntry], List[ProcessingError]]:
    entries: List[RiskEntry] = []
    errors: List[ProcessingError] = []

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        errors.append(ProcessingError(orgao_sigla=sigla, document_type="diretivo",
            stage="extraction", error_type="pdf_open_failed", error_message=str(exc)))
        return entries, errors

    # Extrair lista de ações de tratamento
    full_text = "\n".join(p.get_text() for p in doc)
    action_list = _extract_action_list(full_text)

    risk_ncols = None
    col_order = None

    for page in doc:
        tabs = page.find_tables()
        if not tabs.tables:
            continue
        for table in tabs.tables:
            try:
                df = table.to_pandas()
            except Exception:
                continue
            if df is None or df.shape[1] < 4:
                continue

            df = _consolidate_multiline_cells(df)

            has_header = classify_diretivo_table(df) == "risk_table"
            data_as_header = _cols_are_data(df)
            is_continuation = (risk_ncols and df.shape[1] == risk_ncols
                               and not has_header and _is_risk_data(df))
            is_orphan = (not has_header and not data_as_header and not is_continuation
                         and _is_orphan_risk_data(df))

            if not has_header and not data_as_header and not is_continuation and not is_orphan:
                continue

            if has_header:
                col_map = _map_risk_columns(df)
                if col_map["risco"] is None and len(df.columns) > 0:
                    col_map["risco"] = str(df.columns[0])
                col_order = list(col_map.keys())
                risk_ncols = len(df.columns)

                if len(df) > 0 and _is_subheader_row(df.iloc[0]):
                    df = df.iloc[1:].reset_index(drop=True)
                if len(df) == 0:
                    continue

            elif data_as_header:
                risk_ncols = len(df.columns)
                if col_order is None:
                    col_order = ["risco", "probabilidade", "impacto", "tratamento", "acoes"]
                    if df.shape[1] >= 6:
                        col_order = ["id_risco"] + col_order

                # Recuperar primeiro risco do header
                vals = [normalize_text(str(c)) for c in df.columns]
                vals = ["" if v.lower() in ("nan", "none") else v for v in vals]
                if vals[0] and not _is_subheader_row(vals):
                    prob_raw = vals[1] if len(vals) > 1 else ""
                    imp_raw = vals[2] if len(vals) > 2 else ""
                    trat_raw = vals[3] if len(vals) > 3 else ""
                    acoes_raw = vals[4] if len(vals) > 4 else ""
                    prob_m = fuzzy_match_scale(prob_raw, PROBABILIDADE_SCALE)
                    imp_m = fuzzy_match_scale(imp_raw, IMPACTO_SCALE)
                    trat_m = fuzzy_match_scale(trat_raw, TRATAMENTO_OPTIONS)
                    entries.append(RiskEntry(
                        orgao_sigla=sigla, risco_texto=vals[0],
                        probabilidade_original=prob_raw,
                        probabilidade_normalizada=prob_m[0] if prob_m[1] >= 0.70 else "",
                        impacto_original=imp_raw,
                        impacto_normalizado=imp_m[0] if imp_m[1] >= 0.70 else "",
                        tratamento_original=trat_raw,
                        tratamento_normalizado=trat_m[0] if trat_m[1] >= 0.70 else "",
                        acoes_tratamento=_resolve_action_refs(acoes_raw, action_list),
                        extraction_confidence="medium",
                        needs_review=True,
                        review_reason="recuperado de header de coluna",
                    ))

            elif is_continuation and col_order:
                if len(df) > 0 and _is_subheader_row(df.iloc[0]):
                    df = df.iloc[1:].reset_index(drop=True)

            elif is_orphan:
                risk_ncols = len(df.columns)
                if col_order is None:
                    col_order = ["risco", "probabilidade", "impacto", "tratamento", "acoes"]
                    if df.shape[1] >= 6:
                        col_order = ["id_risco"] + col_order
                if len(df) > 0 and _is_subheader_row(df.iloc[0]):
                    df = df.iloc[1:].reset_index(drop=True)
                if len(df) == 0:
                    continue

            if col_order is None:
                continue

            mapped_count = sum(1 for k in col_order if k in (col_map if has_header else {}))
            if has_header:
                active_map = col_map
            else:
                # Mapeamento posicional. Detecta offset de id_risco quando a
                # tabela tem 1 coluna a mais que o col_order esperado e a 1ª
                # coluna parece um identificador curto (single char/num).
                cols_list = [str(c) for c in df.columns]
                offset = 0
                if len(cols_list) > len(col_order) and len(df) > 0:
                    first_vals = [str(df.iloc[r, 0]).strip() for r in range(min(3, len(df)))]
                    if all(len(v) <= 3 and v.lower() not in ("nan","none","") for v in first_vals if v):
                        offset = 1
                active_map = {f: cols_list[i + offset]
                              for i, f in enumerate(col_order)
                              if i + offset < len(cols_list)}

            for _, row in df.iterrows():
                if _is_subheader_row(row):
                    continue

                def _get(field):
                    col = active_map.get(field)
                    if col and col in row.index:
                        v = normalize_text(str(row[col]))
                        return "" if v.lower() in ("nan", "none") else v
                    return ""

                risco = _get("risco")
                prob = _get("probabilidade")
                imp = _get("impacto")
                trat = _get("tratamento")
                acoes = _get("acoes")

                if not risco and not prob and not imp:
                    continue

                prob_m = fuzzy_match_scale(prob, PROBABILIDADE_SCALE)
                imp_m = fuzzy_match_scale(imp, IMPACTO_SCALE)
                trat_m = fuzzy_match_scale(trat, TRATAMENTO_OPTIONS)
                acoes_resolved = _resolve_action_refs(acoes, action_list)

                review_reasons = []
                if prob and prob_m[1] < 0.70: review_reasons.append(f"probabilidade: '{prob}'")
                if imp and imp_m[1] < 0.70: review_reasons.append(f"impacto: '{imp}'")
                if not risco: review_reasons.append("risco vazio")

                confidence = ("high" if not review_reasons else
                              "medium" if len(review_reasons) <= 1 else "low")

                entries.append(RiskEntry(
                    orgao_sigla=sigla, risco_texto=risco,
                    probabilidade_original=prob,
                    probabilidade_normalizada=prob_m[0] if prob_m[1] >= 0.70 else "",
                    impacto_original=imp,
                    impacto_normalizado=imp_m[0] if imp_m[1] >= 0.70 else "",
                    tratamento_original=trat,
                    tratamento_normalizado=trat_m[0] if trat_m[1] >= 0.70 else "",
                    acoes_tratamento=acoes_resolved,
                    extraction_confidence=confidence,
                    needs_review=len(review_reasons) > 0,
                    review_reason="; ".join(review_reasons) if review_reasons else None,
                ))

    doc.close()
    if not entries:
        errors.append(ProcessingError(orgao_sigla=sigla, document_type="diretivo",
            stage="extraction", error_type="no_risk_table",
            error_message=f"Nenhuma tabela de risco encontrada em {os.path.basename(pdf_path)}"))

    return entries, errors


# --------------- Extração em lote -----------------------------

def extract_all_risks() -> None:
    global all_risks, all_errors

    cached = load_checkpoint("risks_raw")
    if cached is not None and len(cached[0]) > 0:
        cached_risks, cached_errors, processed_siglas = cached
        all_risks.extend(cached_risks)
        all_errors.extend(cached_errors)
        print(f"  Retomando: {len(cached_risks)} riscos de {len(processed_siglas)} órgãos")
    else:
        cached_risks, cached_errors, processed_siglas = [], [], set()

    organs_with_pdf = [o for o in all_organs if o.pdf_path_diretivo]
    pending = [o for o in organs_with_pdf if o.sigla not in processed_siglas]

    if not pending:
        print("  Todos os órgãos já processados (checkpoint).")
        return

    print(f"  Processando: {len(pending)} órgãos pendentes")

    pdf_results_cache: Dict[str, Tuple[List[RiskEntry], List[ProcessingError], str]] = {}
    batch_risks, batch_errors = [], []
    count = 0

    for organ in tqdm(pending, desc="Extraindo riscos"):
        sigla = organ.sigla
        pdf_path = organ.pdf_path_diretivo

        if not os.path.isfile(pdf_path):
            batch_errors.append(ProcessingError(orgao_sigla=sigla, document_type="diretivo",
                stage="extraction", error_type="file_not_found",
                error_message=f"PDF não encontrado: {pdf_path}"))
            processed_siglas.add(sigla)
            count += 1
            continue

        real_path = os.path.realpath(pdf_path)
        if real_path in pdf_results_cache:
            owner = pdf_results_cache[real_path][2]
            processed_siglas.add(sigla)
            logger.info(f"[{sigla}] PDF compartilhado com {owner} — sem duplicação")
        else:
            entries, errs = extract_risk_table(pdf_path, sigla)
            pdf_results_cache[real_path] = (entries, errs, sigla)
            batch_risks.extend(entries)
            all_risks.extend(entries)
            batch_errors.extend(errs)
            all_errors.extend(errs)
            processed_siglas.add(sigla)
            if entries:
                logger.info(f"[{sigla}] {len(entries)} riscos extraídos")

        count += 1
        if count % 10 == 0:
            save_checkpoint((cached_risks + batch_risks, cached_errors + batch_errors, processed_siglas), "risks_raw")

    save_checkpoint((cached_risks + batch_risks, cached_errors + batch_errors, processed_siglas), "risks_raw")
    print(f"  Extração de riscos concluída.")


# --------------- Execução -------------------------------------
extract_all_risks()

organs_with_risks = set(r.orgao_sigla for r in all_risks)
organs_without_risks = set(o.sigla for o in all_organs if o.pdf_path_diretivo) - organs_with_risks
risk_errors = [e for e in all_errors if e.document_type == "diretivo" and e.stage == "extraction"]

print(f"\n{'='*60}")
print(f"RESUMO — Extração de Riscos")
print(f"{'='*60}")
print(f"  Total de riscos extraídos: {len(all_risks)}")
print(f"  Órgãos com tabela de risco: {len(organs_with_risks)}")
print(f"  Órgãos sem tabela de risco: {len(organs_without_risks)}")
if organs_without_risks:
    print(f"    → {', '.join(sorted(organs_without_risks))}")
print(f"  Erros de extração: {len(risk_errors)}")
n_with_acoes = sum(1 for r in all_risks if r.acoes_tratamento and r.acoes_tratamento.strip())
print(f"  Riscos com ações de tratamento: {n_with_acoes}")
