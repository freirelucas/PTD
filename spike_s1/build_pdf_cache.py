#!/usr/bin/env python3
"""Monta o cache versionado de PDFs diretivos em corpus_pdfs/.

Dedup por MD5: grupos ministeriais compartilham o mesmo PDF; o arquivo é
gravado uma vez sob a menor sigla (política do pipeline) e o manifest mapeia
TODAS as siglas para o arquivo canônico.

Saídas:
  corpus_pdfs/diretivo/<SIGLA>_diretivo.pdf   (únicos por MD5)
  corpus_pdfs/template/docdiretivo_minuta_v2-2.docx
  corpus_pdfs/manifest.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO, "ptd_output", "pdfs", "diretivo")
SRC_TPL = os.path.join(REPO, "ptd_output", "template",
                       "docdiretivo_minuta_v2-2.docx")
DST = os.path.join(REPO, "corpus_pdfs")
ORGANS_CSV = os.path.join(REPO, "output", "organs.csv")


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    urls = {}
    with open(ORGANS_CSV, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("url_diretivo"):
                urls[r["sigla"]] = r["url_diretivo"]

    pdfs = sorted(f for f in os.listdir(SRC_DIR) if f.endswith("_diretivo.pdf"))
    by_hash = {}
    for f in pdfs:
        sigla = f.replace("_diretivo.pdf", "")
        by_hash.setdefault(md5(os.path.join(SRC_DIR, f)), []).append(sigla)

    os.makedirs(os.path.join(DST, "diretivo"), exist_ok=True)
    os.makedirs(os.path.join(DST, "template"), exist_ok=True)

    manifest = {"_descricao": "Cache dos PDFs 'Documento Diretivo' dos PTDs, "
                              "dedupado por MD5 (grupos ministeriais "
                              "compartilham o mesmo PDF).",
                "template": {"file": "template/docdiretivo_minuta_v2-2.docx",
                             "md5": md5(SRC_TPL)},
                "orgaos": {}}
    total = 0
    for h, siglas in sorted(by_hash.items(), key=lambda kv: kv[1][0]):
        canonical = sorted(siglas)[0]
        fname = f"diretivo/{canonical}_diretivo.pdf"
        src = os.path.join(SRC_DIR, f"{canonical}_diretivo.pdf")
        shutil.copy2(src, os.path.join(DST, fname))
        total += os.path.getsize(src)
        for s in sorted(siglas):
            manifest["orgaos"][s] = {
                "file": fname, "md5": h,
                "compartilhado_com": sorted(x for x in siglas if x != s),
                "url_original": urls.get(s, ""),
            }
    shutil.copy2(SRC_TPL, os.path.join(DST, "template",
                                       "docdiretivo_minuta_v2-2.docx"))

    manifest["_stats"] = {"orgaos": len(manifest["orgaos"]),
                          "arquivos_unicos": len(by_hash),
                          "bytes": total}
    with open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(f"{len(by_hash)} PDFs únicos ({total/1e6:.0f} MB) cobrindo "
          f"{len(manifest['orgaos'])} órgãos → {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
