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
        "risco": ["risco", "evento", "descricao do risco", "descricao", "id do risco"],
        "probabilidade": ["probabilidade", "probabilidade de ocorrer", "prob",
                          "classificacao de probabilidade"],
        "impacto": ["impacto", "severidade", "classificacao de impacto"],
        "tratamento": ["opcao de tratamento", "tratamento", "resposta",
                       "tipo de tratamento", "estrategia"],
        "acoes": ["acoes de tratamento", "descrever acoes", "acoes", "acao",
                  "medidas", "plano de acao"],
    }

    # Limpar headers: tratar quebras de linha e hífens
    def _clean_h(c):
        s = _normalize_header(str(c))
        s = s.replace("- ", "").replace("-\n", "")
        return s
    headers = {str(c): _clean_h(c) for c in df.columns}

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


def _cols_are_data(df: pd.DataFrame) -> bool:
    """Detecta se find_tables/Docling interpretou o 1o risco como header de coluna."""
    if df.shape[1] < 4:
        return False
    col0 = _normalize_header(str(df.columns[0]))
    if len(col0) < 10 or col0.startswith("risco") or col0.startswith("col") or col0 == "nan":
        return False
    col1 = _normalize_header(str(df.columns[1]))
    scale_vals = ["raro", "pouco provavel", "provavel", "muito provavel", "praticamente certo",
                  "baixo", "medio", "alto", "muito alto", "baixa", "media", "alta"]
    return any(sv in strip_accents(col1) for sv in scale_vals)


def _is_risk_data(df: pd.DataFrame) -> bool:
    """Verifica se uma tabela contém valores de escala de risco (tabela de continuação)."""
    if df is None or df.empty or df.shape[1] < 4:
        return False
    all_text = strip_accents(" ".join(str(v).lower() for v in df.values.flatten()))
    scale_vals = ["raro", "pouco provavel", "provavel", "muito provavel", "praticamente certo",
                  "muito baixo", "baixo", "medio", "alto", "muito alto",
                  "mitigar", "eliminar", "transferir", "aceitar", "baixa", "media", "alta"]
    return sum(1 for sv in scale_vals if sv in all_text) >= 2


def _extract_action_list_from_text(doc_text: str) -> dict:
    """Extrai a lista 'Referencial para ações de tratamento do risco' do texto do documento."""
    actions = {}
    for pat in [r"[Rr]eferencial\s+para\s+a[çc][õo]es\s+de\s+tratamento",
                r"[Aa][çc][õo]es\s+de\s+tratamento\s+do\s+risco\s*:"]:
        m = re.search(pat, doc_text)
        if m:
            for line in doc_text[m.end():].split('\n'):
                line = line.strip()
                am = re.match(r"^(\d{1,2})\s*[\.\-\)]\s*(.+)", line)
                if am:
                    actions[am.group(1)] = am.group(2).strip()
                elif actions and not line[0:1].isdigit() and len(actions) > 3:
                    break
            if actions:
                return actions
    return actions


def _resolve_action_refs(acoes_text: str, action_list: dict) -> str:
    """Resolve referências numéricas ('1, 2, 9') para texto completo."""
    if not acoes_text or not action_list:
        return acoes_text
    refs = re.findall(r'\d+', acoes_text)
    if not refs:
        return acoes_text
    tokens = re.split(r'[,;\s]+', acoes_text.strip())
    num_tokens = sum(1 for t in tokens if re.match(r'^\d+$', t.strip()))
    if num_tokens / max(len(tokens), 1) < 0.5:
        return acoes_text  # texto livre, não referência
    resolved = [f"{ref}. {action_list[ref]}" for ref in refs if ref in action_list]
    return " | ".join(resolved) if resolved else acoes_text


