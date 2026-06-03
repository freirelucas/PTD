"""Testes para `_parse_year_month` (cell 11cb — geração do dashboard).

Normaliza `data_pactuada`/`data_entrega` (formatos heterogêneos vindos dos
PDFs) para 'YYYY-MM', a chave usada nos gráficos de timeline. Docstring da
função lista 5 formatos suportados; aqui cobrimos cada um + os fallbacks.
"""


def test_iso_year_month(cells):
    assert cells["_parse_year_month"]("2025-03") == "2025-03"


def test_iso_year_month_day(cells):
    assert cells["_parse_year_month"]("2025-03-15") == "2025-03"


def test_iso_pads_single_digit_month(cells):
    assert cells["_parse_year_month"]("2025-3") == "2025-03"


def test_month_abbrev_with_noise(cells):
    pym = cells["_parse_year_month"]
    assert pym("mar. 2025 (v2)") == "2025-03"
    assert pym("dez 2024") == "2024-12"


def test_dd_mm_yyyy(cells):
    assert cells["_parse_year_month"]("15/03/2025") == "2025-03"


def test_mm_yyyy(cells):
    assert cells["_parse_year_month"]("03/2025") == "2025-03"


def test_empty_returns_none(cells):
    pym = cells["_parse_year_month"]
    assert pym("") is None
    assert pym("   ") is None
    assert pym(None) is None


def test_unparseable_returns_none(cells):
    # Texto sem nenhum padrão reconhecível.
    assert cells["_parse_year_month"]("a definir") is None


def test_all_month_abbreviations(cells):
    pym = cells["_parse_year_month"]
    expected = {
        "jan": "01", "fev": "02", "mar": "03", "abr": "04",
        "mai": "05", "jun": "06", "jul": "07", "ago": "08",
        "set": "09", "out": "10", "nov": "11", "dez": "12",
    }
    for abbr, num in expected.items():
        assert pym(f"{abbr}. 2025") == f"2025-{num}"
