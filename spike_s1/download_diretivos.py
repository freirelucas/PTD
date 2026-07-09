#!/usr/bin/env python3
"""S1 spike — baixa os PDFs do Documento Diretivo listados em output/organs.csv.

Respeita o delay de 2s entre requests ao gov.br (mesma política do pipeline).
Saída: ptd_output/pdfs/diretivo/<SIGLA>_diretivo.pdf + download_report.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORGANS_CSV = os.path.join(REPO, "output", "organs.csv")
PDF_DIR = os.path.join(REPO, "ptd_output", "pdfs", "diretivo")
REPORT = os.path.join(REPO, "ptd_output", "pdfs", "download_report.json")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
}
DELAY = 2.0
RETRIES = 3


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    os.makedirs(PDF_DIR, exist_ok=True)
    with open(ORGANS_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    report = {"ok": [], "skipped_no_url": [], "failed": [], "md5": {}}
    # O portal foi reestruturado desde a coleta de maio/2026: o segmento
    # "planos-de-transformacao-digital" virou "planos-transformacao-digital".
    todo = [(r["sigla"],
             r["url_diretivo"].replace("/planos-de-transformacao-digital/",
                                       "/planos-transformacao-digital/"))
            for r in rows if r.get("url_diretivo")]
    print(f"{len(rows)} órgãos, {len(todo)} com url_diretivo")

    for i, (sigla, url) in enumerate(todo, 1):
        dest = os.path.join(PDF_DIR, f"{sigla}_diretivo.pdf")
        if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
            report["ok"].append(sigla)
            report["md5"][sigla] = md5(dest)
            continue
        ok = False
        for attempt in range(RETRIES):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=90)
                if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
                    with open(dest, "wb") as fh:
                        fh.write(resp.content)
                    ok = True
                    break
                print(f"  {sigla}: HTTP {resp.status_code} "
                      f"(magic={resp.content[:5]!r}) tentativa {attempt+1}")
            except requests.RequestException as exc:
                print(f"  {sigla}: {type(exc).__name__} tentativa {attempt+1}")
            time.sleep(DELAY * (attempt + 2))
        if ok:
            report["ok"].append(sigla)
            report["md5"][sigla] = md5(dest)
            print(f"[{i}/{len(todo)}] {sigla} ok ({os.path.getsize(dest)//1024} KB)")
        else:
            report["failed"].append({"sigla": sigla, "url": url})
            print(f"[{i}/{len(todo)}] {sigla} FALHOU")
        time.sleep(DELAY)

    report["skipped_no_url"] = [r["sigla"] for r in rows if not r.get("url_diretivo")]
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\nOK={len(report['ok'])} FALHA={len(report['failed'])} "
          f"SEM_URL={len(report['skipped_no_url'])}")
    print(f"Relatório → {REPORT}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
