# ============================================================
# CÉLULA 13c — Empacota output/ para publicação no main
# ============================================================
# Após executar o pipeline, gera um único `output.zip` em DIRS["output"]/..
# com TODOS os artefatos necessários para sincronizar o GitHub Pages.
#
# Por que isso existe:
# - GitHub Pages serve `index.html` + `output/data.js` direto do main.
# - Colab executa o pipeline e escreve em MyDrive/PTD_Scraper/output/.
# - Para Pages refletir dados novos é preciso copiar todo o `output/`
#   para o repo e commitar. Commit parcial (só validation_report sem CSVs,
#   por ex) cria inconsistência detectável pelo CI (ver
#   .github/workflows/notebook-consistency.yml).
# - Este helper zipa o conjunto coerente, evita seleção manual.
# ============================================================

import os
import zipfile
from datetime import datetime

out_dir = DIRS["output"]
zip_name = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
zip_path = os.path.join(os.path.dirname(out_dir), zip_name)

# Arquivos esperados em output/ — devem coincidir com os que o CI valida.
EXPECTED_OUTPUTS = [
    "data.js",
    "manifest.json",
    "validation_report.json",
    "statistics_summary.json",
    "review_data.json",
    "review_queue_prioritized.csv",
    "coverage_summary.csv",
    "pdf_metadata.csv",
    "risks.csv",
    "risks.json",
    "deliveries.csv",
    "deliveries.json",
    "organs.csv",
    "error_report.csv",
]

present, missing = [], []
for fname in EXPECTED_OUTPUTS:
    fpath = os.path.join(out_dir, fname)
    if os.path.exists(fpath):
        present.append((fname, fpath))
    else:
        missing.append(fname)

if not present:
    print("Nenhum arquivo em output/ encontrado — pipeline não rodou completo.")
else:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, fpath in present:
            zf.write(fpath, arcname=f"output/{fname}")

    print("=" * 60)
    print("BUNDLE DE PUBLICAÇÃO")
    print("=" * 60)
    print(f"  Arquivo: {zip_path}")
    print(f"  Conteúdo: {len(present)} arquivos")
    for fname, _ in present:
        size_kb = os.path.getsize(os.path.join(out_dir, fname)) / 1024
        print(f"    output/{fname:<35s} {size_kb:>7.1f} KB")
    if missing:
        print(f"\n  Ausentes ({len(missing)}): {', '.join(missing)}")
    print("\nPara publicar no GitHub Pages:")
    print("  1. Baixe o zip pelo painel de Files do Colab (clique direito → Download)")
    print("  2. No seu clone local do repo PTD:")
    print(f"       unzip -o {zip_name} && \\")
    print("       git add output/ && \\")
    print(f"       git commit -m 'data: refresh output/ pós-Colab run' && \\")
    print("       git push origin main")
    print("  3. GitHub Pages reflete em ~1 min em https://freirelucas.github.io/PTD/")
    print("=" * 60)

    # Em ambiente Colab, oferece o download programático.
    try:
        from google.colab import files as _gc_files
        print("\nIniciando download automático do bundle…")
        _gc_files.download(zip_path)
    except ImportError:
        pass  # Rodando local — usuário já tem o arquivo
