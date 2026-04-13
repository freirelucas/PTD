# ============================================================
# CÉLULA 7 — Extração de Tabelas de Risco (Documentos Diretivos)
# ============================================================

def _map_risk_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Mapeia colunas do DataFrame para nomes canônicos de risco.

    Retorna dict com chaves canônicas e valores = nome real da coluna (ou None).
    """
    canonical = {
        "risco": None,
        "probabilidade": None,
        "impacto": None,
        "tratamento": None,
        "acoes": None,
    }

    # Keywords por campo canônico (prioridade decrescente)
    keyword_map = {
        "risco": ["risco", "evento", "descricao do risco", "descricao"],
        "probabilidade": ["probabilidade", "prob", "classificacao de probabilidade"],
        "impacto": ["impacto", "severidade", "classificacao de impacto"],
        "tratamento": ["tratamento", "resposta", "tipo de tratamento", "estrategia"],
        "acoes": ["acoes", "acao", "acoes de tratamento", "medidas", "plano de acao"],
    }

    headers = {str(c): _normalize_header(str(c)) for c in df.columns}

    for canon_key, keywords in keyword_map.items():
        best_col = None
        best_score = 0.0
        for col_name, col_norm in headers.items():
            for kw in keywords:
                # Substring match
                if kw in col_norm:
                    score = len(kw) / max(len(col_norm), 1)
                    score = max(score, 0.85)  # substring match gets high score
                    if score > best_score:
                        best_score = score
                        best_col = col_name
            # Fuzzy fallback
            if best_col is None:
                for kw in keywords:
                    ratio = difflib.SequenceMatcher(
                        None, col_norm, strip_accents(kw)
                    ).ratio()
                    if ratio > best_score and ratio >= 0.65:
                        best_score = ratio
                        best_col = col_name

        canonical[canon_key] = best_col

    return canonical


def _is_header_row(row: pd.Series, col_map: Dict[str, Optional[str]]) -> bool:
    """Verifica se uma row é na verdade a linha de cabeçalho repetida."""
    values = []
    for canon_key, col_name in col_map.items():
        if col_name is not None and col_name in row.index:
            values.append(_normalize_header(str(row[col_name])))
    header_keywords = [
        "risco", "probabilidade", "impacto", "tratamento", "acoes",
        "evento", "severidade", "resposta",
    ]
    hits = sum(1 for v in values if any(kw in v for kw in header_keywords))
    return hits >= 2


def extract_risk_table(
    pdf_path: str, sigla: str
) -> Tuple[List[RiskEntry], List[ProcessingError]]:
    """Extrai a tabela de riscos de um Documento Diretivo.

    Args:
        pdf_path: Caminho do PDF diretivo.
        sigla: Sigla do órgão.

    Returns:
        (lista de RiskEntry, lista de ProcessingError)
    """
    entries: List[RiskEntry] = []
    errors: List[ProcessingError] = []

    def _try_extract(conv: DocumentConverter) -> Tuple[List[RiskEntry], bool]:
        """Tenta extrair com um conversor. Retorna (entries, found_risk_table)."""
        result = conv.convert(pdf_path)
        local_entries: List[RiskEntry] = []
        found = False

        for table in result.document.tables:
            try:
                df = table.export_to_dataframe()
            except Exception as exc:
                logger.warning(f"[{sigla}] Falha ao exportar tabela: {exc}")
                continue

            if df is None or df.empty:
                continue

            classification = classify_diretivo_table(df)

            if classification != "risk_table":
                continue

            found = True
            col_map = _map_risk_columns(df)

            # Se a coluna 'risco' não foi mapeada, tentar usar a primeira coluna
            if col_map["risco"] is None and len(df.columns) > 0:
                col_map["risco"] = str(df.columns[0])

            mapped_count = sum(1 for v in col_map.values() if v is not None)

            for idx, row in df.iterrows():
                # Pular linhas de cabeçalho repetidas
                if _is_header_row(row, col_map):
                    continue

                # Extrair valores
                risco_raw = ""
                if col_map["risco"] and col_map["risco"] in row.index:
                    risco_raw = normalize_text(str(row[col_map["risco"]]))

                prob_raw = ""
                if col_map["probabilidade"] and col_map["probabilidade"] in row.index:
                    prob_raw = normalize_text(str(row[col_map["probabilidade"]]))

                imp_raw = ""
                if col_map["impacto"] and col_map["impacto"] in row.index:
                    imp_raw = normalize_text(str(row[col_map["impacto"]]))

                trat_raw = ""
                if col_map["tratamento"] and col_map["tratamento"] in row.index:
                    trat_raw = normalize_text(str(row[col_map["tratamento"]]))

                acoes_raw = ""
                if col_map["acoes"] and col_map["acoes"] in row.index:
                    acoes_raw = normalize_text(str(row[col_map["acoes"]]))

                # Limpar valores "nan"
                risco_raw = "" if risco_raw.lower() in ("nan", "none") else risco_raw
                prob_raw = "" if prob_raw.lower() in ("nan", "none") else prob_raw
                imp_raw = "" if imp_raw.lower() in ("nan", "none") else imp_raw
                trat_raw = "" if trat_raw.lower() in ("nan", "none") else trat_raw
                acoes_raw = "" if acoes_raw.lower() in ("nan", "none") else acoes_raw

                # Pular linhas completamente vazias
                if not risco_raw and not prob_raw and not imp_raw:
                    continue

                # Normalizar escalas
                prob_norm, prob_score = fuzzy_match_scale(prob_raw, PROBABILIDADE_SCALE)
                imp_norm, imp_score = fuzzy_match_scale(imp_raw, IMPACTO_SCALE)
                trat_norm, trat_score = fuzzy_match_scale(trat_raw, TRATAMENTO_OPTIONS)

                # Determinar confiança
                review_reasons = []
                if prob_raw and prob_score < 0.70:
                    review_reasons.append(f"probabilidade não mapeada: '{prob_raw}'")
                if imp_raw and imp_score < 0.70:
                    review_reasons.append(f"impacto não mapeado: '{imp_raw}'")
                if trat_raw and trat_score < 0.70:
                    review_reasons.append(f"tratamento não mapeado: '{trat_raw}'")
                if not risco_raw:
                    review_reasons.append("texto do risco vazio")

                if mapped_count >= 4 and not review_reasons:
                    confidence = "high"
                elif mapped_count >= 3 and len(review_reasons) <= 1:
                    confidence = "medium"
                else:
                    confidence = "low"

                entry = RiskEntry(
                    orgao_sigla=sigla,
                    risco_texto=risco_raw,
                    probabilidade_original=prob_raw,
                    probabilidade_normalizada=prob_norm if prob_score >= 0.70 else "",
                    impacto_original=imp_raw,
                    impacto_normalizado=imp_norm if imp_score >= 0.70 else "",
                    tratamento_original=trat_raw,
                    tratamento_normalizado=trat_norm if trat_score >= 0.70 else "",
                    acoes_tratamento=acoes_raw,
                    extraction_confidence=confidence,
                    needs_review=len(review_reasons) > 0,
                    review_reason="; ".join(review_reasons) if review_reasons else None,
                )
                local_entries.append(entry)

        return local_entries, found

    # Tentativa principal: modo ACCURATE
    try:
        entries, found = _try_extract(converter_accurate)
        if not found:
            # Fallback: modo FAST
            logger.info(f"[{sigla}] Tabela de risco não encontrada no modo ACCURATE, tentando FAST...")
            converter_fast = create_converter(accurate=False, ocr=True)
            entries, found = _try_extract(converter_fast)
            if not found:
                errors.append(ProcessingError(
                    orgao_sigla=sigla,
                    document_type="diretivo",
                    stage="extraction",
                    error_type="no_risk_table",
                    error_message=f"Nenhuma tabela de risco encontrada em {os.path.basename(pdf_path)}",
                ))
    except Exception as exc:
        logger.warning(f"[{sigla}] ACCURATE falhou: {exc}. Tentando modo FAST...")
        try:
            converter_fast = create_converter(accurate=False, ocr=True)
            entries, found = _try_extract(converter_fast)
            if not found:
                errors.append(ProcessingError(
                    orgao_sigla=sigla,
                    document_type="diretivo",
                    stage="extraction",
                    error_type="no_risk_table",
                    error_message=f"Nenhuma tabela de risco encontrada (modo FAST) em {os.path.basename(pdf_path)}",
                ))
        except Exception as exc2:
            errors.append(ProcessingError(
                orgao_sigla=sigla,
                document_type="diretivo",
                stage="extraction",
                error_type="docling_failure",
                error_message=f"Docling falhou em ambos os modos: {exc2}",
            ))

    return entries, errors


# --------------- Extração em lote -----------------------------

def extract_all_risks() -> None:
    """Extrai tabelas de risco de todos os órgãos com Documento Diretivo."""
    global all_risks, all_errors

    # Tentar carregar checkpoint
    cached = load_checkpoint("risks_raw")
    if cached is not None:
        cached_risks, cached_errors, processed_siglas = cached
        all_risks.extend(cached_risks)
        all_errors.extend(cached_errors)
        print(f"  Retomando: {len(cached_risks)} riscos já extraídos de {len(processed_siglas)} órgãos")
    else:
        cached_risks = []
        cached_errors = []
        processed_siglas = set()

    # Órgãos que têm PDF diretivo
    organs_with_pdf = [o for o in all_organs if o.pdf_path_diretivo]
    pending = [o for o in organs_with_pdf if o.sigla not in processed_siglas]

    if not pending:
        print("  Todos os órgãos já processados (checkpoint).")
        return

    print(f"  Processando riscos: {len(pending)} órgãos pendentes "
          f"({len(processed_siglas)} já processados)")

    # Rastreamento de PDFs já processados (para grupos com PDF compartilhado)
    pdf_results_cache: Dict[str, Tuple[List[RiskEntry], List[ProcessingError]]] = {}

    batch_risks: List[RiskEntry] = []
    batch_errors: List[ProcessingError] = []
    count = 0

    for organ in tqdm(pending, desc="Extraindo riscos"):
        sigla = organ.sigla
        pdf_path = organ.pdf_path_diretivo

        if not os.path.isfile(pdf_path):
            err = ProcessingError(
                orgao_sigla=sigla,
                document_type="diretivo",
                stage="extraction",
                error_type="file_not_found",
                error_message=f"PDF não encontrado: {pdf_path}",
            )
            batch_errors.append(err)
            all_errors.append(err)
            processed_siglas.add(sigla)
            count += 1
            continue

        # Verificar se o PDF já foi processado (órgãos agrupados)
        real_path = os.path.realpath(pdf_path)
        if real_path in pdf_results_cache:
            # Copiar resultados adaptando a sigla
            cached_entries, cached_errs = pdf_results_cache[real_path]
            for entry in cached_entries:
                new_entry = RiskEntry(
                    orgao_sigla=sigla,
                    risco_texto=entry.risco_texto,
                    probabilidade_original=entry.probabilidade_original,
                    probabilidade_normalizada=entry.probabilidade_normalizada,
                    impacto_original=entry.impacto_original,
                    impacto_normalizado=entry.impacto_normalizado,
                    tratamento_original=entry.tratamento_original,
                    tratamento_normalizado=entry.tratamento_normalizado,
                    acoes_tratamento=entry.acoes_tratamento,
                    extraction_confidence=entry.extraction_confidence,
                    needs_review=entry.needs_review,
                    review_reason=entry.review_reason,
                )
                batch_risks.append(new_entry)
                all_risks.append(new_entry)
            for err in cached_errs:
                new_err = ProcessingError(
                    orgao_sigla=sigla,
                    document_type=err.document_type,
                    stage=err.stage,
                    error_type=err.error_type,
                    error_message=err.error_message,
                )
                batch_errors.append(new_err)
                all_errors.append(new_err)
            processed_siglas.add(sigla)
            logger.info(f"[{sigla}] Reutilizando resultados de PDF compartilhado")
        else:
            # Processar PDF
            entries, errs = extract_risk_table(pdf_path, sigla)
            pdf_results_cache[real_path] = (entries, errs)

            batch_risks.extend(entries)
            all_risks.extend(entries)
            batch_errors.extend(errs)
            all_errors.extend(errs)
            processed_siglas.add(sigla)

            if entries:
                logger.info(f"[{sigla}] {len(entries)} riscos extraídos")
            else:
                logger.info(f"[{sigla}] Nenhum risco extraído")

        count += 1

        # Checkpoint a cada 10 órgãos
        if count % 10 == 0:
            save_checkpoint(
                (cached_risks + batch_risks, cached_errors + batch_errors, processed_siglas),
                "risks_raw",
            )

    # Checkpoint final
    save_checkpoint(
        (cached_risks + batch_risks, cached_errors + batch_errors, processed_siglas),
        "risks_raw",
    )
    print(f"  Extração de riscos concluída.")


# --------------- Execução -------------------------------------
extract_all_risks()

# Resumo
organs_with_risks = set(r.orgao_sigla for r in all_risks)
organs_without_risks = set(
    o.sigla for o in all_organs if o.pdf_path_diretivo
) - organs_with_risks
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
needs_review = [r for r in all_risks if r.needs_review]
print(f"  Riscos que precisam revisão: {len(needs_review)}")
confidence_counts = {}
for r in all_risks:
    confidence_counts[r.extraction_confidence] = confidence_counts.get(r.extraction_confidence, 0) + 1
print(f"  Confiança: {confidence_counts}")
