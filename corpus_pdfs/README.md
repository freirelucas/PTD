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

- `diretivo/<SIGLA>_diretivo.pdf` — 60 PDFs únicos (dedup por MD5) cobrindo
  85 órgãos. Grupos ministeriais (MEC, MD, MF, MMA, MIDR, MDA…) publicam um
  único PDF compartilhado: o arquivo fica sob a **menor sigla** do grupo
  (mesma política do pipeline) e o `manifest.json` mapeia todas as siglas.
- `template/docdiretivo_minuta_v2-2.docx` — minuta oficial v2.2 do Documento
  Diretivo (SGD/MGI, Kit de Elaboração PTD).
- `manifest.json` — por órgão: arquivo canônico, MD5, siglas que compartilham
  o PDF e URL original no portal.

## Lacunas conhecidas (snapshot jul/2026)

- **SUSEP**: PDF renomeado no portal durante o defeso eleitoral → 404 na URL
  registrada; re-scrape futuro deve recuperá-lo.
- **ABIN, ANTT, DNIT, MDIC, MT**: sem URL de Documento Diretivo no portal
  (ANTT/DNIT/MT usam o PTD dos ministérios MT/MIDR; ABIN/MDIC sem diretivo
  publicado).
- 10 diretivos são digitalizações sem OCR (AGU, ANVISA, FBN, FCP, FUNAI,
  INCRA, ITI, MAPA, MCOM, PREVIC) — presentes no cache, mas sem prosa
  extraível.

## Proveniência e integridade

Baixados em 2026-07-09 das URLs em `output/organs.csv` (reescritas para a
forma do portal em defeso eleitoral: `planos-transformacao-digital`, sem
`-de-`). Verifique a integridade com os MD5 do `manifest.json`:

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
