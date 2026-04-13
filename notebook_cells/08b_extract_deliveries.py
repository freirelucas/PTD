# ============================================================
# CÉLULA 8 — Extração de Tabelas de Entregas (Anexos de Entregas)
# ============================================================

def _map_entregas_columns(
    df: pd.DataFrame, tabela_tipo: str
) -> Dict[str, Optional[str]]:
    """Mapeia colunas do DataFrame para nomes canônicos de entregas.

    Args:
        df: DataFrame da tabela extraída.
        tabela_tipo: 'pactuadas', 'concluidas', ou 'canceladas'.

    Returns:
        Dict com chaves canônicas e valores = nome real da coluna (ou None).
    """
    canonical: Dict[str, Optional[str]] = {
        "servico_acao": None,
        "produto": None,
        "eixo": None,
        "area_responsavel": None,
        "data_pactuada": None,
        "data_entrega": None,
        "pactuado": None,
        "justificativa": None,
    }

    keyword_map = {
        "servico_acao": [
            "servico", "acao", "servico/acao", "servico / acao",
            "nome do servico", "servico ou acao",
        ],
        "produto": [
            "produto", "produto ptd", "entrega", "produto/entrega",
        ],
        "eixo": [
            "eixo", "eixo ptd", "eixo de transformacao",
        ],
        "area_responsavel": [
            "area responsavel", "arearesponsavel", "area", "responsavel",
            "unidade responsavel", "setor",
        ],
        "data_pactuada": [
            "dtpactuada", "dt pactuada", "data pactuada", "datapactuada",
            "prazo", "data prevista", "previsao",
        ],
        "data_entrega": [
            "dtentrega", "dt entrega", "data entrega", "dataentrega",
            "data de entrega", "data conclusao", "dataconclusao",
        ],
        "pactuado": [
            "pactuado?", "pactuado ?", "pactuado", "foi pactuado",
        ],
        "justificativa": [
            "justificativa", "motivo", "motivo cancelamento",
            "motivo do cancelamento", "observacao", "obs",
        ],
    }

    headers = {str(c): _normalize_header(str(c)) for c in df.columns}

    for canon_key, keywords in keyword_map.items():
        best_col = None
        best_score = 0.0

        for col_name, col_norm in headers.items():
            # Remove espaços para comparação compacta
            col_compact = col_norm.replace(" ", "")

            for kw in keywords:
                kw_norm = strip_accents(kw.lower())
                kw_compact = kw_norm.replace(" ", "")

                # Substring match
                if kw_norm in col_norm or kw_compact in col_compact:
                    score = len(kw_norm) / max(len(col_norm), 1)
                    score = max(score, 0.85)
                    if score > best_score:
                        best_score = score
                        best_col = col_name
                    continue

                # Fuzzy match
                ratio = difflib.SequenceMatcher(
                    None, col_norm, kw_norm
                ).ratio()
                if ratio > best_score and ratio >= 0.65:
                    best_score = ratio
                    best_col = col_name

        canonical[canon_key] = best_col

    return canonical


