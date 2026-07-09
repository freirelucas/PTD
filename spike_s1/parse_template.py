#!/usr/bin/env python3
"""S1 spike — parseia a minuta oficial do Documento Diretivo (DOCX v2.2) em blocos.

Saída: ptd_output/template/directive_template_blocks.json
  { "template_version": "2.2",
    "sections": [ {"key", "num", "title", "anchors", "text", "n_words"} ] }

Os `anchors` são variantes normalizadas do título usadas depois para segmentar
os PDFs do corpus (tolerantes a prefixo numérico e acentos).
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

import docx

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX_PATH = os.path.join(REPO, "ptd_output", "template", "docdiretivo_minuta_v2-2.docx")
OUT_PATH = os.path.join(REPO, "ptd_output", "template", "directive_template_blocks.json")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    s = strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Seções canônicas da minuta v2.2. O título na capa/PDF costuma vir com
# prefixo "N - "; a numeração no DOCX é automática (numPr), então ancoramos
# no TEXTO. "key" é o identificador estável usado por todo o pipeline.
SECTIONS = [
    {"key": "escopo", "num": 1, "title": "Escopo do Instrumento",
     "match": ["escopo do instrumento"]},
    {"key": "visao", "num": 2, "title": "Visão Estratégica do Órgão",
     "match": ["visao estrategica do orgao relacionada a transformacao digital",
               "visao estrategica do orgao", "visao estrategica"]},
    {"key": "eixos", "num": 3, "title": "Eixos da Transformação Digital",
     "match": ["eixos da transformacao digital", "eixos de transformacao digital"]},
    {"key": "acompanhamento", "num": 4, "title": "Estratégia de Acompanhamento",
     "match": ["estrategia de acompanhamento", "estrategia de monitoramento"]},
    {"key": "riscos", "num": 5, "title": "Gestão de Riscos",
     "match": ["gestao de riscos", "gestao de risco", "gerenciamento de riscos"]},
    {"key": "papeis", "num": 6, "title": "Papéis e Responsabilidades",
     "match": ["papeis e responsabilidades", "papeis e responsabilidade"]},
]


def match_section(text: str):
    """Retorna a seção cujo título casa com `text` (tolerante a prefixo numérico)."""
    t = norm(text)
    t = re.sub(r"^\d+\s*", "", t)  # remove "3 " de "3 eixos da..."
    for sec in SECTIONS:
        for m in sec["match"]:
            if t == m or t.startswith(m):
                return sec
    return None


def main() -> int:
    d = docx.Document(DOCX_PATH)
    blocks = {s["key"]: [] for s in SECTIONS}
    blocks["preambulo"] = []
    current = "preambulo"

    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        sec = match_section(t)
        # Só aceita como heading se for curto (títulos têm < 90 chars)
        if sec and len(t) < 90:
            current = sec["key"]
            continue
        blocks[current].append(t)

    out = {"template_version": "2.2", "source": os.path.basename(DOCX_PATH),
           "sections": []}
    for s in SECTIONS:
        text = "\n".join(blocks[s["key"]])
        out["sections"].append({
            "key": s["key"], "num": s["num"], "title": s["title"],
            "anchors": s["match"], "text": text,
            "n_words": len(text.split()),
        })
    out["preambulo_n_words"] = len(" ".join(blocks["preambulo"]).split())

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    for s in out["sections"]:
        print(f"  [{s['num']}] {s['key']:16s} {s['n_words']:5d} palavras")
    print(f"\npreambulo (capa/descartado): {out['preambulo_n_words']} palavras")
    print(f"OK → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
