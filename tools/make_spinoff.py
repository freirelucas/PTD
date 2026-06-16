#!/usr/bin/env python3
"""Gera a semente do spin-off PTD-corpus (sem analytics) e empacota num zip.

Copia a fatia de engenharia do corpus do repo PTD, aplica as edições mecânicas
de desacoplamento, sobrepõe os templates versionados em spinoff/, regenera os
derivados (notebook, manifest, metadata, corpus), roda a suíte e zipa tudo.

Saídas (sob ptd_output/, ignorado pelo git):
  ptd_output/spinoff/ptd-corpus/        árvore do novo repositório
  ptd_output/ptd-corpus-handout.zip     pacote para descompactar e iniciar o repo

Uso:
  python tools/make_spinoff.py            # gera árvore + zip + valida
  python tools/make_spinoff.py --no-tests # pula pytest (mais rápido)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPINOFF_SRC = os.path.join(REPO_ROOT, "spinoff")
STAGE = os.path.join(REPO_ROOT, "ptd_output", "spinoff", "ptd-corpus")
ZIP_PATH = os.path.join(REPO_ROOT, "ptd_output", "ptd-corpus-handout.zip")

# --- O que sai: analytics + a fila de revisão/curadoria --------------------
# A fila de revisão (worklist de itens needs_review, exportada por 10b) e a
# célula de curadoria 12b saem por decisão do mantenedor — nunca foram
# validadas. A incerteza por linha continua nos CSVs (coluna needs_review) e
# nas contagens de validation_report.json.
EXCLUDE_CELLS = {
    "11a_statistics_header.md", "11b_statistics.py",
    "11ca_dashboard_header.md", "11cb_dashboard_data.py",
    "11cc_review_header.md", "11cd_review_queue.py",
    "11e_nt_insumos.py",
    "12a_iteration_header.md", "12b_iteration.py",
}
EXCLUDE_TESTS = {"test_nt_insumos.py", "test_parse_year_month.py",
                 "test_iteration.py"}
EXCLUDE_OUTPUT_FILES = {
    "statistics_summary.json", "data.js",
    "nota_tecnica_insumos.md", "review_data.json",
    "review_queue.csv", "review_queue_prioritized.csv",
}
EXCLUDE_OUTPUT_DIRS = {"figures"}

# --- O que é copiado verbatim do repo --------------------------------------
TOP_LEVEL_COPY = [
    "LICENSE", "CITATION.cff", "METADATA.md", "DECISIONS.md",
    "build_notebook.py", "build_metadata.py", "build_corpus.py",
    "run_pipeline.py", "smoke_test.py", "requirements-dev.txt", ".gitignore",
]

# --- Templates sobrepostos (spinoff/ → STAGE) ------------------------------
#   destino_relativo : origem_relativa_em_spinoff
TEMPLATES = {
    "README.md": "README.md",
    "Makefile": "Makefile",
    "requirements.txt": "requirements.txt",
    "build_manifest.py": "build_manifest.py",
    "HANDOUT.md": "HANDOUT.md",
    "notebook_cells/00_title.md": "notebook_cells/00_title.md",
    "tests/test_publish_helper.py": "tests/test_publish_helper.py",
    "tests/test_manifest.py": "tests/test_manifest.py",
}


def log(msg: str) -> None:
    print(f"[make_spinoff] {msg}", flush=True)


def patch(rel: str, old: str, new: str, count: int = 1) -> None:
    """Substituição ancorada num arquivo da STAGE; falha se a âncora sumiu."""
    path = os.path.join(STAGE, rel)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    found = content.count(old)
    if found != count:
        raise SystemExit(
            f"PATCH FALHOU em {rel}: âncora encontrada {found}x, esperado {count}.\n"
            f"--- âncora ---\n{old}\n--------------")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content.replace(old, new))
    log(f"patch {rel} ({count}x)")


def copy_tree() -> None:
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)

    for name in TOP_LEVEL_COPY:
        shutil.copy2(os.path.join(REPO_ROOT, name), os.path.join(STAGE, name))

    # notebook_cells/ sem as células de analytics
    src = os.path.join(REPO_ROOT, "notebook_cells")
    dst = os.path.join(STAGE, "notebook_cells")
    os.makedirs(dst)
    for f in sorted(os.listdir(src)):
        if f in EXCLUDE_CELLS:
            continue
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))

    # tests/ sem os testes de analytics (test_publish_helper vem do template)
    src = os.path.join(REPO_ROOT, "tests")
    dst = os.path.join(STAGE, "tests")
    os.makedirs(dst)
    for f in sorted(os.listdir(src)):
        if f in EXCLUDE_TESTS or f == "__pycache__":
            continue
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))

    # output/ sem os artefatos de analytics (subdirs derivados são regenerados)
    src = os.path.join(REPO_ROOT, "output")
    dst = os.path.join(STAGE, "output")
    os.makedirs(dst)
    for entry in sorted(os.listdir(src)):
        if entry in EXCLUDE_OUTPUT_FILES or entry in EXCLUDE_OUTPUT_DIRS:
            continue
        s = os.path.join(src, entry)
        d = os.path.join(dst, entry)
        shutil.copytree(s, d) if os.path.isdir(s) else shutil.copy2(s, d)

    # .github/workflows/
    shutil.copytree(os.path.join(REPO_ROOT, ".github"),
                    os.path.join(STAGE, ".github"))
    log("árvore copiada")


def apply_patches() -> None:
    # 01_setup: tira matplotlib/seaborn do pip do Colab
    patch("notebook_cells/01_setup.py",
          "get_ipython().system('pip install -q pymupdf pypdf beautifulsoup4 "
          "requests tqdm pandas matplotlib seaborn')",
          "get_ipython().system('pip install -q pymupdf pypdf beautifulsoup4 "
          "requests tqdm pandas')")

    # 13b: tira statistics_summary.json dos checksums e do print
    patch("notebook_cells/13b_validation_export.py",
          '    for name in ["risks.csv", "deliveries.csv", "organs.csv",\n'
          '                 "risks.json", "deliveries.json",\n'
          '                 "statistics_summary.json", "error_report.csv"]',
          '    for name in ["risks.csv", "deliveries.csv", "organs.csv",\n'
          '                 "risks.json", "deliveries.json", "error_report.csv"]')
    patch("notebook_cells/13b_validation_export.py",
          'print("Baixe validation_report.json e statistics_summary.json para auditoria local.")',
          'print("Baixe validation_report.json para auditoria local.")')

    # 13c: EXPECTED_OUTPUTS só com artefatos do corpus + build_manifest no help
    patch("notebook_cells/13c_publish_helper.py",
          'EXPECTED_OUTPUTS = [\n'
          '    "data.js",\n'
          '    "manifest.json",\n'
          '    "validation_report.json",\n'
          '    "statistics_summary.json",\n'
          '    "review_data.json",\n'
          '    "review_queue.csv",\n'
          '    "coverage_summary.csv",\n'
          '    "pdf_metadata.csv",\n'
          '    "risks.csv",\n'
          '    "risks.json",\n'
          '    "deliveries.csv",\n'
          '    "deliveries.json",\n'
          '    "organs.csv",\n'
          '    "error_report.csv",\n'
          '    "vocabulary_mapping.csv",\n'
          '    "nota_tecnica_insumos.md",\n'
          ']',
          'EXPECTED_OUTPUTS = [\n'
          '    "manifest.json",\n'
          '    "validation_report.json",\n'
          '    "coverage_summary.csv",\n'
          '    "pdf_metadata.csv",\n'
          '    "risks.csv",\n'
          '    "risks.json",\n'
          '    "deliveries.csv",\n'
          '    "deliveries.json",\n'
          '    "organs.csv",\n'
          '    "error_report.csv",\n'
          '    "vocabulary_mapping.csv",\n'
          ']')
    patch("notebook_cells/13c_publish_helper.py",
          'print("       python build_metadata.py && python build_corpus.py && \\\\")',
          'print("       python build_manifest.py && python build_metadata.py '
          '&& python build_corpus.py && \\\\")')

    # build_metadata: não injeta mais schema.org no index.html (inexistente)
    patch("build_metadata.py",
          '    with open(INDEX_HTML, encoding="utf-8") as fh:\n'
          '        html = fh.read()\n'
          '    artifacts["index.html"] = inject_schema_org(html, '
          'build_schema_org(citation, manifest))\n'
          '    return artifacts',
          '    return artifacts')

    # 10b: remove a exportação da fila de revisão (review_queue.csv)
    patch("notebook_cells/10b_export.py",
          '# ---- 6. Fila de revisão: CSV ----\n'
          'review_rows = []\n'
          '\n'
          'for entry in all_deliveries:\n'
          '    if entry.needs_review:\n'
          '        review_rows.append({\n'
          '            "orgao_sigla": entry.orgao_sigla,\n'
          '            "entry_type": "delivery",\n'
          '            "field": "produto / eixo",\n'
          '            "original_value": entry.produto_original,\n'
          '            "current_value": entry.produto_normalizado,\n'
          '            "eixo_original": entry.eixo_original,\n'
          '            "eixo_normalizado": entry.eixo_normalizado,\n'
          '            "confidence": entry.extraction_confidence,\n'
          '            "review_reason": entry.review_reason or "",\n'
          '            "servico_acao": entry.servico_acao,\n'
          '            "tabela_tipo": entry.tabela_tipo,\n'
          '        })\n'
          '\n'
          'for entry in all_risks:\n'
          '    if entry.needs_review:\n'
          '        review_rows.append({\n'
          '            "orgao_sigla": entry.orgao_sigla,\n'
          '            "entry_type": "risk",\n'
          '            "field": "probabilidade / impacto / tratamento",\n'
          '            "original_value": f"P:{entry.probabilidade_original} | I:{entry.impacto_original} | T:{entry.tratamento_original}",\n'
          '            "current_value": f"P:{entry.probabilidade_normalizada} | I:{entry.impacto_normalizado} | T:{entry.tratamento_normalizado}",\n'
          '            "eixo_original": "",\n'
          '            "eixo_normalizado": "",\n'
          '            "confidence": entry.extraction_confidence,\n'
          '            "review_reason": entry.review_reason or "",\n'
          '            "servico_acao": entry.risco_texto[:100] if entry.risco_texto else "",\n'
          '            "tabela_tipo": "",\n'
          '        })\n'
          '\n'
          'if review_rows:\n'
          '    df_review = pd.DataFrame(review_rows)\n'
          '    csv_path = os.path.join(DIRS["output"], "review_queue.csv")\n'
          '    df_review.to_csv(csv_path, index=False, encoding="utf-8-sig")\n'
          '    export_log.append(("review_queue.csv", len(df_review), _file_size_str(csv_path)))\n'
          'else:\n'
          '    print("Nenhum item pendente de revisão.")\n'
          '\n',
          '')

    # conftest: tira as células de analytics + curadoria do loader de testes
    patch("tests/conftest.py",
          '    "10b_export.py",\n'
          '    "11cb_dashboard_data.py",\n'
          '    "11e_nt_insumos.py",\n'
          '    "12b_iteration.py",',
          '    "10b_export.py",')

    # run_pipeline: comentário do MPLBACKEND + sync chama build_manifest
    patch("run_pipeline.py",
          'os.environ.setdefault("MPLBACKEND", "Agg")   # 11b usa plt.show() — vira no-op',
          'os.environ.setdefault("MPLBACKEND", "Agg")   # headless: sem display (defensivo)')
    patch("run_pipeline.py",
          "    import build_corpus\n"
          "    import build_metadata\n"
          "    if build_metadata.main([]) != 0 or build_corpus.main([]) != 0:\n"
          '        print("SYNC: regeneração de metadados/corpus falhou.")\n'
          "        sys.exit(1)",
          "    import build_corpus\n"
          "    import build_manifest\n"
          "    import build_metadata\n"
          "    if (build_manifest.main([]) != 0 or build_metadata.main([]) != 0\n"
          "            or build_corpus.main([]) != 0):\n"
          '        print("SYNC: regeneração de manifest/metadados/corpus falhou.")\n'
          "        sys.exit(1)")

    # smoke_test: deps obrigatórias sem matplotlib/seaborn
    patch("smoke_test.py",
          '_REQUIREMENTS = {\n'
          '    "pymupdf": "fitz", "beautifulsoup4": "bs4", "requests": "requests",\n'
          '    "tqdm": "tqdm", "pandas": "pandas", "matplotlib": "matplotlib",\n'
          '    "seaborn": "seaborn",\n'
          '}\n'
          '# pypdf é importado lazy dentro de uma função (11cb) → opcional para carga.',
          '_REQUIREMENTS = {\n'
          '    "pymupdf": "fitz", "beautifulsoup4": "bs4", "requests": "requests",\n'
          '    "tqdm": "tqdm", "pandas": "pandas",\n'
          '}\n'
          '# pypdf é importado lazy dentro do pipeline → opcional para carga.')
    patch("smoke_test.py",
          '                "classify_diretivo_table", "generate_review_queue"]',
          '                "classify_diretivo_table"]')

    # monthly-refresh: tira index.html do PR + comentário
    patch(".github/workflows/monthly-refresh.yml",
          "          add-paths: |\n"
          "            output/**\n"
          "            index.html",
          "          add-paths: |\n"
          "            output/**")
    patch(".github/workflows/monthly-refresh.yml",
          "          # data.js/manifest.json/*.json embutem timestamps e mudam SEMPRE.",
          "          # manifest.json/*.json embutem timestamps/hashes e mudam SEMPRE.")
    patch(".github/workflows/monthly-refresh.yml",
          "                      output/vocabulary_mapping.csv output/review_queue.csv\"",
          "                      output/vocabulary_mapping.csv\"")

    # .gitignore: ignora o bundle de publicação do 13c
    patch(".gitignore",
          "/corpus_*.zip",
          "/corpus_*.zip\n# Bundle de publicação gerado por 13c (artefato, não fonte)\n/output_*.zip")


def overlay_templates() -> None:
    for dest_rel, src_rel in TEMPLATES.items():
        src = os.path.join(SPINOFF_SRC, src_rel)
        dst = os.path.join(STAGE, dest_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    log(f"{len(TEMPLATES)} templates sobrepostos")


def write_provenance() -> None:
    try:
        commit = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        commit = "(desconhecido)"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        "PTD-corpus — semente de spin-off (sem analytics)\n"
        f"gerado em: {now}\n"
        f"a partir do repo PTD, commit: {commit}\n"
        "gerador: tools/make_spinoff.py\n"
        "Ver HANDOUT.md para o que foi mantido/removido e os próximos passos.\n")
    with open(os.path.join(STAGE, "SPINOFF_PROVENANCE.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)


def run(cmd: list, label: str) -> None:
    log(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=STAGE)
    if r.returncode != 0:
        raise SystemExit(f"FALHOU: {label} (exit {r.returncode})")


def regenerate(run_tests: bool) -> None:
    py = sys.executable
    run([py, "build_notebook.py"], "build_notebook")
    run([py, "build_manifest.py"], "build_manifest")
    run([py, "build_metadata.py"], "build_metadata")
    run([py, "build_corpus.py"], "build_corpus")
    if run_tests:
        run([py, "-m", "pytest", "-q", "tests/"], "pytest")
        run([py, "smoke_test.py"], "smoke_test")


_ZIP_SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", "ptd_output"}


def make_zip() -> int:
    os.makedirs(os.path.dirname(ZIP_PATH), exist_ok=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    n = 0
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(STAGE):
            dirs[:] = sorted(d for d in dirs if d not in _ZIP_SKIP_DIRS)
            for f in sorted(files):
                if f.endswith((".pyc", ".pyo")):
                    continue
                fpath = os.path.join(root, f)
                arc = os.path.join("ptd-corpus", os.path.relpath(fpath, STAGE))
                zf.write(fpath, arcname=arc)
                n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera o spin-off PTD-corpus.")
    ap.add_argument("--no-tests", action="store_true",
                    help="Pula pytest/smoke (gera mais rápido).")
    args = ap.parse_args(argv)

    copy_tree()
    apply_patches()
    overlay_templates()
    write_provenance()
    regenerate(run_tests=not args.no_tests)
    n = make_zip()

    log(f"OK — árvore em {STAGE}")
    log(f"OK — zip ({n} arquivos) em {ZIP_PATH} "
        f"({os.path.getsize(ZIP_PATH) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
