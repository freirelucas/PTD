#!/usr/bin/env python3
"""S1 spike — extrai a prosa dos PDFs diretivos e segmenta em blocos temáticos.

Estratégia (v2 — pós-diagnóstico AEB):
  1. Texto por página via `get_text("dict")` com bbox POR LINHA. Linhas cujo
     centro cai dentro do bbox de uma tabela CLASSIFICADA (risco ou
     info-de-contato) são excluídas — exclusão geométrica por bloco engolia
     headings vizinhos.
  2. Lixo de página removido: "Versão do modelo: X" (capturado como metadado),
     marcadores "N / M" e linhas repetidas em ≥40% das páginas (cabeçalho/
     rodapé institucional).
  3. Páginas com quase nenhum texto → diretivo escaneado (sem OCR, excluído).
  4. Headings por fuzzy match (difflib) contra âncoras da minuta v2.2,
     tolerante a prefixo numérico ("1. ESCOPO", "3 - EIXOS"). Páginas com ≥3
     âncoras distintas = sumário → ignoradas.
  5. Texto entre âncoras consecutivas = bloco da seção.

Saídas (ptd_output/text/):
  directive_text.json       {sigla: {"pages", "is_scanned", "model_version"}}
  directive_blocks.json     {sigla: {section_key: text}}
  segmentation_report.json  cobertura por órgão/seção
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import unicodedata
from collections import Counter

import fitz

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(REPO, "ptd_output", "pdfs", "diretivo")
TEMPLATE_JSON = os.path.join(REPO, "ptd_output", "template",
                             "directive_template_blocks.json")
OUT_DIR = os.path.join(REPO, "ptd_output", "text")

MIN_CHARS_PER_PAGE = 120
SCANNED_RATIO = 0.6
FUZZY_HEADING = 0.82
MAX_HEADING_LEN = 100
FURNITURE_PAGE_FRAC = 0.4      # linha em ≥40% das páginas = cabeçalho/rodapé

RISK_KW = ["probabilidade", "impacto", "tratamento", "risco"]
CONTACT_KW = ["gerente de relacionamento", "telefone", "e mail", "email",
              "lider do plano", "ponto focal", "cnpj", "orgao proponente"]

MODEL_VERSION_RE = re.compile(r"vers[aã]o do modelo\s*[:\-]?\s*([\d.]+)",
                              re.IGNORECASE)
PAGENUM_RE = re.compile(r"^\d+\s*/\s*\d+$")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    s = strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_heading(line: str) -> str:
    t = norm(line)
    t = re.sub(r"^\d+\s*", "", t)
    t = re.sub(r"\s+\d+$", "", t)
    return t


def load_sections():
    with open(TEMPLATE_JSON, encoding="utf-8") as fh:
        return json.load(fh)["sections"]


def _excluded_table_rects(page) -> list:
    """Bboxes de tabelas de risco/contato — as únicas excluídas da prosa."""
    rects = []
    try:
        tabs = page.find_tables()
    except Exception:
        return rects
    page_h = page.rect.height or 1
    for t in tabs.tables:
        try:
            cells = t.extract()
        except Exception:
            continue
        rect = fitz.Rect(t.bbox)
        text = norm(" ".join(str(c) for row in cells for c in row if c))
        n_risk = sum(1 for kw in RISK_KW if kw in text)
        n_contact = sum(1 for kw in CONTACT_KW if kw in text)
        # find_tables produz falsos positivos que cobrem a página inteira e
        # engolem prosa (caso AEB p.2). Tabela de contato é sempre baixa;
        # tabela de risco exige >=3 dos 4 keywords no conteúdo.
        is_contact = n_contact >= 2 and rect.height < 0.4 * page_h
        is_risk = n_risk >= 3
        if is_risk or is_contact:
            rects.append(rect)
    return rects


def extract_pages(pdf_path: str):
    """Linhas de prosa por página (exclui linhas dentro de tabelas risco/contato)."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        excluded = _excluded_table_rects(page)
        lines = []
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for ln in block.get("lines", []):
                bbox = fitz.Rect(ln["bbox"])
                center = fitz.Point((bbox.x0 + bbox.x1) / 2,
                                    (bbox.y0 + bbox.y1) / 2)
                if any(r.contains(center) for r in excluded):
                    continue
                text = "".join(sp["text"] for sp in ln.get("spans", [])).strip()
                if text:
                    lines.append(text)
        pages.append(lines)
    doc.close()
    return pages


def strip_furniture(pages):
    """Remove cabeçalho/rodapé repetido e marcadores de página; captura versão."""
    model_version = None
    counts = Counter()
    for lines in pages:
        for l in set(norm(x) for x in lines if x.strip()):
            counts[l] += 1
    n_pages = max(len(pages), 1)
    furniture = {l for l, c in counts.items()
                 if c >= max(3, FURNITURE_PAGE_FRAC * n_pages)}

    clean = []
    for lines in pages:
        keep = []
        for l in lines:
            m = MODEL_VERSION_RE.search(l)
            if m:
                model_version = model_version or m.group(1)
                continue
            if PAGENUM_RE.match(l.strip()):
                continue
            if norm(l) in furniture and len(l) < 80:
                continue
            keep.append(l)
        clean.append(keep)
    return clean, model_version


