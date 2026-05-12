"""Carrega notebook_cells/02_config.py + 03_utils.py num namespace compartilhado.

Os cells assumem namespace global do Jupyter — para testá-los como Python
puro, carregamos via exec() num módulo dummy e expomos os símbolos como
fixtures pytest. Side effects das cells (prints, listas vazias `all_*`)
são tolerados.
"""
import os
import sys
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLS_DIR = os.path.join(REPO_ROOT, "notebook_cells")


def _load_cells():
    """Carrega 02_config e 03_utils em um namespace. Retorna dict global."""
    ns: dict = {}

    # Imports que as cells assumem disponíveis (cell 02 faz `import` no topo,
    # mas cell 03 reusa o namespace). Pre-popula para 03 não quebrar se
    # rodado isoladamente.
    import re, unicodedata, difflib, os as _os, time, pickle, json, logging
    from typing import Optional, List, Tuple, Dict, Any
    from dataclasses import dataclass, field, asdict
    from datetime import datetime
    import requests, pandas as pd
    from bs4 import BeautifulSoup
    from tqdm.auto import tqdm

    ns.update({
        "re": re, "unicodedata": unicodedata, "difflib": difflib, "os": _os,
        "time": time, "pickle": pickle, "json": json, "logging": logging,
        "Optional": Optional, "List": List, "Tuple": Tuple, "Dict": Dict, "Any": Any,
        "dataclass": dataclass, "field": field, "asdict": asdict,
        "datetime": datetime, "requests": requests, "pd": pd,
        "BeautifulSoup": BeautifulSoup, "tqdm": tqdm,
        # DIRS stub — apenas cell 03 referencia em save_checkpoint, não no
        # caminho coberto por estes testes
        "DIRS": {"checkpoints": "/tmp"},
    })

    for fname in ("02_config.py", "03_utils.py"):
        path = os.path.join(CELLS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            code = f.read()
        exec(compile(code, path, "exec"), ns)
    return ns


@pytest.fixture(scope="session")
def cells():
    """Namespace com tudo de 02_config + 03_utils carregado.

    Uso típico:
        def test_x(cells):
            assert cells["normalize_text"]("foo") == "foo"
    """
    return _load_cells()
