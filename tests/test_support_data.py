# -*- coding: utf-8 -*-
"""Test della scrittura centralizzata dei dati demo."""
from __future__ import annotations

import json

from supporto.support_data import SUPPORT_FILES, write_support_data


def test_write_support_data_crea_i_sei_file(tmp_path):
    data = write_support_data(tmp_path)
    assert {path.stem for path in tmp_path.glob("*.json")} == set(SUPPORT_FILES)
    assert json.loads((tmp_path / "orders.json").read_text(encoding="utf-8")) == data[
        "orders"
    ]
    assert json.loads(
        (tmp_path / "preferences.json").read_text(encoding="utf-8")
    ) == {}


def test_write_support_data_e_riproducibile(tmp_path):
    primo = write_support_data(tmp_path)
    secondo = write_support_data(tmp_path)
    assert primo == secondo
