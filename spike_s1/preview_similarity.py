#!/usr/bin/env python3
"""S1 spike — prévia da métrica: cosseno TF-IDF de cada bloco vs template.

SUPERSEDIDO por build_text_analysis.py (raiz do repo), que é a implementação
canônica: stopwords ampliadas, somas ordenadas (determinismo bit a bit),
consenso por versão e diffs. Este script fica como registro histórico do
spike; não compare os números daqui com os do dashboard.

TF-IDF implementado em Python puro (corpus pequeno: ~75 órgãos × 6 seções).
Também computa 'novidade' = fração de tokens do órgão ausentes no template.
Saída: ptd_output/text/similarity_preview.json + resumo no stdout.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_DIR = os.path.join(REPO, "ptd_output", "text")
TEMPLATE_JSON = os.path.join(REPO, "ptd_output", "template",
                             "directive_template_blocks.json")

STOP = set("""a o e de da do das dos em no na nos nas um uma uns umas para por
com sem sob sobre entre ao aos as os que se sua seu suas seus este esta isto
esse essa isso aquele aquela ou nem mas mais menos muito pouco tambem ja nao
sim como quando onde qual quais cada todo toda todos todas outro outra outros
outras mesmo mesma sendo ser sera serao foi foram esta estao estar tem tinha
ter havera haver pela pelo pelas pelos lhe lhes nos vos eu tu ele ela eles
elas voce voces meu minha teu tua dele dela deles delas num numa nuns numas
e s ate apos desde durante mediante perante salvo visando fim modo forma
respectivo respectiva referente relativo relativa""".split())


def tokenize(s: str):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower())
                if unicodedata.category(c) != "Mn")
    toks = re.findall(r"[a-z0-9]{2,}", s)
    return [t for t in toks if t not in STOP and not t.isdigit()]


def cosine(c1: Counter, c2: Counter, idf: dict) -> float:
    v1 = {t: n * idf.get(t, 0.0) for t, n in c1.items()}
    v2 = {t: n * idf.get(t, 0.0) for t, n in c2.items()}
    dot = sum(v1[t] * v2[t] for t in v1.keys() & v2.keys())
    n1 = math.sqrt(sum(x * x for x in v1.values()))
    n2 = math.sqrt(sum(x * x for x in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def main() -> int:
    with open(TEMPLATE_JSON, encoding="utf-8") as fh:
        tpl = {s["key"]: s["text"] for s in json.load(fh)["sections"]}
    with open(os.path.join(TEXT_DIR, "directive_blocks.json"),
              encoding="utf-8") as fh:
        blocks = json.load(fh)

    # IDF por seção sobre corpus (órgãos + template)
    results = {}
    for key, tpl_text in tpl.items():
        docs = {sig: b[key] for sig, b in blocks.items() if b.get(key)}
        if not docs:
            continue
        toks = {sig: tokenize(t) for sig, t in docs.items()}
        tpl_toks = tokenize(tpl_text)
        all_docs = list(toks.values()) + [tpl_toks]
        n_docs = len(all_docs)
        df = Counter()
        for d in all_docs:
            df.update(set(d))
        idf = {t: math.log(n_docs / (1 + c)) + 1 for t, c in df.items()}

        tpl_counter = Counter(tpl_toks)
        tpl_set = set(tpl_toks)
        sec = {}
        for sig, d in toks.items():
            c = Counter(d)
            sim = cosine(c, tpl_counter, idf)
            novel = (sum(1 for t in d if t not in tpl_set) / len(d)) if d else 0.0
            sec[sig] = {"cosine_tpl": round(sim, 4),
                        "novelty": round(novel, 4),
                        "n_tokens": len(d)}
        results[key] = sec

    out_path = os.path.join(TEXT_DIR, "similarity_preview.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)

    print(f"{'seção':16s} {'média':>6s} {'min':>6s} {'max':>6s}   ± contextualizados (novelty alta)")
    for key, sec in results.items():
        sims = [v["cosine_tpl"] for v in sec.values()]
        mean = sum(sims) / len(sims)
        top_novel = sorted(sec.items(), key=lambda kv: -kv[1]["novelty"])[:3]
        tn = ", ".join(f"{s}({v['novelty']:.2f})" for s, v in top_novel)
        print(f"{key:16s} {mean:6.3f} {min(sims):6.3f} {max(sims):6.3f}   {tn}")
    print(f"\nOK → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
