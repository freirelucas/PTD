#!/usr/bin/env python3
"""Análise de similaridade & discrepância do corpo em prosa do Documento Diretivo.

Mede, por (órgão, seção temática), o quão pro forma o texto é (similaridade ao
template oficial SGD e ao consenso do corpus) versus o quão contextualizado
(vocabulário próprio, ausente da referência). Puro Python/stdlib — 100%
determinístico e reprodutível.

Referências por seção:
  - `cosine_tpl`: cosseno TF-IDF contra a minuta oficial v2.2 (Kit de
    Elaboração PTD). Órgãos em versões antigas do modelo divergem do template
    por VERSÃO, não por originalidade — por isso também:
  - `cosine_ref`: cosseno contra o CONSENSO do grupo de versão do órgão
    (bloco medoide = maior cosseno médio intra-grupo; grupos <5 órgãos usam o
    medoide global). Para a seção `riscos` o template é só instrução de
    preenchimento, então a referência é sempre o consenso.
  - `novelty`: fração de tokens do bloco ausentes na referência de consenso —
    o sinal de contextualização local.
  - `local_terms`: termos TF-IDF mais distintivos do bloco ausentes da
    referência (o "vocabulário próprio" do órgão).
  - `diff`: opcodes difflib palavra-a-palavra vs a referência, para o
    visualizador do dashboard (estável: inserir uma palavra não cascateia).

Dedup: grupos ministeriais compartilham o mesmo PDF (MD5) — a análise roda uma
vez por PDF único, sob a menor sigla; `compartilhado_com` preserva o mapa.

Entradas (committadas, sem rede):
  spike_s1/data/directive_blocks.json          blocos segmentados por órgão
  spike_s1/data/directive_template_blocks.json template v2.2 em blocos
  spike_s1/data/directive_text.json            versão do modelo por órgão
  spike_s1/data/download_report.json           MD5 por órgão (dedup)
  output/directive_text_embeddings.json        (opcional) cosine_emb offline

Saídas:
  output/directive_text_analysis.json   métricas por órgão/seção + agregados
  output/text_data.js                   const PTD_TEXT = {...} (lazy-load)

Uso:
  python build_text_analysis.py           # (re)gera as saídas
  python build_text_analysis.py --check   # falha se saída committada defasou
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter

REPO = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPO, "spike_s1", "data")
OUT_JSON = os.path.join(REPO, "output", "directive_text_analysis.json")
OUT_JS = os.path.join(REPO, "output", "text_data.js")
EMB_JSON = os.path.join(REPO, "output", "directive_text_embeddings.json")

MIN_VERSION_GROUP = 5     # grupo de versão menor que isso usa medoide global
N_LOCAL_TERMS = 12        # termos distintivos exibidos por bloco
MIN_BLOCK_TOKENS = 15     # bloco menor que isso não recebe métricas (ruído)

# Stopwords pt-BR mínimas (funcionais) — suficiente para TF-IDF de blocos
STOPWORDS = set("""a o e de da do das dos em no na nos nas um uma uns umas
para por com sem sob sobre entre ao aos as os que se sua seu suas seus este
esta isto esse essa isso aquele aquela ou nem mas mais menos muito pouco
tambem ja nao sim como quando onde qual quais cada todo toda todos todas
outro outra outros outras mesmo mesma sendo ser sera serao foi foram esta
estao estar tem tinha ter havera haver pela pelo pelas pelos lhe lhes nos
vos eu tu ele ela eles elas voce voces meu minha teu tua dele dela deles
delas num numa nuns numas ate apos desde durante mediante perante salvo
visando fim modo forma respectivo respectiva referente relativo relativa
sao ha nº n° art caput inciso paragrafo alinea itens item pdf""".split())


# ------------------------- primitivas de texto -------------------------

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# Bullets de PDFs (Wingdings/Symbol) chegam como Private Use Area e viram
# tofu no navegador. Trocamos por bullet real ANTES de tokenizar/diffar,
# para que os índices dos opcodes correspondam ao texto exibido.
_PUA_RE = re.compile(r"[-￼�]")


def clean_pdf_text(s: str) -> str:
    return _PUA_RE.sub("•", s)


def tokenize(s: str) -> list:
    """Tokens minúsculos sem acento, sem stopwords, sem números puros."""
    s = strip_accents(s.lower())
    toks = re.findall(r"[a-z0-9]{2,}", s)
    return [t for t in toks if t not in STOPWORDS and not t.isdigit()]


def build_idf(docs: list) -> dict:
    """IDF suavizado sobre uma lista de listas de tokens."""
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d))
    return {t: math.log(n / (1 + c)) + 1 for t, c in df.items()}


def cosine(c1: Counter, c2: Counter, idf: dict) -> float:
    v1 = {t: n * idf.get(t, 0.0) for t, n in c1.items()}
    v2 = {t: n * idf.get(t, 0.0) for t, n in c2.items()}
    dot = sum(v1[t] * v2[t] for t in v1.keys() & v2.keys())
    n1 = math.sqrt(sum(x * x for x in v1.values()))
    n2 = math.sqrt(sum(x * x for x in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def medoid(tok_by_sigla: dict, idf: dict) -> str:
    """Sigla do bloco medoide (maior cosseno médio contra os demais)."""
    siglas = sorted(tok_by_sigla)
    if len(siglas) == 1:
        return siglas[0]
    counters = {s: Counter(tok_by_sigla[s]) for s in siglas}
    best, best_avg = siglas[0], -1.0
    for s in siglas:
        avg = sum(cosine(counters[s], counters[o], idf)
                  for o in siglas if o != s) / (len(siglas) - 1)
        if avg > best_avg:
            best, best_avg = s, avg
    return best


def word_diff_opcodes(ref_words: list, org_words: list) -> list:
    """Opcodes difflib compactos [op, i1, i2, j1, j2] p/ render no dashboard."""
    sm = difflib.SequenceMatcher(None, ref_words, org_words, autojunk=False)
    return [[op, i1, i2, j1, j2] for op, i1, i2, j1, j2 in sm.get_opcodes()]


# ----------------------------- pipeline -------------------------------

def load_inputs():
    with open(os.path.join(DATA, "directive_blocks.json"), encoding="utf-8") as fh:
        blocks = json.load(fh)
    with open(os.path.join(DATA, "directive_template_blocks.json"),
              encoding="utf-8") as fh:
        template = json.load(fh)
    with open(os.path.join(DATA, "directive_text.json"), encoding="utf-8") as fh:
        text_meta = json.load(fh)
    with open(os.path.join(DATA, "download_report.json"), encoding="utf-8") as fh:
        dl = json.load(fh)
    emb = None
    if os.path.exists(EMB_JSON):
        with open(EMB_JSON, encoding="utf-8") as fh:
            emb = json.load(fh)
    return blocks, template, text_meta, dl, emb


def dedup_organs(blocks: dict, md5s: dict):
    """PDFs idênticos → análise única sob a menor sigla."""
    groups = {}
    for sigla in blocks:
        groups.setdefault(md5s.get(sigla, sigla), []).append(sigla)
    canonical, shared = {}, {}
    for _, siglas in groups.items():
        siglas = sorted(siglas)
        canonical[siglas[0]] = siglas[1:]
        for s in siglas:
            shared[s] = siglas[0]
    return canonical, shared


def analyze():
    blocks, template, text_meta, dl, emb = load_inputs()
    tpl_sections = {s["key"]: s for s in template["sections"]}
    md5s = dl.get("md5", {})
    canonical, shared_map = dedup_organs(blocks, md5s)

    versions = {s: (text_meta.get(s, {}).get("model_version") or "sem_versao")
                for s in blocks}

    result = {
        "template_version": template.get("template_version"),
        "secoes": [{"key": s["key"], "num": s["num"], "title": s["title"]}
                   for s in template["sections"]],
        "orgaos": {},          # sigla canônica → {versao, compartilhado_com}
        "metricas": {},        # sigla → seção → métricas
        "referencias": {},     # seção → {template, consenso: {grupo: sigla}}
        "diffs": {},           # sigla → seção → opcodes vs referência
        "textos": {},          # sigla → seção → texto do bloco
        "textos_ref": {},      # seção → {ref_id: texto}
    }

    for sigla, others in sorted(canonical.items()):
        result["orgaos"][sigla] = {
            "versao_modelo": versions.get(sigla),
            "compartilhado_com": others,
        }

    for key, tpl_sec in tpl_sections.items():
        tpl_tokens = tokenize(tpl_sec["text"])
        # blocos canônicos presentes nesta seção
        sec_blocks = {s: clean_pdf_text(blocks[s][key]) for s in canonical
                      if blocks.get(s, {}).get(key)}
        sec_tokens = {s: tokenize(t) for s, t in sec_blocks.items()}
        sec_tokens = {s: t for s, t in sec_tokens.items()
                      if len(t) >= MIN_BLOCK_TOKENS}
        if not sec_tokens:
            continue

        idf = build_idf(list(sec_tokens.values()) + [tpl_tokens])
        tpl_counter = Counter(tpl_tokens)

        # Consenso por grupo de versão (medoide); grupos pequenos → global
        by_version = {}
        for s in sec_tokens:
            by_version.setdefault(versions.get(s, "sem_versao"), []).append(s)
        global_medoid = medoid(sec_tokens, idf)
        consensus = {}
        for ver, siglas in by_version.items():
            if len(siglas) >= MIN_VERSION_GROUP:
                consensus[ver] = medoid({s: sec_tokens[s] for s in siglas}, idf)
            else:
                consensus[ver] = global_medoid

        result["referencias"][key] = {
            "consenso_por_versao": consensus,
            "medoide_global": global_medoid,
        }
        # textos de referência usados pelo diff viewer
        ref_texts = {"template": tpl_sec["text"]}
        for ver, ms in consensus.items():
            ref_texts[f"consenso:{ms}"] = sec_blocks[ms]
        result["textos_ref"][key] = ref_texts

        # a seção riscos compara SÓ contra consenso (template é instrução)
        use_template = key != "riscos"

        for s, toks in sorted(sec_tokens.items()):
            c = Counter(toks)
            ver = versions.get(s, "sem_versao")
            ref_sigla = consensus[ver]
            ref_tokens = sec_tokens[ref_sigla]
            ref_counter = Counter(ref_tokens)
            ref_set = set(ref_tokens)

            is_ref = s == ref_sigla
            cos_ref = 1.0 if is_ref else cosine(c, ref_counter, idf)
            novelty = (0.0 if is_ref else
                       sum(1 for t in toks if t not in ref_set) / len(toks))

            # termos distintivos: maior tf-idf entre os ausentes da referência
            # (para o medoide, ausentes do template)
            base_set = ref_set if not is_ref else set(tpl_tokens)
            distinct = sorted(
                ((n * idf.get(t, 0.0), t) for t, n in c.items()
                 if t not in base_set),
                reverse=True)[:N_LOCAL_TERMS]

            m = {
                "cosine_ref": round(cos_ref, 4),
                "novelty": round(novelty, 4),
                "n_tokens": len(toks),
                "ref": ref_sigla,
                "local_terms": [t for _, t in distinct],
            }
            if use_template:
                m["cosine_tpl"] = round(cosine(c, tpl_counter, idf), 4)
            if emb:
                e = emb.get("cosine", {}).get(s, {}).get(key)
                if e is not None:
                    m["cosine_emb"] = round(e, 4)
            result["metricas"].setdefault(s, {})[key] = m

            # diff palavra-a-palavra contra a referência exibível
            ref_words = (tpl_sec["text"] if use_template
                         else sec_blocks[ref_sigla]).split()
            org_words = sec_blocks[s].split()
            result["diffs"].setdefault(s, {})[key] = \
                word_diff_opcodes(ref_words, org_words)
            result["textos"].setdefault(s, {})[key] = sec_blocks[s]

    # ----- agregados por seção (pro forma vs contextualizado) -----
    aggregates = {}
    for key in tpl_sections:
        vals = [m[key] for m in result["metricas"].values() if key in m]
        if not vals:
            continue
        n = len(vals)
        cos_r = sorted(v["cosine_ref"] for v in vals)
        nov = sorted(v["novelty"] for v in vals)
        aggregates[key] = {
            "n_orgaos": n,
            "cosine_ref_mediana": round(cos_r[n // 2], 4),
            "novelty_mediana": round(nov[n // 2], 4),
        }
    result["agregados"] = aggregates
    result["provenance"] = {
        "gerado_por": "build_text_analysis.py",
        "fonte_blocos": "spike_s1/data/ (snapshot 2026-07-09)",
        "embeddings": bool(emb),
    }
    return result


def render_js(result: dict) -> str:
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return ("// Gerado por build_text_analysis.py — análise textual do "
            "Documento Diretivo.\n"
            "// Carregado sob demanda pela aba 'Texto Diretivo' do dashboard.\n"
            f"const PTD_TEXT = {payload};\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="Não escreve; falha (exit 1) se as saídas commitadas "
                         "diferem do que seria gerado.")
    args = ap.parse_args(argv)

    result = analyze()
    out_json = json.dumps(result, ensure_ascii=False, indent=1)
    out_js = render_js(result)

    if args.check:
        stale = []
        for path, want in ((OUT_JSON, out_json), (OUT_JS, out_js)):
            have = (open(path, encoding="utf-8").read()
                    if os.path.exists(path) else None)
            if have != want:
                stale.append(os.path.relpath(path, REPO))
        if stale:
            print(f"DEFASADO: {', '.join(stale)} — rode "
                  f"python build_text_analysis.py")
            return 1
        print("--check ok: saídas em dia.")
        return 0

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        fh.write(out_json)
    with open(OUT_JS, "w", encoding="utf-8") as fh:
        fh.write(out_js)

    n_org = len(result["metricas"])
    print(f"Análise: {n_org} órgãos canônicos × {len(result['secoes'])} seções")
    for key, agg in result["agregados"].items():
        print(f"  {key:16s} n={agg['n_orgaos']:2d} "
              f"cos_ref~{agg['cosine_ref_mediana']:.2f} "
              f"novelty~{agg['novelty_mediana']:.2f}")
    print(f"OK → {os.path.relpath(OUT_JSON, REPO)}, "
          f"{os.path.relpath(OUT_JS, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
