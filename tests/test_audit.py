# -*- coding: utf-8 -*-
"""Ledger dei rimborsi: validazioni e idempotenza, indipendenti dall'LLM."""
from __future__ import annotations

import pytest

from supporto import policy


def _proposal(sandbox, order_id: str = "ORD-1001", customer: str = "C-001") -> dict:
    order = policy.find_order(order_id, customer)
    refund = policy.calculate_refund(order)
    return {
        "order_id": order_id,
        "customer_id": customer,
        "amount": refund["total"],
        "reason": "Test del ledger",
        "requires_escalation": refund["requires_escalation"],
        "level": "responsabile" if refund["requires_escalation"] else "operatore",
    }


def test_senza_approvazione_non_scrive(sandbox):
    prima = len(sandbox.ledger.refunds())
    result = sandbox.ledger.execute_refund(_proposal(sandbox), {"approved": False})
    assert result["eseguito"] is False
    assert len(sandbox.ledger.refunds()) == prima


def test_importo_non_coerente_bloccato(sandbox):
    proposal = _proposal(sandbox)
    proposal["amount"] = 1.0
    result = sandbox.ledger.execute_refund(proposal, {"approved": True})
    assert result["eseguito"] is False
    assert "Importo" in result["motivo"]
    assert "ORD-1001" not in sandbox.ledger.refunds()
    eventi = [record["event"] for record in sandbox.ledger.read_audit(20)]
    assert "rimborso_errore" in eventi


def test_cliente_non_coerente_bloccato(sandbox):
    proposal = _proposal(sandbox)
    proposal["customer_id"] = "C-002"
    result = sandbox.ledger.execute_refund(proposal, {"approved": True})
    assert result["eseguito"] is False
    assert "cliente" in result["motivo"].lower()
    assert "ORD-1001" not in sandbox.ledger.refunds()


def test_idempotenza(sandbox):
    proposal = _proposal(sandbox)
    prima = len(sandbox.ledger.refunds())
    primo = sandbox.ledger.execute_refund(
        proposal, {"approved": True, "approver": "operatore-test", "level": "operatore"}
    )
    assert primo["eseguito"] is True
    record = sandbox.ledger.refunds()["ORD-1001"]
    assert record["amount"] == pytest.approx(89.70)
    assert record["approved_by"] == "operatore-test"

    secondo = sandbox.ledger.execute_refund(
        proposal, {"approved": True, "approver": "operatore-test"}
    )
    assert secondo["eseguito"] is False
    assert secondo["duplicato"] is True
    assert len(sandbox.ledger.refunds()) == prima + 1
    eventi = [item["event"] for item in sandbox.ledger.read_audit(30)]
    assert eventi.count("rimborso_eseguito") == 1
    assert "rimborso_duplicato_bloccato" in eventi


def test_ticket_progressivo(sandbox):
    primo = sandbox.ledger.create_ticket(
        customer_id="C-001", reason="Reclamo", message="Test", priority="alta"
    )
    secondo = sandbox.ledger.create_ticket(
        customer_id="C-001", reason="Info", message="Test", priority="normale"
    )
    assert primo["ticket_id"] == "TKT-2026-0001"
    assert secondo["ticket_id"] == "TKT-2026-0002"
    assert len(sandbox.ledger.tickets()) == 2
