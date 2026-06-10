"""Testes dos aliases do snapshot 2026-05, do filtro de fragmentos (09b)
e do gerador de insumos da NT (11e)."""
import csv
import json
import os


# ---------- Aliases novos (handout 2026-06, seções 3.1/3.2) ----------

def test_produto_aliases_truncamentos(cells):
    fmp = cells["fuzzy_match_produto"]
    casos = {
        "integração à ferramenta de avaliação da":
            "Integração à ferramenta de avaliação da satisfação dos usuários",
        "integração à base de dados (outros)": "Integração à base de dados",
        "auto-avaliação, análise de lacunas e pla":
            "Auto-avaliação, análise de lacunas e planejamento do PPSI",
        "migração de serviço para plataforma":
            "Migração de Serviço para Plataforma Unificada",
        "disponibilização em acesso d": "Disponibilização em Acesso Digital",
        "implantação da área logada": "Implantação da Área Logada Gov.Br",
    }
    for original, esperado in casos.items():
        result, score = fmp(original)
        assert result == esperado, f"{original!r} → {result!r}"
        assert score >= 0.98


def test_produto_aliases_char_colado(cells):
    fmp = cells["fuzzy_match_produto"]
    casos = {
        "eintegração ao login único": "Integração ao Login Único",
        "edisponibilização em acesso digital": "Disponibilização em Acesso Digital",
        "eintegração à ferramenta de avaliação da":
            "Integração à ferramenta de avaliação da satisfação dos usuários",
    }
    for original, esperado in casos.items():
        result, score = fmp(original)
        assert result == esperado, f"{original!r} → {result!r}"
        assert score >= 0.98


def test_eixo_aliases_artefatos_pdf(cells):
    fme = cells["fuzzy_match_eixo"]
    casos = {
        "iviços digitais e melhoria da qualidade":
            "Serviços Digitais e Melhoria da Qualidade",
        "iserviços digitais e melhoria da qualidade":
            "Serviços Digitais e Melhoria da Qualidade",
        "psegurança e privacidade": "Segurança e Privacidade",
    }
    for original, esperado in casos.items():
        result, score = fme(original)
        assert result == esperado, f"{original!r} → {result!r}"
        assert score >= 0.93


def test_alias_targets_pertencem_ao_catalogo(cells):
    """Todo alias deve apontar para um produto/eixo do catálogo — um typo
    no target criaria um vocabulário fantasma fora da Portaria."""
    all_produtos = set(cells["ALL_PRODUTOS"])
    for alias, target in cells["PRODUTO_ALIASES"].items():
        assert target in all_produtos, f"alias {alias!r} → target fora do catálogo"
    eixos = set(cells["CANONICAL_EIXOS"])
    for alias, target in cells["EIXO_ALIASES"].items():
        assert target in eixos, f"alias {alias!r} → eixo fora do catálogo"


def test_prob_alias_baixo_mantido(cells):
    """'baixo' → 'pouco provável' (consistente com 'baixa' da escala ANTAQ).
    O handout 2026-06 propôs 'raro'; mantido o mapeamento existente até
    verificação no PDF do IBAMA — ver BALANCO_CONSISTENCIA.md (C4)."""
    assert cells["PROBABILIDADE_ALIASES"]["baixo"] == "pouco provável"


# ---------- Filtro de fragmentos (09b) ----------

def _entry(cells, produto, servico):
    return cells["DeliveryEntry"](
        orgao_sigla="TST", produto_normalizado=produto, servico_acao=servico)


def test_filter_fragments_descarta_outros_curto(cells):
    f = cells["filter_fragment_deliveries"]
    entries = [
        _entry(cells, "Outros", ""),                       # vazio → descarta
        _entry(cells, "Outros", "Meu RPPS"),               # 8 chars → descarta
        _entry(cells, "Outros", "Sistema Mercante ABC"),   # substantivo → mantém
        _entry(cells, "Integração ao Login Único", ""),    # não-Outros → mantém
    ]
    kept, dropped = f(entries)
    assert len(kept) == 2 and len(dropped) == 2
    assert all(e.produto_normalizado == "Outros" for e in dropped)


def test_filter_fragments_limite_10_chars(cells):
    f = cells["filter_fragment_deliveries"]
    kept, dropped = f([
        _entry(cells, "Outros", "123456789"),    # 9 → descarta
        _entry(cells, "Outros", "1234567890"),   # 10 → mantém
        _entry(cells, "Outros", "  espaços  "),  # strip → 7 → descarta
    ])
    assert len(dropped) == 2 and len(kept) == 1


# ---------- Gerador de insumos (11e) ----------