def _clean_cell(value) -> str:
    """Limpa valor de célula: trata NaN, multi-line, espaços extras."""
    if value is None:
        return ""
    s = str(value)
    if s.lower() in ("nan", "none", "nat", ""):
        return ""
    # Multi-line text: juntar com espaço
    s = re.sub(r"[\r\n]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_entregas_header_row(row: pd.Series, col_map: Dict[str, Optional[str]]) -> bool:
    """Verifica se a row é uma linha de cabeçalho repetida."""
    values = []
    for canon_key, col_name in col_map.items():
        if col_name is not None and col_name in row.index:
            values.append(_normalize_header(str(row[col_name])))

    header_keywords = [
        "servico", "acao", "produto", "eixo", "area", "responsavel",
        "dtpactuada", "dtentrega", "pactuado", "justificativa",
        "data", "prazo",
    ]
    hits = sum(1 for v in values if any(kw in v for kw in header_keywords))
    return hits >= 2


def extract_entregas_tables(
    pdf_path: str, sigla: str
) -> Tuple[List[DeliveryEntry], List[ProcessingError]]:
    """Extrai tabelas de entregas de um Anexo de Entregas.

    Args:
        pdf_path: Caminho do PDF de entregas.
        sigla: Sigla do órgão.

    Returns:
        (lista de DeliveryEntry, lista de ProcessingError)
    """
    entries: List[DeliveryEntry] = []
    errors: List[ProcessingError] = []

    def _try_extract(conv: DocumentConverter) -> Tuple[List[DeliveryEntry], bool]:
        """Tenta extrair com um conversor. Retorna (entries, found_any_table)."""
        result = conv.convert(pdf_path)

        # Detectar formato legado (EGD 2020-2022)
        legacy = detect_legacy_format(result)
        if legacy:
            logger.info(f"[{sigla}] Formato legado detectado ({legacy}) — tabelas podem diferir do padrão")
            errors.append(ProcessingError(
                orgao_sigla=sigla,
                document_type="entregas",
                stage="extraction",
                error_type="legacy_format",
                error_message=f"Formato legado {legacy}: estrutura pode diferir do template atual",
            ))

        local_entries: List[DeliveryEntry] = []
        found_any = False

        for table in result.document.tables:
            try:
                df = table.export_to_dataframe()
            except Exception as exc:
                logger.warning(f"[{sigla}] Falha ao exportar tabela de entregas: {exc}")
                continue

            if df is None or df.empty:
                continue

            classification = classify_entregas_table(df)

            if classification == "unknown":
                continue

            found_any = True
            col_map = _map_entregas_columns(df, classification)
            mapped_count = sum(1 for v in col_map.values() if v is not None)

            # Mapear tabela_tipo para valor padronizado
            tipo_map = {
                "pactuadas": "pactuada",
                "concluidas": "concluida",
                "canceladas": "cancelada",
            }
            tabela_tipo = tipo_map.get(classification, classification)

            for idx, row in df.iterrows():
                # Pular linhas de cabeçalho repetidas
                if _is_entregas_header_row(row, col_map):
                    continue

                # Extrair valores
                servico_raw = _clean_cell(
                    row.get(col_map["servico_acao"]) if col_map["servico_acao"] else None
                )
                produto_raw = _clean_cell(
                    row.get(col_map["produto"]) if col_map["produto"] else None
                )
                eixo_raw = _clean_cell(
                    row.get(col_map["eixo"]) if col_map["eixo"] else None
                )
                area_raw = _clean_cell(
                    row.get(col_map["area_responsavel"]) if col_map["area_responsavel"] else None
                )
                dt_pact_raw = _clean_cell(
                    row.get(col_map["data_pactuada"]) if col_map["data_pactuada"] else None
                )
                dt_entr_raw = _clean_cell(
                    row.get(col_map["data_entrega"]) if col_map["data_entrega"] else None
                )
                pactuado_raw = _clean_cell(
                    row.get(col_map["pactuado"]) if col_map["pactuado"] else None
                )
                justif_raw = _clean_cell(
                    row.get(col_map["justificativa"]) if col_map["justificativa"] else None
                )

                # Pular linhas completamente vazias
                if not servico_raw and not produto_raw and not eixo_raw:
                    continue

                # Normalizar produto e eixo
                produto_norm = ""
                produto_score = 0.0
                if produto_raw:
                    produto_norm, produto_score = fuzzy_match_produto(produto_raw)

                eixo_norm = ""
                eixo_score = 0.0
                if eixo_raw:
                    eixo_norm, eixo_score = fuzzy_match_eixo(eixo_raw)

                # Se eixo não veio no texto mas o produto foi normalizado, inferir
                if not eixo_norm and produto_norm and produto_score >= 0.80:
                    eixo_norm = PRODUTO_TO_EIXO.get(produto_norm, "")

                # Parsear datas
                dt_pactuada = parse_date(dt_pact_raw) if dt_pact_raw else None
                dt_entrega = parse_date(dt_entr_raw) if dt_entr_raw else None

                # Normalizar pactuado (Sim/Não)
                pactuado_final = None
                if pactuado_raw:
                    p_lower = pactuado_raw.lower().strip()
                    if p_lower in ("sim", "s", "yes", "x"):
                        pactuado_final = "Sim"
                    elif p_lower in ("nao", "não", "n", "no"):
                        pactuado_final = "Não"
                    else:
                        pactuado_final = pactuado_raw

                # Determinar confiança
                review_reasons = []
                if produto_raw and produto_score < 0.70:
                    review_reasons.append(f"produto não mapeado: '{produto_raw}'")
                if eixo_raw and eixo_score < 0.70 and not eixo_norm:
                    review_reasons.append(f"eixo não mapeado: '{eixo_raw}'")
                if not servico_raw and not produto_raw:
                    review_reasons.append("serviço e produto vazios")

                if mapped_count >= 4 and not review_reasons:
                    confidence = "high"
                elif mapped_count >= 3 and len(review_reasons) <= 1:
                    confidence = "medium"
                else:
                    confidence = "low"

                entry = DeliveryEntry(
                    orgao_sigla=sigla,
                    tabela_tipo=tabela_tipo,
                    servico_acao=servico_raw,
                    produto_original=produto_raw,
                    produto_normalizado=produto_norm if produto_score >= 0.70 else "",
                    eixo_original=eixo_raw,
                    eixo_normalizado=eixo_norm,
                    area_responsavel=area_raw if area_raw else None,
                    data_pactuada=dt_pactuada,
                    data_entrega=dt_entrega,
                    pactuado=pactuado_final,
                    justificativa=justif_raw if justif_raw else None,
                    extraction_confidence=confidence,
                    needs_review=len(review_reasons) > 0,
                    review_reason="; ".join(review_reasons) if review_reasons else None,
                )
                local_entries.append(entry)

        return local_entries, found_any

    # Tentativa principal: modo ACCURATE
    try:
        entries, found = _try_extract(converter_accurate)
        if not found:
            logger.info(
                f"[{sigla}] Nenhuma tabela de entregas no modo ACCURATE, tentando FAST..."
            )
            converter_fast = create_converter(accurate=False, ocr=True)
            entries, found = _try_extract(converter_fast)
            if not found:
                errors.append(ProcessingError(
                    orgao_sigla=sigla,
                    document_type="entregas",
                    stage="extraction",
                    error_type="no_entregas_table",
                    error_message=(
                        f"Nenhuma tabela de entregas encontrada em "
                        f"{os.path.basename(pdf_path)}"
                    ),
                ))
    except Exception as exc:
        logger.warning(f"[{sigla}] ACCURATE falhou em entregas: {exc}. Tentando FAST...")
        try:
            converter_fast = create_converter(accurate=False, ocr=True)
            entries, found = _try_extract(converter_fast)
            if not found:
                errors.append(ProcessingError(
                    orgao_sigla=sigla,
                    document_type="entregas",
                    stage="extraction",
                    error_type="no_entregas_table",
                    error_message=(
                        f"Nenhuma tabela de entregas encontrada (modo FAST) em "
                        f"{os.path.basename(pdf_path)}"
                    ),
                ))
        except Exception as exc2:
            errors.append(ProcessingError(
                orgao_sigla=sigla,
                document_type="entregas",
                stage="extraction",
                error_type="docling_failure",
                error_message=f"Docling falhou em ambos os modos: {exc2}",
            ))

    return entries, errors


# --------------- Extração em lote -----------------------------

def extract_all_deliveries() -> None:
    """Extrai tabelas de entregas de todos os órgãos com Anexo de Entregas."""
    global all_deliveries, all_errors

    # Tentar carregar checkpoint (só usa se tiver dados reais)
    cached = load_checkpoint("deliveries_raw")
    if cached is not None and len(cached[0]) > 0:
        cached_deliveries, cached_errors, processed_siglas = cached
        all_deliveries.extend(cached_deliveries)
        all_errors.extend(cached_errors)
        print(
            f"  Retomando: {len(cached_deliveries)} entregas já extraídas "
            f"de {len(processed_siglas)} órgãos"
        )
    else:
        cached_deliveries = []
        cached_errors = []
        processed_siglas = set()

    # Órgãos com PDF de entregas
    organs_with_pdf = [o for o in all_organs if o.pdf_path_entregas]
    pending = [o for o in organs_with_pdf if o.sigla not in processed_siglas]

    if not pending:
        print("  Todos os órgãos já processados (checkpoint).")
        return

    print(
        f"  Processando entregas: {len(pending)} órgãos pendentes "
        f"({len(processed_siglas)} já processados)"
    )

    # Cache de resultados por PDF (para órgãos agrupados com PDF compartilhado)
    pdf_results_cache: Dict[str, Tuple[List[DeliveryEntry], List[ProcessingError]]] = {}

    batch_deliveries: List[DeliveryEntry] = []
    batch_errors: List[ProcessingError] = []
    count = 0

    for organ in tqdm(pending, desc="Extraindo entregas"):
        sigla = organ.sigla
        pdf_path = organ.pdf_path_entregas

        if not os.path.isfile(pdf_path):
            err = ProcessingError(
                orgao_sigla=sigla,
                document_type="entregas",
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
            cached_entries, cached_errs = pdf_results_cache[real_path]
            for entry in cached_entries:
                new_entry = DeliveryEntry(
                    orgao_sigla=sigla,
                    tabela_tipo=entry.tabela_tipo,
                    servico_acao=entry.servico_acao,
                    produto_original=entry.produto_original,
                    produto_normalizado=entry.produto_normalizado,
                    eixo_original=entry.eixo_original,
                    eixo_normalizado=entry.eixo_normalizado,
                    area_responsavel=entry.area_responsavel,
                    data_pactuada=entry.data_pactuada,
                    data_entrega=entry.data_entrega,
                    pactuado=entry.pactuado,
                    justificativa=entry.justificativa,
                    extraction_confidence=entry.extraction_confidence,
                    needs_review=entry.needs_review,
                    review_reason=entry.review_reason,
                )
                batch_deliveries.append(new_entry)
                all_deliveries.append(new_entry)
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
            entries, errs = extract_entregas_tables(pdf_path, sigla)
            pdf_results_cache[real_path] = (entries, errs)

            batch_deliveries.extend(entries)
            all_deliveries.extend(entries)
            batch_errors.extend(errs)
            all_errors.extend(errs)
            processed_siglas.add(sigla)

            if entries:
                logger.info(f"[{sigla}] {len(entries)} entregas extraídas")
            else:
                logger.info(f"[{sigla}] Nenhuma entrega extraída")

        count += 1

        # Checkpoint a cada 10 órgãos
        if count % 10 == 0:
            save_checkpoint(
                (
                    cached_deliveries + batch_deliveries,
                    cached_errors + batch_errors,
                    processed_siglas,
                ),
                "deliveries_raw",
            )

    # Checkpoint final
    save_checkpoint(
        (
            cached_deliveries + batch_deliveries,
            cached_errors + batch_errors,
            processed_siglas,
        ),
        "deliveries_raw",
    )
    print(f"  Extração de entregas concluída.")


# --------------- Execução -------------------------------------
extract_all_deliveries()

# Resumo
organs_with_deliveries = set(d.orgao_sigla for d in all_deliveries)
organs_without_deliveries = set(
    o.sigla for o in all_organs if o.pdf_path_entregas
) - organs_with_deliveries
delivery_errors = [
    e for e in all_errors
    if e.document_type == "entregas" and e.stage == "extraction"
]

print(f"\n{'='*60}")
print(f"RESUMO — Extração de Entregas")
print(f"{'='*60}")
print(f"  Total de entregas extraídas: {len(all_deliveries)}")
print(f"  Órgãos com entregas: {len(organs_with_deliveries)}")
print(f"  Órgãos sem entregas: {len(organs_without_deliveries)}")
if organs_without_deliveries:
    print(f"    → {', '.join(sorted(organs_without_deliveries))}")
print(f"  Erros de extração: {len(delivery_errors)}")

# Breakdown por tipo de tabela
tipo_counts = {}
for d in all_deliveries:
    tipo_counts[d.tabela_tipo] = tipo_counts.get(d.tabela_tipo, 0) + 1
print(f"  Por tipo: {tipo_counts}")

needs_review = [d for d in all_deliveries if d.needs_review]
print(f"  Entregas que precisam revisão: {len(needs_review)}")

confidence_counts = {}
for d in all_deliveries:
    confidence_counts[d.extraction_confidence] = (
        confidence_counts.get(d.extraction_confidence, 0) + 1
    )
print(f"  Confiança: {confidence_counts}")
