# -*- coding: utf-8 -*-
"""Fixture condivise: dati demo isolati e modello scriptato (nessuna rete)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import AIMessage  # noqa: E402

from supporto import policy  # noqa: E402
from supporto.agent import build_graph  # noqa: E402
from supporto.audit import AuditLedger  # noqa: E402
from supporto.config import Settings  # noqa: E402
from supporto.memory import PreferenceMemory  # noqa: E402
from supporto.support_data import write_support_data  # noqa: E402


class ScriptedModel:
    """Modello finto: restituisce le risposte AIMessage nell'ordine dato."""

    def __init__(self, responses: list[AIMessage]):
        self.responses = list(responses)
        self.calls: list[list] = []
        self.tools: list = []

    def bind_tools(self, tools):
        self.tools = list(tools)
        return self

    def invoke(self, messages):
        self.calls.append(list(messages))
        if not self.responses:
            raise RuntimeError("ScriptedModel: nessuna risposta preparata")
        return self.responses.pop(0)


def tool_call(name: str, args: dict, call_id: str = "call-1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id}],
    )


def final_answer(text: str) -> AIMessage:
    return AIMessage(content=text)


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_TODAY", "2026-10-23")
    monkeypatch.setenv("MODEL_BACKEND", "local")
    monkeypatch.setenv("TOP_K", "3")

    write_support_data(tmp_path)

    monkeypatch.setattr(policy, "ORDERS_PATH", tmp_path / "orders.json")
    monkeypatch.setattr(policy, "CUSTOMERS_PATH", tmp_path / "customers.json")
    monkeypatch.setattr(policy, "PRODUCTS_PATH", tmp_path / "products.json")
    monkeypatch.setattr(policy, "REFUNDS_PATH", tmp_path / "refunds.json")

    ledger = AuditLedger(
        audit_path=tmp_path / "audit.jsonl",
        refunds_path=tmp_path / "refunds.json",
        orders_path=tmp_path / "orders.json",
        tickets_path=tmp_path / "tickets.json",
    )
    memory = PreferenceMemory(tmp_path / "preferences.json")
    settings = Settings(
        model_backend="local",
        lm_studio_model="modello-finto",
        demo_today=date(2026, 10, 23),
    )
    return SimpleNamespace(
        tmp=tmp_path,
        ledger=ledger,
        memory=memory,
        settings=settings,
        policy=policy,
    )


@pytest.fixture()
def scripted_graph(sandbox):
    """Costruisce un grafo con il modello scriptato e le dipendenze del sandbox."""

    def _make(responses: list[AIMessage]):
        model = ScriptedModel(responses)
        graph = build_graph(
            sandbox.settings,
            model=model,
            ledger=sandbox.ledger,
            memory=sandbox.memory,
        )
        return graph, model

    return _make


@pytest.fixture()
def runtime():
    return SimpleNamespace(
        state={"customer_id": "C-001"},
        config={"configurable": {"thread_id": "test-thread"}},
    )
