# ============================================================
# CÉLULA 6 — Configuração do Docling e Classificação de Tabelas
# ============================================================

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

# --------------- Criação do conversor -------------------------

def create_converter(accurate: bool = True, ocr: bool = True) -> DocumentConverter:
    """Cria um DocumentConverter configurado para extração de tabelas.

    Args:
        accurate: Se True usa TableFormerMode.ACCURATE; senão FAST.
        ocr: Se True habilita OCR para PDFs escaneados.

    Returns:
        DocumentConverter pronto para uso.
    """
    pipeline_opts = PdfPipelineOptions()
    pipeline_opts.do_table_structure = True
    pipeline_opts.table_structure_options.mode = (
        TableFormerMode.ACCURATE if accurate else TableFormerMode.FAST
    )

    # OCR
    pipeline_opts.do_ocr = ocr

    # Desabilita features desnecessárias (compatível com diferentes versões do docling)
    for attr in ["generate_picture_images", "do_picture_description",
                 "do_picture_classification", "do_code_enrichment",
                 "do_formula_enrichment"]:
        if hasattr(pipeline_opts, attr):
            setattr(pipeline_opts, attr, False)

    format_options = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts),
    }

    return DocumentConverter(format_options=format_options)


# --------------- Classificação de tabelas diretivo ------------

def _normalize_header(text: str) -> str:
    """Normaliza texto de cabeçalho para comparação: minúscula, sem acentos, sem espaços extras."""
    if not isinstance(text, str):
        return ""
    t = normalize_text(text).lower()
    return strip_accents(t)


def classify_diretivo_table(df: pd.DataFrame) -> str:
    """Classifica uma tabela extraída de Documento Diretivo.

    Returns:
        'risk_table' — tabela de riscos e tratamento
        'organ_info' — informações institucionais
        'signature'  — bloco de assinaturas
        'unknown'    — não classificada
    """
    if df is None or df.empty:
        return "unknown"

    ncols = len(df.columns)
    headers = [_normalize_header(str(c)) for c in df.columns]
    # Também verificar a primeira linha caso os headers sejam genéricos (0,1,2...)
    first_row_headers = []
    if len(df) > 0:
        first_row_headers = [_normalize_header(str(v)) for v in df.iloc[0]]

    all_headers = headers + first_row_headers

    combined = " ".join(all_headers)

    # --- Tabela de riscos: espera 4-6 colunas com keywords específicas ---
    risk_keywords = ["risco", "probabilidade", "impacto", "tratamento"]
    risk_alt_keywords = ["evento", "classificacao", "severidade", "resposta", "acao", "acoes"]
    risk_hits = sum(1 for kw in risk_keywords if kw in combined)
    risk_alt_hits = sum(1 for kw in risk_alt_keywords if kw in combined)

    if risk_hits >= 2 and 3 <= ncols <= 8:
        return "risk_table"
    if risk_hits >= 1 and risk_alt_hits >= 1 and 3 <= ncols <= 8:
        return "risk_table"

    # --- Informações do órgão: keywords institucionais ---
    info_keywords = [
        "orgao", "ministerio", "secretaria", "sigla", "cnpj",
        "responsavel", "gestor", "dirigente", "titular", "autoridade",
        "instituicao", "vinculacao",
    ]
    info_hits = sum(1 for kw in info_keywords if kw in combined)
    if info_hits >= 2:
        return "organ_info"

    # --- Bloco de assinatura ---
    sig_keywords = ["assinatura", "assinado", "data", "nome", "cargo", "cpf"]
    sig_hits = sum(1 for kw in sig_keywords if kw in combined)
    if sig_hits >= 2 and ncols <= 4:
        return "signature"

    return "unknown"


# --------------- Classificação de tabelas entregas ------------