def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _mini_output(tmp_path):
    """Corpus sintético mínimo: 3 entregas, 2 riscos, 3 órgãos."""
    base_d = {"tabela_tipo": "pactuada", "produto_original": "", "produto_score": "1.0",
              "eixo_original": "", "eixo_normalizado": "Serviços Digitais e Melhoria da Qualidade",
              "eixo_score": "1.0", "eixo_method": "exact", "area_responsavel": "",
              "data_pactuada": "2026-12-01", "data_entrega": "", "pactuado": "",
              "justificativa": "", "extraction_confidence": "high",
              "needs_review": "False", "review_reason": ""}
    _write_csv(tmp_path / "deliveries.csv", [
        {**base_d, "orgao_sigla": "AAA", "servico_acao": "Serviço X",
         "produto_normalizado": "Integração ao Login Único", "produto_method": "exact"},
        {**base_d, "orgao_sigla": "AAA", "servico_acao": "Serviço Y",
         "produto_normalizado": "Implementação do PPSI", "produto_method": "alias"},
        {**base_d, "orgao_sigla": "BBB", "servico_acao": "abc",
         "produto_normalizado": "Outros", "produto_method": "fuzzy_high"},
    ])
    base_r = {"probabilidade_original": "", "probabilidade_score": "1.0",
              "probabilidade_method": "exact", "impacto_original": "",
              "impacto_score": "1.0", "impacto_method": "exact",
              "tratamento_original": "", "tratamento_score": "1.0",
              "tratamento_method": "exact", "extraction_confidence": "high",
              "needs_review": "False", "review_reason": ""}
    _write_csv(tmp_path / "risks.csv", [
        {**base_r, "orgao_sigla": "AAA", "risco_texto": "Falta de fornecedor",
         "probabilidade_normalizada": "praticamente certo",
         "impacto_normalizado": "muito alto", "tratamento_normalizado": "mitigar",
         "acoes_tratamento": "Plano A"},
        {**base_r, "orgao_sigla": "BBB", "risco_texto": "Rotatividade de equipe",
         "probabilidade_normalizada": "raro", "impacto_normalizado": "baixo",
         "tratamento_normalizado": "aceitar", "acoes_tratamento": ""},
    ])
    _write_csv(tmp_path / "coverage_summary.csv", [
        {"sigla": "AAA", "grupo": "", "pdf_diretivo": "ok", "pdf_entregas": "ok",
         "entregas_extraidas": "2", "riscos_extraidos": "1",
         "status_entregas": "ok", "status_riscos": "ok"},
        {"sigla": "BBB", "grupo": "", "pdf_diretivo": "ok", "pdf_entregas": "ok",
         "entregas_extraidas": "1", "riscos_extraidos": "1",
         "status_entregas": "ok", "status_riscos": "ok"},
        {"sigla": "CCC", "grupo": "", "pdf_diretivo": "", "pdf_entregas": "",
         "entregas_extraidas": "0", "riscos_extraidos": "0",
         "status_entregas": "sem_dados", "status_riscos": "sem_pdf"},
    ])
    return tmp_path


def test_compute_nt_metrics_sintetico(cells, tmp_path):
    M = cells["compute_nt_metrics"](str(_mini_output(tmp_path)), cells)
    assert M["n_deliveries"] == 3 and M["n_risks"] == 2
    assert M["n_signatarios"] == 3 and M["ent_cobertos"] == 2
    assert M["zona_critica"] == 1 and M["sev_max"] == 1
    assert M["sev_max_orgaos"] == [("AAA", 1)]
    assert M["sem_acoes"] == 1
    assert M["fragmentos_n"] == 1          # 'Outros' com 'abc'
    assert M["forn_n"] == 1 and M["forn_zc"] == 1
    assert M["prob_canon"] == 2 and M["imp_canon"] == 2
    assert M["trat_canon"] == 2
    assert M["dez_pct"] == 1.0             # todas as datas em dezembro


def test_write_nt_insumos_gera_md_e_atualiza_manifest(cells, tmp_path):
    out = _mini_output(tmp_path)
    manifest = {"data_execucao": "2026-05-12",
                "outputs": {"nota_tecnica_insumos.md": {"sha256": "stale"}}}
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    path = cells["write_nt_insumos"](str(out), cells)
    text = open(path, encoding="utf-8").read()
    assert "GERADO por notebook_cells/11e_nt_insumos.py" in text
    assert "Zona crítica" in text and "2026-05-12" in text

    with open(out / "manifest.json", encoding="utf-8") as f:
        m = json.load(f)
    entry = m["outputs"]["nota_tecnica_insumos.md"]
    assert entry["sha256"] != "stale" and entry["bytes"] > 0

    # Idempotência: segundo run não altera o conteúdo
    before = open(path, encoding="utf-8").read()
    cells["write_nt_insumos"](str(out), cells)
    assert open(path, encoding="utf-8").read() == before


def test_insumos_commitado_consistente_com_csvs(cells):
    """O nota_tecnica_insumos.md commitado deve ser exatamente o que o
    gerador produz sobre os CSVs commitados (detecta edição manual)."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo, "output")
    if not os.path.exists(os.path.join(out_dir, "deliveries.csv")):
        import pytest
        pytest.skip("output/ sem dados")
    M = cells["compute_nt_metrics"](out_dir, cells)
    with open(os.path.join(out_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    rendered = cells["render_nt_insumos"](M, manifest)
    committed = open(os.path.join(out_dir, "nota_tecnica_insumos.md"),
                     encoding="utf-8").read()
    assert rendered == committed