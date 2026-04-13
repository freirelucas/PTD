# ============================================================
# CÉLULA 1 — Setup & Instalação
# ============================================================
# Monta Google Drive e instala dependências.
# Em Colab, execute esta célula primeiro.

import os, sys

# --- Google Drive (descomente em Colab) ---
# from google.colab import drive
# drive.mount('/content/drive')

# --- Instalação de pacotes ---
# !pip install -q "typer>=0.24.0" "typer-slim>=0.24.0"
# !pip install -q docling beautifulsoup4 requests tqdm pandas matplotlib seaborn tabulate

# --- Diretórios de trabalho ---
# Em Colab aponte para o Drive; localmente use ./output
USE_DRIVE = False
if USE_DRIVE:
    BASE_DIR = "/content/drive/MyDrive/PTD_Scraper"
else:
    BASE_DIR = os.path.join(os.getcwd(), "ptd_output")

DIRS = {
    "pdfs_diretivo":  os.path.join(BASE_DIR, "pdfs", "diretivo"),
    "pdfs_entregas":  os.path.join(BASE_DIR, "pdfs", "entregas"),
    "output":         os.path.join(BASE_DIR, "output"),
    "checkpoints":    os.path.join(BASE_DIR, "checkpoints"),
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

print(f"Diretório base: {BASE_DIR}")
print("Estrutura criada:", list(DIRS.keys()))