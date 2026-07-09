#!/usr/bin/env python3
"""Camada semântica OFFLINE da análise textual do Documento Diretivo.

Computa embeddings sentence-transformers dos blocos temáticos e o cosseno de
cada bloco contra sua referência (a mesma referência por versão que o
build_text_analysis.py usa), gravando SÓ os cossenos em
output/directive_text_embeddings.json — commitado como dado.

Roda UMA vez por snapshot do corpus (exige torch + download do modelo, fora
do caminho reprodutível-do-zero da CI; modelo e versões ficam registrados na
saída). Depois, `python build_text_analysis.py` mescla `cosine_emb` nas
métricas.

Uso:
  python build_text_embeddings.py
"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPO, "spike_s1", "data")
OUT = os.path.join(REPO, "output", "directive_text_embeddings.json")

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MAX_CHARS = 6000   # blocos longos são truncados (janela do modelo é menor)


def main() -> int:
    try:
        from sentence_transformers import SentenceTransformer
        import sentence_transformers
        import torch
    except ImportError as exc:
        print(f"Dependência ausente ({exc}). Instale com:\n"
              "  pip install torch --index-url "
              "https://download.pytorch.org/whl/cpu\n"
              "  pip install sentence-transformers")
        return 1

    import build_text_analysis as bta

    blocks, template, text_meta, dl, _ = bta.load_inputs()
    md5s = dl.get("md5", {})
    canonical, _ = bta.dedup_organs(blocks, md5s)
    versions = {s: (text_meta.get(s, {}).get("model_version") or "sem_versao")
                for s in blocks}
    tpl_sections = {s["key"]: s for s in template["sections"]}

    # Reusa exatamente a mesma escolha de referências do build_text_analysis
    analysis = bta.analyze()
    refs = analysis["referencias"]

    model = SentenceTransformer(MODEL_NAME)

    def embed(texts):
        return model.encode([t[:MAX_CHARS] for t in texts],
                            normalize_embeddings=True, show_progress_bar=False)

    result = {"model": MODEL_NAME,
              "sentence_transformers": sentence_transformers.__version__,
              "torch": torch.__version__,
              "cosine": {}}

    for key, tpl_sec in tpl_sections.items():
        if key not in refs:
            continue
        sec_blocks = {s: blocks[s][key] for s in canonical
                      if blocks.get(s, {}).get(key)}
        if not sec_blocks:
            continue
        consensus = refs[key]["consenso_por_versao"]
        use_template = key != "riscos"

        siglas = sorted(sec_blocks)
        vecs = dict(zip(siglas, embed([sec_blocks[s] for s in siglas])))
        tpl_vec = embed([tpl_sec["text"]])[0] if use_template else None

        for s in siglas:
            ver = versions.get(s, "sem_versao")
            ref_sigla = consensus.get(ver) or refs[key]["medoide_global"]
            ref_vec = (tpl_vec if use_template else vecs[ref_sigla])
            # vs a MESMA referência exibida no dashboard: template quando
            # aplicável, consenso para riscos
            cos = float((vecs[s] * ref_vec).sum())
            result["cosine"].setdefault(s, {})[key] = round(cos, 4)
        print(f"  {key}: {len(siglas)} blocos")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(f"OK → {os.path.relpath(OUT, REPO)}")
    print("Agora rode: python build_text_analysis.py  (mescla cosine_emb)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
