# -*- coding: utf-8 -*-
"""Coerenza della suite di valutazione con tool, clienti e corpus."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from scenarios import SCENARIOS  # noqa: E402

from supporto import policy  # noqa: E402
from supporto.config import CORPUS_DIR  # noqa: E402
from supporto.tools import make_tools  # noqa: E402


def test_scenari_coerenti(sandbox):
    nomi_tool = {tool.name for tool in make_tools(sandbox.ledger, sandbox.memory)}
    clienti = {customer["customer_id"] for customer in policy.load_customers()}
    documenti = {path.name for path in CORPUS_DIR.glob("*.md")}
    ids = [scenario["id"] for scenario in SCENARIOS]

    assert len(ids) == len(set(ids))
    for scenario in SCENARIOS:
        assert scenario["customer"] in clienti
        assert set(scenario.get("tools") or []) <= nomi_tool, scenario["id"]
        assert set(scenario.get("forbidden_tools") or []) <= nomi_tool, scenario["id"]
        assert set(scenario.get("sources") or []) <= documenti, scenario["id"]
        if scenario.get("interrupt"):
            assert scenario.get("approve") is not None, scenario["id"]
        if scenario.get("refund_executed"):
            assert scenario.get("approve") is True, scenario["id"]
