# ============================================================
# CÉLULA 13c — Empacota output/ para publicação no main
# ============================================================
# Após executar o pipeline, gera um único `output_TIMESTAMP.zip` em
# DIRS["output"]/.. com o conteúdo COMPLETO de output/ (recursivo,
# incluindo figures/ e quaisquer extras presentes).
#
# Por que isso existe:
# - GitHub Pages serve `index.html` + `output/data.js` direto do main.
# - Colab executa o pipeline e escreve em MyDrive/PTD_Scraper/output/.
# - Para Pages refletir dados novos é preciso copiar todo o `output/`
#   para o repo e commitar. Commit parcial (só validation_report sem CSVs,
#   por ex) cria inconsistência detectável pelo CI (ver
#   .github/workflows/notebook-consistency.yml).
# - Este helper valida o conjunto essencial e zipa tudo, sem seleção manual.
# ============================================================

import os
import zipfile
from datetime import datetime

out_dir = DIRS["output"]
zip_name = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
zip_path = os.path.join(os.path.dirname(out_dir), zip_name)

# Núcleo obrigatório: o que o pipeline SEMPRE gera no top-level de output/.
# Fora da lista (decisão deliberada):
#   - review_queue_prioritized.csv  condicional (12b só grava com fila
#                                   não-vazia); entra no zip se existir
#   - datapackage.json, metadata/, harmonized/  derivados no repo por
#     build_metadata.py / build_corpus.py (ver README §Publicar)
EXPECTED_OUTPUTS = [
    "data.js",
    "manifest.json",
    "validation_report.json",
    "statistics_summary.json",
    "review_data.json",
    "review_queue.csv",
    "coverage_summary.csv",
    "pdf_metadata.csv",
    "risks.csv",
    "risks.json",
    "deliveries.csv",
    "deliveries.json",
    "organs.csv",
    "error_report.csv",
    "vocabulary_mapping.csv",
    "nota_tecnica_insumos.md",
]

_missing = [f for f in EXPECTED_OUTPUTS
            if not os.path.exists(os.path.join(out_dir, f))]
if _missing:
    raise RuntimeError(
        f"Pipeline incompleto — {len(_missing)} artefato(s) essenciais "
        f"ausentes em output/: {', '.join(_missing)}. Execute as células "
        f"anteriores (04b→13b) antes de publicar.")

# Zip recursivo de TODO o output/. Arcnames sempre sob 'output/' por
# construção (relpath ancorado em out_dir) — sem path traversal.
_entries = []
for _root, _dirs, _files in os.walk(out_dir):
    _dirs.sort()
    for _fname in sorted(_files):
        _fpath = os.path.join(_root, _fname)
        _arc = os.path.join("output", os.path.relpath(_fpath, out_dir))
        _entries.append((_fpath, _arc))

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for _fpath, _arc in _entries:
        zf.write(_fpath, arcname=_arc)

print("=" * 60)
print("BUNDLE DE PUBLICAÇÃO")
print("=" * 60)
print(f"  Arquivo: {zip_path}")
print(f"  Conteúdo: {len(_entries)} arquivos (output/ completo)")
for _fpath, _arc in _entries:
    print(f"    {_arc:<48s} {os.path.getsize(_fpath) / 1024:>8.1f} KB")
print("\nPara publicar no GitHub Pages:")
print("  1. Baixe o zip pelo painel de Files do Colab (ou aguarde o download automático)")
print("  2. No seu clone local do repo PTD:")
print(f"       unzip -o {zip_name} && \\")
print("       python build_metadata.py && python build_corpus.py && \\")
print("       git add output/ index.html && \\")
print("       git commit -m 'data: refresh output/ pós-Colab run' && \\")
print("       git push origin main")
print("  3. GitHub Pages reflete em ~1 min em https://freirelucas.github.io/PTD/")
print("=" * 60)

# Em ambiente Colab, oferece o download programático.
try:
    from google.colab import files as _gc_files
    print("\nIniciando download automático do bundle…")
    _gc_files.download(zip_path)
except ImportError:
    pass  # headless/local — o zip fica em disco
