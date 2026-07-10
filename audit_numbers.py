#!/usr/bin/env python3
"""Auditoria de consistência numérica dos documentos do repo.

Compara os números CANÔNICOS (gerados pelo pipeline em output/) contra os
números citados como texto nos documentos versionados. Falha (exit 1) se
qualquer citação divergir — impede que README/NOTA_TECNICA/CITATION fiquem
defasados após um refresh do corpus.

Regras:
  - Números CORRENTES devem bater com output/statistics_summary.json,
    validation_report.json e directive_text_analysis.json.
  - Números HISTÓRICOS (DECISIONS.md, erratas) são ignorados aqui — a
    convenção é carimbá-los com a data do snapshot ("mai/2026") em vez de
    reescrevê-los.

Uso:
  python audit_numbers.py          # relatório + exit 1 se houver divergência
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    with open(os.path.join(REPO, path), encoding="utf-8") as fh:
        return fh.read()


def canonical() -> dict:
    import csv
    stats = json.loads(_read("output/statistics_summary.json"))
    val = json.loads(_read("output/validation_report.json"))
    txt = json.loads(_read("output/directive_text_analysis.json"))
    cache = json.loads(_read("corpus_pdfs/manifest.json"))
    seg = json.loads(_read("spike_s1/data/segmentation_report.json"))["summary"]

    cov = list(csv.DictReader(
        open(os.path.join(REPO, "output/coverage_summary.csv"),
             encoding="utf-8-sig")))
    n_del_comp = sum(1 for r in cov if r["status_entregas"] == "compartilhado")
    n_risk_comp = sum(1 for r in cov if r["status_riscos"] == "compartilhado")

    return {
        "orgaos": stats["orgaos_total"],
        "entregas": stats["entregas_total"],
        "riscos": stats["riscos_total"],
        "entregas_orgaos": stats["entregas_orgaos"],
        "riscos_orgaos": stats["riscos_orgaos"],
        "entregas_compartilhados": n_del_comp,
        "riscos_compartilhados": n_risk_comp,
        "pdfs_total": stats["pdfs_total"],
        "data_execucao": stats["data_execucao"],
        "counts_val": val["counts"],
        "txt_orgaos_canonicos": len(txt["metricas"]),
        "txt_orgaos_compartilhados": sum(
            len(o["compartilhado_com"]) for o in txt["orgaos"].values()),
        "txt_segmentados": seg["n_4plus_sections"],
        "txt_6_secoes": seg["n_6_sections"],
        "cache_unicos": cache["_stats"]["arquivos_unicos"],
        "cache_orgaos": cache["_stats"]["orgaos"],
    }


# Cada assertiva: (arquivo, regex com UM grupo numérico, chave canônica,
# transformação opcional do valor canônico p/ comparação textual).
def build_assertions(c: dict):
    fmt_milhar = lambda n: f"{n:,}".replace(",", ".")
    return [
        # README — tabela de números-chave
        ("README.md", r"\| Órgãos signatários \| (\d+) \|", c["orgaos"]),
        ("README.md", r"\| Entregas pactuadas \| \*\*([\d.]+)\*\* \|",
         fmt_milhar(c["entregas"])),
        ("README.md", r"\| Riscos identificados \| \*\*([\d.]+)\*\* \|",
         fmt_milhar(c["riscos"])),
        ("README.md", r"Cobertura entregas \| (\d+)/\d+ órgãos",
         c["entregas_orgaos"]),
        ("README.md", r"Cobertura entregas \| \d+/(\d+) órgãos", c["orgaos"]),
        ("README.md", r"Cobertura riscos \| (\d+)/\d+ órgãos",
         c["riscos_orgaos"]),
        ("README.md", r"PTDs de (\d+) órgãos federais brasileiros",
         c["orgaos"]),
        ("README.md", r"(\d+) órgãos federais signatários", c["orgaos"]),
        # CITATION.cff — abstract alimenta o JSON-LD do index.html
        ("CITATION.cff", r"(\d+) órgãos signatários", c["orgaos"]),
        ("CITATION.cff",
         r"PTDs de (\d+) órgãos federais brasileiros", c["orgaos"]),
        # NOTA_TECNICA — números correntes no corpo
        ("NOTA_TECNICA.md", r"snapshot atual cobre \*\*(\d+) órgãos\*\*",
         c["orgaos"]),
        ("NOTA_TECNICA.md", r"\| `output/deliveries.csv` / `.json` \| (\d+) entregas",
         c["entregas"]),
        ("NOTA_TECNICA.md", r"\| `output/risks.csv` / `.json` \| (\d+) riscos",
         c["riscos"]),
        ("NOTA_TECNICA.md", r"\| `output/organs.csv` \| (\d+) órgãos",
         c["orgaos"]),
        # README/NT — coberturas próprias vs compartilhadas
        ("README.md",
         r"Cobertura entregas \| \d+/\d+ órgãos \((\d+) próprios",
         c["entregas_orgaos"] - c["entregas_compartilhados"]),
        ("README.md",
         r"Cobertura riscos \| \d+/\d+ órgãos \((\d+) próprios",
         c["riscos_orgaos"] - c["riscos_compartilhados"]),
        # Cache de PDFs — número de únicos e de órgãos cobertos
        ("README.md", r"\((\d+) únicos, \d+ órgãos\)", c["cache_unicos"]),
        ("README.md", r"\(\d+ únicos, (\d+) órgãos\)", c["cache_orgaos"]),
        ("corpus_pdfs/README.md", r"(\d+) PDFs únicos \(dedup por MD5\)",
         c["cache_unicos"]),
        ("corpus_pdfs/README.md",
         r"PDFs únicos \(dedup por MD5\) cobrindo\n  (\d+) órgãos",
         c["cache_orgaos"]),
        # NT §4.6 — segmentação da prosa
        ("NOTA_TECNICA.md",
         r"(\d+)/\d+ diretivos não escaneados segmentados",
         c["txt_segmentados"]),
        ("NOTA_TECNICA.md",
         r"diretivos não escaneados segmentados, (\d+) com as 6 seções",
         c["txt_6_secoes"]),
    ]


def main() -> int:
    c = canonical()
    problems, checked = [], 0
    for path, pattern, expected in build_assertions(c):
        text = _read(path)
        m = re.search(pattern, text)
        if not m:
            problems.append(f"{path}: padrão não encontrado: /{pattern}/")
            continue
        checked += 1
        found = m.group(1)
        if str(found) != str(expected):
            problems.append(f"{path}: '{found}' ≠ esperado '{expected}' "
                            f"(/{pattern}/)")

    print(f"Canônicos ({c['data_execucao']}): órgãos={c['orgaos']} "
          f"entregas={c['entregas']} riscos={c['riscos']} "
          f"cobertura={c['entregas_orgaos']}/{c['riscos_orgaos']} "
          f"texto={c['txt_orgaos_canonicos']}+{c['txt_orgaos_compartilhados']}")
    if problems:
        print(f"\nDIVERGÊNCIAS ({len(problems)}):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print(f"AUDITORIA OK: {checked} citações numéricas consistentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
