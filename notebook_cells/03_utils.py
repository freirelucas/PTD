# ============================================================
# CÉLULA 3 — Funções Utilitárias
# ============================================================

# --------------- Rede com retry -----------------------------
def safe_request(url: str, max_retries: int = MAX_RETRIES,
                 delay: float = REQUEST_DELAY,
                 timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """GET com retry exponencial e rate-limiting."""
    for attempt in range(1, max_retries + 1):
        try:
            time.sleep(delay)
            resp = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 503 and attempt < max_retries:
                wait = delay * (2 ** attempt)
                print(f"  503 em {url} — retry {attempt}/{max_retries} em {wait:.0f}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            if attempt < max_retries:
                wait = delay * (2 ** attempt)
                print(f"  Erro ({exc}) — retry {attempt}/{max_retries} em {wait:.0f}s")
                time.sleep(wait)
            else:
                print(f"  FALHA definitiva: {url} — {exc}")
                return None
    return None

# --------------- Normalização de texto ----------------------
def normalize_text(text: str) -> str:
    """Normaliza unicode, whitespace e caixa para comparação."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text

def strip_accents(text: str) -> str:
    """Remove acentos para matching fuzzy."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

# --------------- Matching fuzzy de vocabulário --------------
def fuzzy_match(original: str, candidates: list,
                threshold: float = 0.85) -> Tuple[str, float]:
    """Retorna (melhor_candidato, score). Score 0 se abaixo do threshold."""
    if not original or not candidates:
        return ("", 0.0)
    norm = normalize_text(original).lower()
    norm_stripped = strip_accents(norm)
    # Tentativa exata (case-insensitive, accent-insensitive)
    for c in candidates:
        c_norm = normalize_text(c).lower()
        if norm == c_norm or norm_stripped == strip_accents(c_norm):
            return (c, 1.0)
    # Fuzzy
    best, best_score = "", 0.0
    for c in candidates:
        c_norm = normalize_text(c).lower()
        score = difflib.SequenceMatcher(None, norm_stripped,
                                        strip_accents(c_norm)).ratio()
        if score > best_score:
            best, best_score = c, score
    if best_score >= threshold:
        return (best, best_score)
    return (best, best_score)   # retorna melhor mesmo abaixo do threshold

def fuzzy_match_produto(original: str) -> Tuple[str, float]:
    """Match produto com: aliases determinísticos → canônicos+legados → fuzzy."""
    if not original:
        return ("", 0.0)
    norm = normalize_text(original)
    # Camada 0: alias determinístico (variações conhecidas)
    for alias_key, canonical_val in PRODUTO_ALIASES.items():
        if normalize_text(alias_key).lower() == norm.lower():
            return (canonical_val, 1.0)
        if strip_accents(normalize_text(alias_key).lower()) == strip_accents(norm.lower()):
            return (canonical_val, 0.98)
    # Camada 1+: match fuzzy contra lista completa (canônicos + legados)
    return fuzzy_match(original, ALL_PRODUTOS, threshold=0.80)

def fuzzy_match_eixo(original: str) -> Tuple[str, float]:
    """Match eixo com: aliases legados → canônicos → fuzzy."""
    if not original:
        return ("", 0.0)
    norm = normalize_text(original)
    # Camada 0: alias legado (eixos EGD 2020-2022 → EFGD 2024)
    for alias_key, canonical_val in EIXO_ALIASES.items():
        if normalize_text(alias_key).lower() == norm.lower():
            return (canonical_val, 0.95)
        if strip_accents(normalize_text(alias_key).lower()) == strip_accents(norm.lower()):
            return (canonical_val, 0.93)
    return fuzzy_match(original, CANONICAL_EIXOS, threshold=0.80)

def fuzzy_match_scale(original: str, scale: list) -> Tuple[str, float]:
    """Canoniza valores de escala (probabilidade/impacto/tratamento) com
    suporte a escalas alternativas usadas por alguns órgãos (ANTAQ 3-pontos,
    SUSEP numérica, CADE mista). Aliases têm prioridade sobre fuzzy match."""
    if not original:
        return ("", 0.0)
    norm = strip_accents(normalize_text(original).lower().strip())
    if scale is PROBABILIDADE_SCALE and norm in PROBABILIDADE_ALIASES:
        return (PROBABILIDADE_ALIASES[norm], 0.95)
    if scale is IMPACTO_SCALE and norm in IMPACTO_ALIASES:
        return (IMPACTO_ALIASES[norm], 0.95)
    if scale is TRATAMENTO_OPTIONS and norm in TRATAMENTO_ALIASES:
        return (TRATAMENTO_ALIASES[norm], 0.95)
    return fuzzy_match(original, scale, threshold=0.70)

# --------------- Parse de datas variadas --------------------
_DATE_PATTERNS = [
    (r"(\d{2})/(\d{2})/(\d{4})", lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),
    (r"(\d{2})/(\d{4})",          lambda m: f"{m.group(2)}-{m.group(1)}"),
    (r"(\d{4})-(\d{2})-(\d{2})",  lambda m: m.group(0)),
]
_MONTH_MAP = {
    "jan": "01", "fev": "02", "mar": "03", "abr": "04",
    "mai": "05", "jun": "06", "jul": "07", "ago": "08",
    "set": "09", "out": "10", "nov": "11", "dez": "12",
}

def parse_date(text: str) -> Optional[str]:
    """Converte formatos variados para YYYY-MM ou YYYY-MM-DD."""
    if not text:
        return None
    text = normalize_text(text).strip()
    for pat, fmt in _DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return fmt(m)
    # Formato "jun/25", "mar/2026"
    m = re.match(r"([a-záéíóú]{3})[\./\-](\d{2,4})", text.lower())
    if m:
        month = _MONTH_MAP.get(m.group(1)[:3])
        year = m.group(2)
        if len(year) == 2:
            year = "20" + year
        if month:
            return f"{year}-{month}"
    return text   # retorna original se não parsear

# --------------- Checkpoint / Resume ------------------------
def save_checkpoint(data: Any, name: str) -> None:
    path = os.path.join(DIRS["checkpoints"], f"{name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)
    print(f"  Checkpoint salvo: {name}")

def load_checkpoint(name: str) -> Optional[Any]:
    path = os.path.join(DIRS["checkpoints"], f"{name}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = pickle.load(f)
        print(f"  Checkpoint carregado: {name}")
        return data
    return None

# --------------- Logging ------------------------------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ptd_scraper")

print("Funções utilitárias carregadas.")