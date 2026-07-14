# Cache de PDFs — Documento Diretivo

Cache versionado dos PDFs **"Documento Diretivo"** dos PTDs vigentes, baixados
do portal SGD/MGI (gov.br), + a minuta oficial do template (Kit de Elaboração
PTD). Existe para que a análise textual seja **reprodutível sem depender do
portal** — que muda de estrutura (ex.: defeso eleitoral) e renomeia arquivos.

## Download com um clique

- **Tudo (repo inteiro, inclui este cache):**
  [`main.zip`](https://github.com/freirelucas/PTD/archive/refs/heads/main.zip)
- **Um PDF específico:** navegue em [`diretivo/`](./diretivo) e clique em
  *Download raw file*.

## Conteúdo

- `diretivo/<SIGLA>_diretivo.pdf` — 66 PDFs únicos (dedup por MD5) cobrindo
  93 órgãos. Grupos ministeriais (MEC, MD, MF, MMA, MIDR, MDA…) publicam um
  único PDF compartilhado: o arquivo fica sob a **menor sigla** do grupo
  (mesma política do pipeline) e o `manifest.json` mapeia todas as siglas.
- `template/docdiretivo_minuta_v2-2.docx` — minuta oficial v2.2 do Documento
  Diretivo (SGD/MGI, Kit de Elaboração PTD).
- `manifest.json` — por órgão: arquivo canônico, MD5, siglas que compartilham
  o PDF e URL original no portal.

## Lacunas conhecidas (snapshot 2026-07-10)

- **ABIN e MDIC**: sem Documento Diretivo publicado no portal (só Anexo de
  Entregas). ANTT/DNIT/MT herdam o PTD dos grupos ministeriais.
- 14 diretivos são digitalizações sem OCR (AGU, ANVISA, CODEVASF, FBN, FCP,
  INCRA, ITI, MAPA, MCOM, MIDR, PREVIC, SUDAM, SUDECO, SUDENE) — presentes
  no cache, mas sem prosa extraível. O grupo MIDR re-publicou o diretivo
  como digitalização em jul/2026; a FUNAI saiu da lista com PDF pesquisável.
- **SUSEP**: o PDF renomeado no defeso foi recuperado pelo scraper de
  listagem — está no cache normalmente.

## Proveniência e integridade

Baixados em 2026-07-10 pelo pipeline (`run_pipeline.py`), com o portal em
defeso eleitoral (modo listagem paginada; URLs na forma
`planos-transformacao-digital`, sem `-de-`). Verifique a integridade com os MD5 do `manifest.json`:

```bash
python3 - <<'EOF'
import json, hashlib
m = json.load(open("corpus_pdfs/manifest.json"))
for sigla, info in m["orgaos"].items():
    h = hashlib.md5(open("corpus_pdfs/" + info["file"], "rb").read()).hexdigest()
    assert h == info["md5"], sigla
print("Integridade OK:", len(m["orgaos"]), "órgãos")
EOF
```