def classify_entregas_table(df: pd.DataFrame) -> str:
    """Classifica uma tabela extraída de Anexo de Entregas.

    Returns:
        'pactuadas'   — entregas pactuadas (agendadas)
        'concluidas'  — entregas concluídas
        'canceladas'  — entregas canceladas
        'unknown'     — não classificada
    """
    if df is None or df.empty:
        return "unknown"

    headers = [_normalize_header(str(c)) for c in df.columns]
    first_row_headers = []
    if len(df) > 0:
        first_row_headers = [_normalize_header(str(v)) for v in df.iloc[0]]

    all_headers = headers + first_row_headers
    combined = " ".join(all_headers)

    has_area_resp = any(
        "area" in h and "responsavel" in h for h in all_headers
    ) or "area responsavel" in combined or "arearesponsavel" in combined.replace(" ", "")

    has_dt_pactuada = (
        "dtpactuada" in combined.replace(" ", "")
        or "data pactuada" in combined
        or "dt pactuada" in combined
        or "datapactuada" in combined.replace(" ", "")
    )

    has_dt_entrega = (
        "dtentrega" in combined.replace(" ", "")
        or "data entrega" in combined
        or "dt entrega" in combined
        or "dataentrega" in combined.replace(" ", "")
        or "data de entrega" in combined
    )

    has_pactuado_flag = (
        "pactuado?" in combined
        or "pactuado ?" in combined
        or ("pactuado" in combined and ("sim" in combined or "nao" in combined))
    )

    has_justificativa = (
        "justificativa" in combined
        or "motivo" in combined and "cancelamento" in combined
    )

    # Classificação por prioridade (canceladas são mais restritivas)
    # Canceladas: tem Justificativa
    if has_justificativa:
        return "canceladas"

    # Concluídas: tem DtEntrega ou coluna "Pactuado?"
    if has_dt_entrega or has_pactuado_flag:
        return "concluidas"

    # Pactuadas: tem Area Responsável E DtPactuada
    if has_area_resp and has_dt_pactuada:
        return "pactuadas"

    # Fallback: se tem DtPactuada mas sem Area (layout alternativo)
    if has_dt_pactuada:
        return "pactuadas"

    return "unknown"


# --------------- Detecção de formato legado ---------------------

def detect_legacy_format(result) -> Optional[str]:
    """Detecta se um PDF convertido usa formato legado (pré-EFGD 2024).

    Heurísticas:
      - Presença de seções numeradas como '1 – PUBLICAÇÃO DE SERVIÇOS'
      - Ausência de tabelas com headers padrão (Servico/Acao, Produto, Eixo)
      - Menção a 'EGD', 'SGD/ME', 'formalizado no SEI'

    Returns:
        'legacy_egd2020' se formato antigo detectado, None se formato atual.
    """
    try:
        doc_text = result.document.export_to_markdown()[:5000].lower()
    except Exception:
        return None

    legacy_signals = [
        "publicação de serviços no portal gov.br",
        "transformação digital dos serviços no portal gov.br",
        "quantitativo de serviços por solução tecnológica",
        "formalizado no sei",
        "sgd/me",
        "egd 2020",
        "ações do plano anterior",
    ]
    hits = sum(1 for s in legacy_signals if s in doc_text)

    # Se encontrou 2+ sinais legados E não tem headers padrão de tabela
    standard_signals = ["servico/acao", "produto", "dtpactuada", "anexo de entregas"]
    std_hits = sum(1 for s in standard_signals if s in doc_text)

    if hits >= 2 and std_hits < 2:
        return "legacy_egd2020"
    return None


# --------------- Instância default ----------------------------

converter_accurate = create_converter(accurate=True, ocr=True)

print("Docling configurado (modo ACCURATE + OCR).")
print("Classificadores de tabelas carregados.")
print(f"Produtos no vocabulário: {len(ALL_PRODUTOS)} ({len(CANONICAL_PRODUTOS)} canônicos + {len(LEGACY_PRODUTOS)} eixos legados)")
print(f"Aliases de produto: {len(PRODUTO_ALIASES)}")
print(f"Aliases de eixo: {len(EIXO_ALIASES)}")
