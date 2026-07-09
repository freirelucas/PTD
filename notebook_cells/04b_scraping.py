# ============================================================
# CÉLULA 4 — Scraping: Lista de Órgãos e URLs dos PDFs
# ============================================================

def _classify_pdf_link(anchor_text: str) -> Optional[str]:
    """Classifica um link de PDF como 'diretivo' ou 'entregas' pelo texto da âncora."""
    text = normalize_text(anchor_text).lower()
    text_no_accents = strip_accents(text)

    diretivo_kw = ["diretivo", "documento diretivo"]
    if any(kw in text_no_accents for kw in diretivo_kw):
        return "diretivo"

    entregas_kw = ["entregas", "anexo de entregas", "anexo entregas"]
    if any(kw in text_no_accents for kw in entregas_kw):
        return "entregas"

    return None


def _extract_siglas_from_header(header_text: str) -> List[str]:
    """
    Extrai siglas de um cabeçalho como:
      'Plano de Transformação Digital SIGLA:'
      'Plano de Transformação Digital SIGLA1 / SIGLA2 / SIGLA3:'
      'Plano de Transformação Digital CVM -'
    """
    text = normalize_text(header_text)

    # Remove o prefixo "Plano de Transformação Digital"
    prefix_pattern = re.compile(
        r"Plano\s+de\s+Transforma[çc][ãa]o\s+Digital\s*", re.IGNORECASE
    )
    text = prefix_pattern.sub("", text).strip()

    # Remove trailing : ou -
    text = re.sub(r"[\s:–\-]+$", "", text).strip()

    if not text:
        return []

    # Divide por " / " para múltiplas siglas
    parts = [p.strip() for p in re.split(r"\s*/\s*", text) if p.strip()]

    # Filtra: siglas são uppercase (permitem hífen para SG-PR), 2-14 chars
    siglas = []
    for p in parts:
        # Limpa possíveis sufixos ("(NOVO)")
        p = re.sub(r"\s*\(.*?\)\s*", "", p).strip()
        if re.match(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-]{1,14}$", p):
            siglas.append(p)

    return siglas


def scrape_organ_listing(url: str) -> List[OrganInfo]:
    """
    Faz o scraping da página gov.br para extrair órgãos e links de PDFs.

    Estrutura real da página:
      Cada órgão é um <td> contendo:
        <strong>Plano de Transformação Digital SIGLA:</strong>
        <a href="...diretivo.pdf">Documento Diretivo</a> /
        <a href="...entregas.pdf">Anexo de Entregas</a>
    """
    resp = safe_request(url)
    if resp is None:
        raise RuntimeError(f"Não foi possível acessar {url}")

    soup = BeautifulSoup(resp.content, "html.parser")

    # Encontrar todos os <strong> que contêm "Plano de Transformação Digital"
    organ_data: Dict[str, Dict[str, Optional[str]]] = {}
    seen_sigla_sets = set()  # evitar duplicatas

    for strong_tag in soup.find_all(["strong", "b"]):
        raw_text = strong_tag.get_text(separator=" ", strip=True)
        if "transformação digital" not in raw_text.lower() and "transformacao digital" not in raw_text.lower():
            continue

        siglas = _extract_siglas_from_header(raw_text)
        if not siglas:
            continue

        # Evitar processar duplicatas do mesmo grupo
        sigla_key = tuple(sorted(siglas))
        if sigla_key in seen_sigla_sets:
            continue
        seen_sigla_sets.add(sigla_key)

        # Encontrar links PDF no mesmo container (td, p, div, etc.)
        container = strong_tag.parent
        if container is None:
            continue

        pdf_links_in_container = []
        for a_tag in container.find_all("a", href=True):
            href = a_tag["href"]
            if not href.lower().endswith(".pdf"):
                continue
            if "ptds-vigentes/" not in href and "planos-de-transformacao-digital" not in href:
                continue
            anchor_text = a_tag.get_text(separator=" ", strip=True)
            doc_type = _classify_pdf_link(anchor_text)

            # Fallback: classificar pelo nome do arquivo
            if doc_type is None:
                fname = href.rsplit("/", 1)[-1].lower()
                if "diretivo" in fname or "diretiv" in fname:
                    doc_type = "diretivo"
                elif "entregas" in fname or "anexo" in fname:
                    doc_type = "entregas"
                else:
                    doc_type = "unknown"

            # Converter URL relativa para absoluta
            if href.startswith("/"):
                href = "https://www.gov.br" + href

            pdf_links_in_container.append((href, doc_type))

        # Atribuir URLs por tipo
        url_diretivo = None
        url_entregas = None
        for href, doc_type in pdf_links_in_container:
            if doc_type == "diretivo" and url_diretivo is None:
                url_diretivo = href
            elif doc_type == "entregas" and url_entregas is None:
                url_entregas = href
            elif doc_type == "unknown":
                if url_diretivo is None:
                    url_diretivo = href
                elif url_entregas is None:
                    url_entregas = href

        # Registrar para todas as siglas neste header
        for sigla in siglas:
            if sigla not in organ_data:
                organ_data[sigla] = {
                    "nome": raw_text,
                    "url_diretivo": url_diretivo,
                    "url_entregas": url_entregas,
                }

    logger.info(f"Scraping direto: {len(organ_data)} siglas encontradas")
    return _build_organ_list(organ_data)


