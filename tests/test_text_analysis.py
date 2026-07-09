"""Testes de build_text_analysis.py — métricas textuais do Documento Diretivo.

Fixtures pequenas, sem rede e sem os dados reais do corpus: cada função é
exercitada isoladamente (tokenizador, cosseno TF-IDF, medoide, opcodes de
diff, dedup por MD5).
"""
from collections import Counter

import build_text_analysis as bta


# ---------------------------- tokenize ------------------------------

def test_tokenize_remove_acentos_stopwords_e_numeros():
    toks = bta.tokenize("A Transformação Digital do órgão em 2025 é ampla")
    assert "transformacao" in toks
    assert "digital" in toks
    assert "orgao" in toks
    assert "2025" not in toks          # número puro
    assert "do" not in toks            # stopword
    assert "a" not in toks


def test_tokenize_vazio():
    assert bta.tokenize("") == []
    assert bta.tokenize("de da do") == []


# ----------------------------- cosine -------------------------------

def test_cosine_identico_e_disjunto():
    d1 = bta.tokenize("governanca digital servicos publicos")
    d2 = bta.tokenize("politica espacial brasileira lancamentos")
    idf = bta.build_idf([d1, d2])
    c1, c2 = Counter(d1), Counter(d2)
    assert bta.cosine(c1, c1, idf) == 1.0 or abs(bta.cosine(c1, c1, idf) - 1.0) < 1e-9
    assert bta.cosine(c1, c2, idf) == 0.0


def test_cosine_parcial_entre_0_e_1():
    d1 = bta.tokenize("governanca digital servicos publicos qualidade")
    d2 = bta.tokenize("governanca digital seguranca privacidade")
    idf = bta.build_idf([d1, d2])
    sim = bta.cosine(Counter(d1), Counter(d2), idf)
    assert 0.0 < sim < 1.0


def test_cosine_vetor_vazio_zero():
    idf = {"x": 1.0}
    assert bta.cosine(Counter(), Counter({"x": 1}), idf) == 0.0


# ----------------------------- medoid -------------------------------

def test_medoid_escolhe_o_mais_central():
    # a e b quase iguais; c é o estranho → medoide deve ser a ou b
    docs = {
        "A": bta.tokenize("governanca digital servicos publicos federais"),
        "B": bta.tokenize("governanca digital servicos publicos estaduais"),
        "C": bta.tokenize("politica espacial lancamento satelites orbita"),
    }
    idf = bta.build_idf(list(docs.values()))
    assert bta.medoid(docs, idf) in ("A", "B")


def test_medoid_unico_elemento():
    docs = {"X": ["a", "b"]}
    assert bta.medoid(docs, bta.build_idf(list(docs.values()))) == "X"


# ------------------------- word_diff_opcodes -------------------------

def test_diff_opcodes_insercao_de_palavra_e_estavel():
    # Inserir UMA palavra não cascateia: resto permanece 'equal'
    ref = "o plano de transformacao digital do orgao".split()
    org = "o plano ESTRATEGICO de transformacao digital do orgao".split()
    ops = bta.word_diff_opcodes(ref, org)
    kinds = [o[0] for o in ops]
    assert kinds.count("insert") == 1
    assert kinds.count("equal") == 2
    assert "delete" not in kinds
    # cobertura completa dos dois lados
    assert ops[0][1] == 0 and ops[-1][2] == len(ref)
    assert ops[0][3] == 0 and ops[-1][4] == len(org)


def test_diff_opcodes_identico():
    words = "a b c".split()
    ops = bta.word_diff_opcodes(words, words)
    assert ops == [["equal", 0, 3, 0, 3]]


# ---------------------------- dedup_organs ---------------------------

def test_dedup_por_md5_menor_sigla_canonica():
    blocks = {"MEC": {}, "CAPES": {}, "FNDE": {}, "AEB": {}}
    md5s = {"MEC": "h1", "CAPES": "h1", "FNDE": "h1", "AEB": "h2"}
    canonical, shared = bta.dedup_organs(blocks, md5s)
    assert set(canonical) == {"CAPES", "AEB"}          # menor sigla do grupo
    assert sorted(canonical["CAPES"]) == ["FNDE", "MEC"]
    assert shared["MEC"] == "CAPES" and shared["AEB"] == "AEB"


def test_dedup_sem_md5_cada_um_e_canonico():
    blocks = {"X": {}, "Y": {}}
    canonical, _ = bta.dedup_organs(blocks, {})
    assert set(canonical) == {"X", "Y"}
    assert canonical["X"] == [] and canonical["Y"] == []


# ------------------------- integração leve ---------------------------

def test_analyze_com_dados_reais_commitados():
    """Roda a análise completa sobre os dados commitados do spike (rápido,
    sem rede) e valida propriedades estruturais, não valores exatos."""
    result = bta.analyze()
    assert result["template_version"] == "2.2"
    assert len(result["secoes"]) == 6
    assert len(result["metricas"]) >= 40           # ~50 órgãos canônicos

    for sigla, secoes in result["metricas"].items():
        for key, m in secoes.items():
            assert 0.0 <= m["cosine_ref"] <= 1.0, (sigla, key)
            assert 0.0 <= m["novelty"] <= 1.0, (sigla, key)
            if key == "riscos":
                assert "cosine_tpl" not in m       # template é só instrução
    # eixos é cópia do template → mediana de novelty deve ser baixa;
    # visao é conteúdo próprio → mediana de novelty deve ser alta
    ag = result["agregados"]
    assert ag["eixos"]["novelty_mediana"] < 0.15
    assert ag["visao"]["novelty_mediana"] > 0.4
