"""Testes para o cell 12b (iteração): generate_review_queue e apply_corrections.

Ambas dependem de globais do pipeline (all_deliveries/all_risks/all_errors),
injetados no namespace compartilhado via monkeypatch.
"""


def _risk(cells, **kw):
    RiskEntry = cells["RiskEntry"]
    base = dict(orgao_sigla="ABIN", risco_texto="r", probabilidade_original="raro",
                impacto_original="alto", tratamento_original="mitigar")
    base.update(kw)
    return RiskEntry(**base)


def _delivery(cells, **kw):
    DeliveryEntry = cells["DeliveryEntry"]
    base = dict(orgao_sigla="ABIN", tabela_tipo="pactuada", servico_acao="x",
                produto_original="P", produto_normalizado="P",
                eixo_original="", eixo_normalizado="")
    base.update(kw)
    return DeliveryEntry(**base)


# ---------------------- generate_review_queue ----------------------

def test_review_queue_collects_flagged_entries(cells, monkeypatch):
    r = _risk(cells, needs_review=True, review_reason="tratamento múltiplo/composto",
              extraction_confidence="medium")
    d = _delivery(cells, needs_review=True, review_reason="produto não reconhecido",
                  extraction_confidence="low")
    clean = _risk(cells, needs_review=False)
    monkeypatch.setitem(cells, "all_deliveries", [d])
    monkeypatch.setitem(cells, "all_risks", [r, clean])
    monkeypatch.setitem(cells, "all_errors", [])

    df = cells["generate_review_queue"]()
    assert len(df) == 2  # só os needs_review=True
    assert set(df["type"]) == {"risk", "delivery"}
    assert "priority" in df.columns


def test_review_queue_empty_when_nothing_flagged(cells, monkeypatch):
    monkeypatch.setitem(cells, "all_deliveries", [])
    monkeypatch.setitem(cells, "all_risks", [_risk(cells, needs_review=False)])
    monkeypatch.setitem(cells, "all_errors", [])
    df = cells["generate_review_queue"]()
    assert len(df) == 0


# ---------------------- apply_corrections ----------------------

_HEADER = "orgao_sigla,entry_type,field_name,original_value,corrected_value\n"


def test_apply_corrections_updates_entry(cells, tmp_path, monkeypatch):
    r = _risk(cells, tratamento_normalizado="mitigar", needs_review=True)
    monkeypatch.setitem(cells, "all_risks", [r])
    monkeypatch.setitem(cells, "all_deliveries", [])
    csv = tmp_path / "corr.csv"
    csv.write_text(_HEADER + "ABIN,risk,tratamento_normalizado,mitigar,aceitar\n",
                   encoding="utf-8")

    applied, failed = cells["apply_corrections"](str(csv))
    assert (applied, failed) == (1, 0)
    assert r.tratamento_normalizado == "aceitar"
    assert r.needs_review is False


def test_apply_corrections_unmatched_counts_failed(cells, tmp_path, monkeypatch):
    r = _risk(cells, tratamento_normalizado="mitigar")
    monkeypatch.setitem(cells, "all_risks", [r])
    monkeypatch.setitem(cells, "all_deliveries", [])
    csv = tmp_path / "corr.csv"
    # original_value não bate com o valor atual → não aplica.
    csv.write_text(_HEADER + "ABIN,risk,tratamento_normalizado,VALOR_ERRADO,aceitar\n",
                   encoding="utf-8")
    applied, failed = cells["apply_corrections"](str(csv))
    assert applied == 0 and failed == 1


def test_apply_corrections_missing_file(cells):
    assert cells["apply_corrections"]("/caminho/inexistente.csv") == (0, 0)


def test_apply_corrections_missing_columns(cells, tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("foo,bar\n1,2\n", encoding="utf-8")
    assert cells["apply_corrections"](str(csv)) == (0, 0)