def _build_organ_list(organ_data: Dict[str, Dict[str, Optional[str]]]) -> List[OrganInfo]:
    """Expande grupos ministeriais e materializa a lista final de OrganInfo."""
    # Expandir grupos: membros herdam PDFs do cabeça se não tiverem próprios
    expanded = dict(organ_data)
    for head_sigla, members in ORGAN_GROUPS.items():
        if head_sigla in organ_data:
            head_info = organ_data[head_sigla]
            for member in members:
                if member == head_sigla:
                    continue
                if member not in expanded:
                    expanded[member] = {
                        "nome": head_info["nome"],
                        "url_diretivo": head_info["url_diretivo"],
                        "url_entregas": head_info["url_entregas"],
                    }
                else:
                    if expanded[member]["url_diretivo"] is None:
                        expanded[member]["url_diretivo"] = head_info["url_diretivo"]
                    if expanded[member]["url_entregas"] is None:
                        expanded[member]["url_entregas"] = head_info["url_entregas"]

    # Construir lista final
    organs: List[OrganInfo] = []
    for sigla in sorted(expanded.keys()):
        info = expanded[sigla]
        grupo = MEMBER_TO_GROUP.get(sigla)
        organs.append(OrganInfo(
            sigla=sigla,
            nome_completo=info["nome"],
            grupo=grupo,
            url_diretivo=info.get("url_diretivo"),
            url_entregas=info.get("url_entregas"),
        ))

    return organs


# --------- Fallback do defeso eleitoral: listagem paginada -----------
# Durante o defeso a página estruturada some; resta a listagem paginada de
# arquivos em ptds-vigentes?b_start:int=N (20 itens/página), cujos títulos
# são os NOMES DOS ARQUIVOS. Para não envenenar os dados com adivinhação,
# a associação sigla/tipo ancora primeiro no snapshot anterior committado
# (output/organs.csv); heurística de nome só para arquivos novos/renomeados.

def _load_previous_url_map() -> Dict[str, Tuple[str, str]]:
    """basename do PDF → (sigla, tipo) a partir do snapshot output/organs.csv."""
    path = os.path.join(os.getcwd(), "output", "organs.csv")
    mapping: Dict[str, Tuple[str, str]] = {}
    if not os.path.exists(path):
        return mapping
    import csv as _csv
    with open(path, encoding="utf-8-sig") as fh:
        for row in _csv.DictReader(fh):
            for tipo, col in (("diretivo", "url_diretivo"),
                              ("entregas", "url_entregas")):
                url = (row.get(col) or "").strip()
                if url:
                    mapping[url.rsplit("/", 1)[-1].lower()] = (row["sigla"], tipo)
    return mapping