def extract_risk_table(
    pdf_path: str, sigla: str
) -> Tuple[List[RiskEntry], List[ProcessingError]]:
    """Extrai a tabela de riscos de um Documento Diretivo.

    Inclui:
    - Merge de tabelas multi-página (header na pág N, dados na pág N+1)
    - Recuperação de riscos que viraram header de coluna em tabelas de continuação
    - Resolução de referências numéricas de ações ('1, 2, 9' → texto completo)
    """
    entries: List[RiskEntry] = []
    errors: List[ProcessingError] = []

    def _try_extract(conv: DocumentConverter) -> Tuple[List[RiskEntry], bool]:
        result = conv.convert(pdf_path)

        # Detectar formato legado
        legacy = detect_legacy_format(result)
        if legacy:
            logger.info(f"[{sigla}] Formato legado detectado ({legacy})")
            errors.append(ProcessingError(
                orgao_sigla=sigla, document_type="diretivo", stage="extraction",
                error_type="legacy_format",
                error_message=f"Formato legado {legacy}: estrutura pode diferir do template atual",
            ))

        # Extrair lista de ações de tratamento do texto do documento
        try:
            doc_text = result.document.export_to_markdown()
        except Exception:
            doc_text = ""
        action_list = _extract_action_list_from_text(doc_text)

        local_entries: List[RiskEntry] = []
        found = False
        risk_ncols = None
        col_map = None

        for table in result.document.tables:
            try:
                df = table.export_to_dataframe()
            except Exception as exc:
                logger.warning(f"[{sigla}] Falha ao exportar tabela: {exc}")
                continue

            if df is None or df.shape[1] < 4:
                continue

            has_header = classify_diretivo_table(df) == "risk_table"
            data_as_header = _cols_are_data(df)
            is_continuation = (risk_ncols and df.shape[1] == risk_ncols
                               and not has_header and _is_risk_data(df))

            if not has_header and not data_as_header and not is_continuation:
                continue

            found = True

            if has_header:
                col_map = _map_risk_columns(df)
                if col_map["risco"] is None and len(df.columns) > 0:
                    col_map["risco"] = str(df.columns[0])
                risk_ncols = len(df.columns)

                # Checar se primeira linha é sub-header
                if len(df) > 0 and _is_header_row(df.iloc[0], col_map):
                    df = df.iloc[1:].reset_index(drop=True)
                if len(df) == 0:
                    continue  # Header-only, dados na próxima tabela

            elif data_as_header:
                # Primeiro risco virou header de coluna — recuperar
                risk_ncols = len(df.columns)
                if col_map is None:
                    # Inferir col_map pela posição
                    col_names = list(df.columns)
                    col_map = {}
                    positions = ["risco", "probabilidade", "impacto", "tratamento", "acoes"]
                    if len(col_names) >= 6:
                        positions = ["id_risco"] + positions
                    for i, field in enumerate(positions):
                        if i < len(col_names):
                            col_map[field] = str(col_names[i])

                # Extrair o risco que virou header
                header_vals = {str(c): normalize_text(str(c)) for c in df.columns}
                risco_raw = normalize_text(str(df.columns[0])) if col_map.get("risco") else ""
                if risco_raw.lower() not in ("nan", "none", "") and not _is_header_row(
                    pd.Series({str(c): str(c) for c in df.columns}), col_map
                ):
                    prob_col = col_map.get("probabilidade", "")
                    imp_col = col_map.get("impacto", "")
                    trat_col = col_map.get("tratamento", "")
                    acoes_col = col_map.get("acoes", "")

                    prob_raw = normalize_text(str(dict(zip([str(c) for c in df.columns], df.columns)).get(prob_col, "")))
                    # Simplificar: usar posição
                    cols_list = [normalize_text(str(c)) for c in df.columns]
                    for var in cols_list:
                        if var.lower() in ("nan", "none"):
                            cols_list[cols_list.index(var)] = ""

                    p_raw = cols_list[1] if len(cols_list) > 1 else ""
                    i_raw = cols_list[2] if len(cols_list) > 2 else ""
                    t_raw = cols_list[3] if len(cols_list) > 3 else ""
                    a_raw = cols_list[4] if len(cols_list) > 4 else ""

                    prob_norm, prob_score = fuzzy_match_scale(p_raw, PROBABILIDADE_SCALE)
                    imp_norm, imp_score = fuzzy_match_scale(i_raw, IMPACTO_SCALE)
                    trat_norm, trat_score = fuzzy_match_scale(t_raw, TRATAMENTO_OPTIONS)
                    acoes_resolved = _resolve_action_refs(a_raw, action_list)

                    local_entries.append(RiskEntry(
                        orgao_sigla=sigla, risco_texto=cols_list[0],
                        probabilidade_original=p_raw,
                        probabilidade_normalizada=prob_norm if prob_score >= 0.70 else "",
                        impacto_original=i_raw,
                        impacto_normalizado=imp_norm if imp_score >= 0.70 else "",
                        tratamento_original=t_raw,
                        tratamento_normalizado=trat_norm if trat_score >= 0.70 else "",
                        acoes_tratamento=acoes_resolved,
                        extraction_confidence="medium",
                        needs_review=True,
                        review_reason="recuperado de header de coluna",
                    ))

            elif is_continuation and col_map:
                # Tabela de continuação — pular sub-headers
                if len(df) > 0 and _is_header_row(df.iloc[0], col_map):
                    df = df.iloc[1:].reset_index(drop=True)

            # Extrair linhas de dados
            if col_map is None:
                continue

            mapped_count = sum(1 for v in col_map.values() if v is not None)

            for idx, row in df.iterrows():
                if _is_header_row(row, col_map):
                    continue

                risco_raw = ""
                if col_map.get("risco") and col_map["risco"] in row.index:
                    risco_raw = normalize_text(str(row[col_map["risco"]]))
                prob_raw = ""
                if col_map.get("probabilidade") and col_map["probabilidade"] in row.index:
                    prob_raw = normalize_text(str(row[col_map["probabilidade"]]))
                imp_raw = ""
                if col_map.get("impacto") and col_map["impacto"] in row.index:
                    imp_raw = normalize_text(str(row[col_map["impacto"]]))
                trat_raw = ""
                if col_map.get("tratamento") and col_map["tratamento"] in row.index:
                    trat_raw = normalize_text(str(row[col_map["tratamento"]]))
                acoes_raw = ""
                if col_map.get("acoes") and col_map["acoes"] in row.index:
                    acoes_raw = normalize_text(str(row[col_map["acoes"]]))

                # Limpar nan
                for var_name in ["risco_raw", "prob_raw", "imp_raw", "trat_raw", "acoes_raw"]:
                    if eval(var_name).lower() in ("nan", "none"):
                        exec(f"{var_name} = ''")

                if not risco_raw and not prob_raw and not imp_raw:
                    continue

                # Normalizar
                prob_norm, prob_score = fuzzy_match_scale(prob_raw, PROBABILIDADE_SCALE)
                imp_norm, imp_score = fuzzy_match_scale(imp_raw, IMPACTO_SCALE)
                trat_norm, trat_score = fuzzy_match_scale(trat_raw, TRATAMENTO_OPTIONS)
                acoes_resolved = _resolve_action_refs(acoes_raw, action_list)

                review_reasons = []
                if prob_raw and prob_score < 0.70:
                    review_reasons.append(f"probabilidade não mapeada: '{prob_raw}'")
                if imp_raw and imp_score < 0.70:
                    review_reasons.append(f"impacto não mapeado: '{imp_raw}'")
                if not risco_raw:
                    review_reasons.append("texto do risco vazio")

                confidence = "high" if mapped_count >= 4 and not review_reasons else \
                             "medium" if mapped_count >= 3 and len(review_reasons) <= 1 else "low"

                local_entries.append(RiskEntry(
                    orgao_sigla=sigla, risco_texto=risco_raw,
                    probabilidade_original=prob_raw,
                    probabilidade_normalizada=prob_norm if prob_score >= 0.70 else "",
                    impacto_original=imp_raw,
                    impacto_normalizado=imp_norm if imp_score >= 0.70 else "",
                    tratamento_original=trat_raw,
                    tratamento_normalizado=trat_norm if trat_score >= 0.70 else "",
                    acoes_tratamento=acoes_resolved,
                    extraction_confidence=confidence,
                    needs_review=len(review_reasons) > 0,
                    review_reason="; ".join(review_reasons) if review_reasons else None,
                ))

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

    # Tentar carregar checkpoint (só usa se tiver dados reais)
    cached = load_checkpoint("risks_raw")
    if cached is not None and len(cached[0]) > 0:
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
            # PDF compartilhado — não duplicar entries (evita dupla contagem).
            # O órgão-cabeça já possui os registros; este membro é apenas
            # marcado como processado.
            owner_sigla = pdf_results_cache[real_path][2]
            processed_siglas.add(sigla)
            logger.info(
                f"[{sigla}] PDF compartilhado com {owner_sigla} — "
                f"riscos atribuídos a {owner_sigla} (sem duplicação)"
            )
        else:
            # Processar PDF
            entries, errs = extract_risk_table(pdf_path, sigla)
            pdf_results_cache[real_path] = (entries, errs, sigla)

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
