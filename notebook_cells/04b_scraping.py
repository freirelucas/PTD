# ============================================================
# CÉLULA 4 — Scraping: Lista de Órgãos e URLs dos PDFs
# ============================================================

def _classify_pdf_link(anchor_text: str) -> Optional[str]:
    """Classifica um link de PDF como 'diretivo' ou 'entregas' pelo texto da âncora."""
    text = normalize_text(anchor_text).lower()
    text_no_accents = strip_accents(text)

    # Documento Diretivo
    diretivo_kw = ["diretivo", "documento diretivo"]
    if any(kw in text_no_accents for kw in diretivo_kw):
        return "diretivo"

    # Anexo de Entregas
    entregas_kw = ["entregas", "anexo de entregas", "anexo entregas"]
    if any(kw in text_no_accents for kw in entregas_kw):
        return "entregas"

    return None


def _parse_sigla_nome(raw_text: str) -> List[Tuple[str, str]]:
    """
    Extrai pares (sigla, nome_completo) de um texto de cabeçalho de órgão.

    Formatos comuns:
      "SIGLA - Nome Completo"
      "SIGLA1 / SIGLA2 - Nome Completo"   (órgãos agrupados)
      "SIGLA – Nome Completo"              (meia-risca)
    """
    text = normalize_text(raw_text)
    if not text:
        return []

    # Separa sigla(s) do nome pelo primeiro traço (- ou –)
    match = re.match(r"^(.+?)\s*[-–]\s*(.+)$", text)
    if not match:
        return []

    sigla_part = match.group(1).strip()
    nome_part = match.group(2).strip()

    # Pode haver múltiplas siglas: "SIGLA1 / SIGLA2"
    siglas = [s.strip() for s in re.split(r"\s*/\s*", sigla_part) if s.strip()]
    # Validação: siglas são uppercase e curtas
    siglas = [s for s in siglas if re.match(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,12}$", s)]

    if not siglas:
        return []

    return [(s, nome_part) for s in siglas]


def scrape_organ_listing(url: str) -> List[OrganInfo]:
    """
    Faz o scraping da página principal do gov.br para extrair a lista
    de órgãos signatários e seus links de PDFs.

    Estratégia:
      1. Encontra todos os links que apontam para PDFs em 'ptds-vigentes/'
      2. Para cada link, localiza o cabeçalho do órgão mais próximo acima
      3. Classifica o link como 'diretivo' ou 'entregas' pelo texto da âncora
      4. Agrupa por sigla, expandindo órgãos que compartilham PDFs
    """
    resp = safe_request(url)
    if resp is None:
        raise RuntimeError(f"Não foi possível acessar {url}")

    soup = BeautifulSoup(resp.content, "html.parser")

    # Encontra a área de conteúdo principal
    content = (
        soup.find("article")
        or soup.find("div", {"id": "content-core"})
        or soup.find("div", class_=re.compile(r"(content|texto|article)", re.I))
        or soup.body
    )
    if content is None:
        raise RuntimeError("Não encontrou área de conteúdo na página")

    # ---- Fase 1: coletar todos os cabeçalhos de órgãos ----
    # Procuramos <strong> ou <b> que contenham padrão "SIGLA - Nome"
    organ_headers = []   # [(element, [(sigla, nome)])]
    for tag in content.find_all(["strong", "b"]):
        raw = tag.get_text(separator=" ", strip=True)
        parsed = _parse_sigla_nome(raw)
        if parsed:
            organ_headers.append((tag, parsed))

    # ---- Fase 2: coletar todos os links de PDF ----
    pdf_links = []   # [(element, href, doc_type)]
    for a_tag in content.find_all("a", href=True):
        href = a_tag["href"]
        if "ptds-vigentes/" not in href:
            continue
        if not href.lower().endswith(".pdf"):
            continue
        anchor_text = a_tag.get_text(separator=" ", strip=True)
        doc_type = _classify_pdf_link(anchor_text)
        if doc_type is None:
            # Tentativa pelo nome do arquivo
            fname_lower = href.rsplit("/", 1)[-1].lower()
            if "diretivo" in fname_lower:
                doc_type = "diretivo"
            elif "entregas" in fname_lower or "anexo" in fname_lower:
                doc_type = "entregas"
            else:
                # Default heuristic: primeiro link = diretivo, segundo = entregas
                doc_type = "unknown"
        # Converte URL relativa para absoluta
        if href.startswith("/"):
            href = "https://www.gov.br" + href
        pdf_links.append((a_tag, href, doc_type))

    logger.info(f"Encontrados {len(organ_headers)} cabeçalhos de órgãos e {len(pdf_links)} links de PDF")

    # ---- Fase 3: associar cada PDF ao órgão mais próximo acima ----
    # Obtemos posição de cada elemento na árvore linearizada
    all_elements = list(content.descendants)

    def _element_index(el):
        """Retorna o índice do elemento na lista linearizada de descendentes."""
        try:
            # Percorre para cima até encontrar o próprio elemento ou um ancestral direto
            for idx, node in enumerate(all_elements):
                if node is el:
                    return idx
        except Exception:
            pass
        return -1

    # Cache de posições
    header_positions = []
    for tag, parsed in organ_headers:
        idx = _element_index(tag)
        header_positions.append((idx, parsed))

    # Ordena por posição
    header_positions.sort(key=lambda x: x[0])

    # Para cada link PDF, encontra o cabeçalho imediatamente anterior
    organ_data: Dict[str, Dict[str, Optional[str]]] = {}
    # sigla → {"nome": ..., "url_diretivo": ..., "url_entregas": ...}

    for a_tag, href, doc_type in pdf_links:
        link_idx = _element_index(a_tag)

        # Encontra o cabeçalho mais próximo antes deste link
        best_header = None
        for h_idx, parsed in header_positions:
            if h_idx <= link_idx:
                best_header = parsed
            else:
                break

        if best_header is None:
            logger.warning(f"PDF sem órgão associado: {href}")
            continue

        # Registra para todas as siglas desse cabeçalho
        for sigla, nome in best_header:
            if sigla not in organ_data:
                organ_data[sigla] = {"nome": nome, "url_diretivo": None, "url_entregas": None}

            if doc_type == "diretivo":
                organ_data[sigla]["url_diretivo"] = href
            elif doc_type == "entregas":
                organ_data[sigla]["url_entregas"] = href
            elif doc_type == "unknown":
                # Primeiro desconhecido vai para diretivo, segundo para entregas
                if organ_data[sigla]["url_diretivo"] is None:
                    organ_data[sigla]["url_diretivo"] = href
                elif organ_data[sigla]["url_entregas"] is None:
                    organ_data[sigla]["url_entregas"] = href

    # ---- Fase 4: expandir órgãos agrupados ----
    # Órgãos membros de um grupo herdam os PDFs da sigla-cabeça
    expanded: Dict[str, Dict[str, Optional[str]]] = dict(organ_data)

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
                    # Preenche URLs ausentes com as do cabeça do grupo
                    if expanded[member]["url_diretivo"] is None:
                        expanded[member]["url_diretivo"] = head_info["url_diretivo"]
                    if expanded[member]["url_entregas"] is None:
                        expanded[member]["url_entregas"] = head_info["url_entregas"]

    # ---- Fase 5: construir lista de OrganInfo ----
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


# ---- Execução ----
_cached = load_checkpoint("organ_listing")
if _cached is not None:
    all_organs = _cached
    print(f"Carregado do checkpoint: {len(all_organs)} órgãos")
else:
    print("Fazendo scraping da página principal...")
    all_organs = scrape_organ_listing(BASE_URL)
    save_checkpoint(all_organs, "organ_listing")

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
    print(f"  ATENÇÃO: esperados ~91 órgãos, encontrados {_n_total}")
else:
    print(f"  Contagem dentro do esperado (~91)")
print(f"  Com Documento Diretivo:    {_n_diretivo}")
print(f"  Com Anexo de Entregas:     {_n_entregas}")
print(f"  Com ambos:                 {_n_ambos}")
print(f"  Sem nenhum PDF:            {_n_nenhum}")
print(f"  Membros de grupo:          {_n_grupos}")
print(f"{'='*50}")

# Lista órgãos sem PDFs para revisão
if _n_nenhum > 0:
    print("\nÓrgãos SEM nenhum PDF:")
    for o in all_organs:
        if not o.url_diretivo and not o.url_entregas:
            print(f"  - {o.sigla} ({o.nome_completo})")

# Amostra
print("\nAmostra (primeiros 5):")
for o in all_organs[:5]:
    print(f"  {o.sigla:12s} | dir={'Sim' if o.url_diretivo else '---'} "
          f"| ent={'Sim' if o.url_entregas else '---'} "
          f"| grupo={o.grupo or '—'}")