# Tokens genéricos que aparecem como 1º token mas nunca são sigla
_FILENAME_STOPWORDS = {"anexo", "ptd", "novo", "plano", "doc", "documento",
                       "de", "do", "da", "transformacao", "digital"}


def _sigla_tipo_from_filename(fname: str,
                              known_siglas: set) -> Tuple[Optional[str], Optional[str]]:
    """Heurística p/ arquivos fora do snapshot anterior.

    Sigla: (1) qualquer token que seja sigla conhecida (ex.:
    'anexo_de_entregas_-_mt_...' → MT); (2) 1º token que COMEÇA com sigla
    conhecida (concatenações tipo 'mmulheresptd_...' → MMULHERES); (3) 1º
    token plausível fora da stoplist (sigla inédita, vai p/ revisão).
    Tipo: keyword no nome; sem keyword → None (não adivinha).
    """
    stem = fname.lower().replace(".pdf", "")
    tokens = [t for t in re.split(r"[\-_.]+", stem) if t]

    sigla = None
    for t in tokens:
        if t.upper() in known_siglas:
            sigla = t.upper()
            break
    if sigla is None and tokens:
        prefixes = [s for s in known_siglas
                    if len(s) >= 3 and tokens[0].startswith(s.lower())]
        if prefixes:
            sigla = max(prefixes, key=len)
    if sigla is None:
        for t in tokens:
            if t in _FILENAME_STOPWORDS:
                continue
            if re.match(r"^[a-z][a-z0-9]{1,13}$", t):
                sigla = t.upper()
            break

    if "diretiv" in stem:
        tipo = "diretivo"
    elif "entrega" in stem or "anexo" in stem:
        tipo = "entregas"
    else:
        tipo = None
    return sigla, tipo


def scrape_pdf_listing_paginated(base_url: str) -> List[OrganInfo]:
    """Scraping da listagem paginada (modo defeso eleitoral)."""
    prev_map = _load_previous_url_map()
    known_siglas = set(s for s, _ in prev_map.values()) | set(MEMBER_TO_GROUP)
    organ_data: Dict[str, Dict[str, Optional[str]]] = {}
    review: List[str] = []
    seen_hrefs = set()

    for start in range(0, 600, 20):
        page_url = f"{base_url}/ptds-vigentes?b_start:int={start}"
        resp = safe_request(page_url)
        if resp is None:
            break
        soup = BeautifulSoup(resp.content, "html.parser")
        new_links = []
        for a_tag in soup.select(".summary a[href], a.summary[href]"):
            href = a_tag["href"]
            clean = href[:-5] if href.endswith("/view") else href
            if not clean.lower().endswith(".pdf") or "ptds-vigentes" not in clean:
                continue
            if clean in seen_hrefs:
                continue
            seen_hrefs.add(clean)
            new_links.append(clean)
        if not new_links:
            break

        for href in new_links:
            basename = href.rsplit("/", 1)[-1].lower()
            if basename in prev_map:
                sigla, tipo = prev_map[basename]
            else:
                sigla, tipo = _sigla_tipo_from_filename(basename, known_siglas)
                if not sigla or not tipo:
                    review.append(basename)
                    continue
                if sigla not in known_siglas:
                    # Órgão inédito é possível, mas fica sinalizado
                    review.append(f"{basename} (sigla nova: {sigla})")
            entry = organ_data.setdefault(sigla, {
                "nome": f"Plano de Transformação Digital {sigla}",
                "url_diretivo": None, "url_entregas": None,
            })
            key = f"url_{tipo}"
            if entry[key] is None:
                entry[key] = href

    logger.info(f"Listagem paginada: {len(organ_data)} siglas, "
                f"{len(seen_hrefs)} PDFs, {len(review)} p/ revisão")
    if review:
        print(f"  ⚠ {len(review)} arquivos não associados automaticamente:")
        for r in review[:10]:
            print(f"    - {r}")
    return _build_organ_list(organ_data)


