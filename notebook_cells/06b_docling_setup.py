# ============================================================
# CÉLULA 6 — Configuração do Extrator de Tabelas (PyMuPDF)
# ============================================================

import fitz  # PyMuPDF

# --------------- Classificação de tabelas diretivo ------------

def _normalize_header(text: str) -> str:
    if not isinstance(text, str): return ""
    t = normalize_text(text).lower()
    t = t.replace("- ", "").replace("-\n", "")
    return strip_accents(t)


def classify_diretivo_table(df: pd.DataFrame) -> str:
    if df is None or df.empty: return "unknown"
    ncols = len(df.columns)
    headers = [_normalize_header(str(c)) for c in df.columns]
    first_row = [_normalize_header(str(v)) for v in df.iloc[0]] if len(df) > 0 else []
    combined = " ".join(headers + first_row)

    risk_kw = ["risco", "probabilidade", "impacto", "tratamento", "ocorrer"]
    risk_alt = ["evento", "classificacao", "severidade", "resposta", "acao", "acoes",
                "id do risco", "descricao do risco", "opcao de tratamento"]
    risk_hits = sum(1 for kw in risk_kw if kw in combined)
    risk_alt_hits = sum(1 for kw in risk_alt if kw in combined)

    if risk_hits >= 2 and 3 <= ncols <= 8: return "risk_table"
    if risk_hits >= 1 and risk_alt_hits >= 1 and 3 <= ncols <= 8: return "risk_table"
    if "risco" in combined and "tratamento" in combined and 3 <= ncols <= 8: return "risk_table"

    info_kw = ["orgao", "ministerio", "secretaria", "sigla", "cnpj", "responsavel",
               "gestor", "dirigente", "titular", "instituicao", "vinculacao"]
    if sum(1 for kw in info_kw if kw in combined) >= 2: return "organ_info"

    sig_kw = ["assinatura", "assinado", "data", "nome", "cargo", "cpf"]
    if sum(1 for kw in sig_kw if kw in combined) >= 2 and ncols <= 4: return "signature"

    return "unknown"


def classify_entregas_table(df: pd.DataFrame) -> str:
    if df is None or df.empty: return "unknown"
    headers = [_normalize_header(str(c)) for c in df.columns]
    first_row = [_normalize_header(str(v)) for v in df.iloc[0]] if len(df) > 0 else []
    combined = " ".join(headers + first_row)
    compact = combined.replace(" ", "")

    if "justificativa" in combined: return "canceladas"
    if "dtentrega" in compact or "data entrega" in combined or "data de entrega" in combined: return "concluidas"
    if "pactuado?" in combined or "pactuado ?" in combined: return "concluidas"
    if ("area" in combined and "responsavel" in combined) and "dtpactuada" in compact: return "pactuadas"
    if "dtpactuada" in compact or "data pactuada" in combined: return "pactuadas"
    return "unknown"


def _cols_are_data(df: pd.DataFrame) -> bool:
    """Detecta se find_tables interpretou o 1o risco como header de coluna."""
    if df.shape[1] < 4: return False
    col0 = _normalize_header(str(df.columns[0]))
    if len(col0) < 10 or col0.startswith("risco") or col0.startswith("col") or col0 == "nan":
        return False
    col1 = _normalize_header(str(df.columns[1]))
    scale_vals = ["raro", "pouco provavel", "provavel", "muito provavel", "praticamente certo",
                  "baixo", "medio", "alto", "muito alto", "baixa", "media", "alta"]
    return any(sv in col1 for sv in scale_vals)


def _is_risk_data(df: pd.DataFrame) -> bool:
    """Verifica se uma tabela contém valores de escala de risco (continuação)."""
    if df is None or df.empty or df.shape[1] < 4: return False
    all_text = strip_accents(" ".join(str(v).lower() for v in df.values.flatten()))
    scale_vals = ["raro", "pouco provavel", "provavel", "muito provavel", "praticamente certo",
                  "muito baixo", "baixo", "medio", "alto", "muito alto",
                  "mitigar", "eliminar", "transferir", "aceitar", "baixa", "media", "alta"]
    return sum(1 for sv in scale_vals if sv in all_text) >= 2


def _is_subheader_row(row) -> bool:
    text = strip_accents(" ".join(str(v) for v in row).lower())
    return any(kw in text for kw in ["certo]", "certo ]", "ocorrer", "muito alto]",
               "muito alto ]", "tratamento do risco", "escolher entre"])


def _extract_action_list(doc_text: str) -> dict:
    """Extrai lista 'Referencial para ações de tratamento do risco'."""
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
            if actions: return actions
    return actions


def _resolve_action_refs(acoes_text: str, action_list: dict) -> str:
    """Resolve referências numéricas ('1, 2, 9') para texto completo."""
    if not acoes_text or not action_list: return acoes_text
    refs = re.findall(r'\d+', acoes_text)
    if not refs: return acoes_text
    tokens = re.split(r'[,;\s]+', acoes_text.strip())
    num_tokens = sum(1 for t in tokens if re.match(r'^\d+$', t.strip()))
    if num_tokens / max(len(tokens), 1) < 0.5: return acoes_text
    resolved = [f"{ref}. {action_list[ref]}" for ref in refs if ref in action_list]
    return " | ".join(resolved) if resolved else acoes_text


print("PyMuPDF configurado.")
print("Classificadores de tabelas e funções de extração carregados.")
print(f"Produtos no vocabulário: {len(ALL_PRODUTOS)}")