def find_anchors(pages, sections):
    per_page = []       # (pi, li, key, raw_line)
    for pi, lines in enumerate(pages):
        for li, line in enumerate(lines):
            if not line or len(line) > MAX_HEADING_LEN:
                continue
            h = norm_heading(line)
            if len(h) < 8:
                continue
            for sec in sections:
                hit = False
                for anchor in sec["anchors"]:
                    if h == anchor or h.startswith(anchor) or \
                       difflib.SequenceMatcher(None, h, anchor).ratio() >= FUZZY_HEADING:
                        hit = True
                        break
                if hit:
                    per_page.append((pi, li, sec["key"], line))
                    break

    # Sumário: ≥3 âncoras distintas na página E a página parece TOC de fato
    # (linhas com nº de página no fim / dot leaders, ou página com pouco
    # texto). Seções curtas legitimamente põem 3 headings na mesma página
    # (caso CONAB) — não podem ser descartadas.
    page_keys, page_anchor_lines = {}, {}
    for pi, li, key, raw in per_page:
        page_keys.setdefault(pi, set()).add(key)
        page_anchor_lines.setdefault(pi, []).append(raw)
    toc_pages = set()
    for pi, keys in page_keys.items():
        if len(keys) < 3:
            continue
        raws = page_anchor_lines[pi]
        n_toclike = sum(1 for r in raws
                        if re.search(r"(\.{3,}|\s\d{1,3})\s*$", r.strip()))
        page_words = sum(len(l.split()) for l in pages[pi])
        if n_toclike >= len(raws) / 2 or page_words < 150:
            toc_pages.add(pi)
    anchors = [(pi, li, k) for pi, li, k, _ in per_page if pi not in toc_pages]

    seen = {}
    for pi, li, key in sorted(anchors):
        if key not in seen:
            seen[key] = (pi, li)
    return seen, toc_pages


def segment(pages, sections):
    seen, toc_pages = find_anchors(pages, sections)
    if not seen:
        return {}, toc_pages

    marks = sorted((pi, li, key) for key, (pi, li) in seen.items())
    flat = [(pi, li, l) for pi, lines in enumerate(pages)
            for li, l in enumerate(lines)]
    pos = {(pi, li): n for n, (pi, li, _) in enumerate(flat)}

    blocks = {}
    for k, (pi, li, key) in enumerate(marks):
        start = pos[(pi, li)] + 1
        end = pos[marks[k + 1][:2]] if k + 1 < len(marks) else len(flat)
        blocks[key] = "\n".join(l for _, _, l in flat[start:end]).strip()
    return blocks, toc_pages


def main() -> int:
    sections = load_sections()
    os.makedirs(OUT_DIR, exist_ok=True)

    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.endswith("_diretivo.pdf"))
    all_text, all_blocks = {}, {}
    report = {"orgaos": {}, "scanned": [], "no_anchors": []}

    for fname in pdfs:
        sigla = fname.replace("_diretivo.pdf", "")
        try:
            raw_pages = extract_pages(os.path.join(PDF_DIR, fname))
        except Exception as exc:
            report["orgaos"][sigla] = {"error": f"{type(exc).__name__}: {exc}"}
            continue

        pages, model_version = strip_furniture(raw_pages)
        page_texts = ["\n".join(ls) for ls in pages]
        n_empty = sum(1 for p in page_texts if len(p.strip()) < MIN_CHARS_PER_PAGE)
        is_scanned = bool(page_texts) and n_empty / len(page_texts) >= SCANNED_RATIO

        all_text[sigla] = {"pages": page_texts, "is_scanned": is_scanned,
                           "n_pages": len(page_texts),
                           "model_version": model_version}
        if is_scanned:
            report["scanned"].append(sigla)
            report["orgaos"][sigla] = {"scanned": True, "n_pages": len(page_texts)}
            continue

        blocks, toc_pages = segment(pages, sections)
        all_blocks[sigla] = blocks
        report["orgaos"][sigla] = {
            "n_pages": len(page_texts),
            "model_version": model_version,
            "toc_pages": sorted(toc_pages),
            "sections_found": sorted(blocks.keys()),
            "n_sections": len(blocks),
            "words_per_section": {k: len(v.split()) for k, v in blocks.items()},
        }
        if not blocks:
            report["no_anchors"].append(sigla)

    keys = [s["key"] for s in sections]
    coverage = {k: sum(1 for b in all_blocks.values() if k in b) for k in keys}
    report["summary"] = {
        "n_pdfs": len(pdfs),
        "n_scanned": len(report["scanned"]),
        "n_no_anchors": len(report["no_anchors"]),
        "n_4plus_sections": sum(1 for b in all_blocks.values() if len(b) >= 4),
        "n_6_sections": sum(1 for b in all_blocks.values() if len(b) == 6),
        "coverage_por_secao": coverage,
        "model_versions": dict(Counter(
            v["model_version"] for v in all_text.values()
            if v.get("model_version"))),
    }

    with open(os.path.join(OUT_DIR, "directive_text.json"), "w",
              encoding="utf-8") as fh:
        json.dump(all_text, fh, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "directive_blocks.json"), "w",
              encoding="utf-8") as fh:
        json.dump(all_blocks, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "segmentation_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"escaneados: {report['scanned']}")
    print(f"sem âncoras: {report['no_anchors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