# ---- Execução (sempre faz scraping fresco — leva ~3s) ----
# Tenta os candidatos de URL em ordem (portal normal → defeso eleitoral).
# Gate anti-envenenamento: um modo só é aceito com >=60 órgãos com URL;
# se todos falharem, aborta SEM escrever nada (corpus anterior preservado).
MIN_ORGAOS_SCRAPING = 60
all_organs: List[OrganInfo] = []
PORTAL_MODE = None
for _base, _modo in BASE_URL_CANDIDATES:
    print(f"Tentando portal ({_modo}): {_base}")
    try:
        # GET leve (stream, corpo não lido): o WAF do gov.br devolve 403
        # para HEAD mesmo quando o recurso existe.
        _probe = requests.get(_base, headers=HTTP_HEADERS, timeout=30,
                              allow_redirects=True, stream=True)
        _probe.close()
        if _probe.status_code >= 400:
            print(f"  HTTP {_probe.status_code} — próximo candidato")
            continue
    except requests.RequestException as _exc:
        print(f"  {type(_exc).__name__} — próximo candidato")
        continue
    try:
        _organs = (scrape_organ_listing(_base) if _modo == "estruturado"
                   else scrape_pdf_listing_paginated(_base))
    except Exception as _exc:
        logger.warning(f"Modo {_modo} falhou: {_exc}")
        continue
    _com_url = sum(1 for o in _organs if o.url_diretivo or o.url_entregas)
    if _com_url >= MIN_ORGAOS_SCRAPING:
        all_organs, PORTAL_MODE = _organs, _modo
        print(f"Portal em modo '{_modo}': {_com_url} órgãos com URL")
        break
    logger.warning(f"Modo {_modo}: só {_com_url} órgãos com URL "
                   f"(mínimo {MIN_ORGAOS_SCRAPING}) — tentando próximo")

if not all_organs:
    raise RuntimeError(
        "Scraping falhou em todos os candidatos de URL (portal fora do ar ou "
        "estrutura mudou de novo). Abortando SEM escrever dados — o corpus "
        "anterior permanece intacto.")

# ---- Validação e Resumo ----
_n_total = len(all_organs)
_n_diretivo = sum(1 for o in all_organs if o.url_diretivo)
_n_entregas = sum(1 for o in all_organs if o.url_entregas)
_n_ambos = sum(1 for o in all_organs if o.url_diretivo and o.url_entregas)
_n_nenhum = sum(1 for o in all_organs if not o.url_diretivo and not o.url_entregas)
_n_grupos = sum(1 for o in all_organs if o.grupo is not None)

print(f"\n{'='*50}")
print(f"Total de órgãos encontrados: {_n_total}")
if _n_total < 80 or _n_total > 110:
    print(f"  ⚠ ATENÇÃO: esperados ~91 órgãos, encontrados {_n_total}")
else:
    print(f"  ✓ Contagem dentro do esperado (~91)")
print(f"  Com Documento Diretivo:    {_n_diretivo}")
print(f"  Com Anexo de Entregas:     {_n_entregas}")
print(f"  Com ambos:                 {_n_ambos}")
print(f"  Sem nenhum PDF:            {_n_nenhum}")
print(f"  Membros de grupo:          {_n_grupos}")
print(f"{'='*50}")

if _n_nenhum > 0:
    print("\nÓrgãos SEM nenhum PDF:")
    for o in all_organs:
        if not o.url_diretivo and not o.url_entregas:
            print(f"  - {o.sigla}")

print("\nAmostra (primeiros 10):")
for o in all_organs[:10]:
    print(f"  {o.sigla:12s} | dir={'Sim' if o.url_diretivo else '---'} "
          f"| ent={'Sim' if o.url_entregas else '---'} "
          f"| grupo={o.grupo or '—'}")