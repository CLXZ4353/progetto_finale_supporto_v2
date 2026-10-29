# -*- coding: utf-8 -*-
"""Policy-as-code, coerenza con il corpus e retrieval BM25."""
from __future__ import annotations

import pytest

from supporto import policy
from supporto.config import CORPUS_DIR
from supporto.corpus import corpus_stats, retrieve, split_documents, load_corpus


def _testo() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in CORPUS_DIR.glob("*.md")}


def test_numero_documenti():
    assert len(_testo()) == 10


def test_costanti_policy():
    assert policy.RETURN_WINDOW_DAYS == 30
    assert policy.WARRANTY_MONTHS == 24
    assert policy.REFUND_PROCESSING_DAYS == "5-10"
    assert policy.FREE_SHIPPING_THRESHOLD_EUR == 50.0
    assert policy.SHIPPING_COST_EUR == 4.90
    assert policy.ESCALATION_THRESHOLD_EUR == 500.0


def test_numeri_dei_documenti_coerenti():
    docs = _testo()
    assert f"{policy.RETURN_WINDOW_DAYS} giorni" in docs["resi.md"]
    assert f"{policy.RETURN_WINDOW_DAYS} giorni" in docs["faq.md"]
    assert f"{policy.WARRANTY_MONTHS} mesi" in docs["garanzia.md"]
    assert policy.REFUND_PROCESSING_DAYS in docs["rimborsi.md"]
    assert f"{policy.ESCALATION_THRESHOLD_EUR:.0f} EUR" in docs["rimborsi.md"]
    assert (
        f"{policy.ESCALATION_FIRST_RESPONSE_HOURS} ore lavorative"
        in docs["escalation.md"]
    )
    assert "4,90 EUR" in docs["spedizioni.md"]


def test_ordine_di_altro_cliente_non_esiste(sandbox):
    assert policy.find_order("ORD-1004", "C-001") is None
    assert policy.find_order("ORD-1004", "C-002") is not None


def test_idoneita_finestra_e_categorie(sandbox):
    today = sandbox.settings.demo_today
    casi = {
        "ORD-1001": True,
        "ORD-1002": False,
        "ORD-1003": False,
        "ORD-1006": False,
        "ORD-1007": False,
        "ORD-1008": True,
    }
    for order_id, expected in casi.items():
        order = policy.find_order(order_id, "C-001")
        result = policy.check_return_eligibility(order, "C-001", today=today)
        assert result["eligible"] is expected, (order_id, result)


def test_motivi_idoneita(sandbox):
    today = sandbox.settings.demo_today
    fuori = policy.check_return_eligibility(
        policy.find_order("ORD-1002", "C-001"), "C-001", today=today
    )
    assert "30 giorni" in fuori["reason"]
    personalizzato = policy.check_return_eligibility(
        policy.find_order("ORD-1003", "C-001"), "C-001", today=today
    )
    assert "personalizzati" in personalizzato["reason"].lower()
    igiene = policy.check_return_eligibility(
        policy.find_order("ORD-1007", "C-001"), "C-001", today=today
    )
    assert "igiene" in igiene["reason"].lower()


def test_rimborsi_calcolati_dalla_policy(sandbox):
    standard = policy.calculate_refund(policy.find_order("ORD-1001", "C-001"))
    assert standard["total"] == pytest.approx(89.70)
    assert standard["requires_escalation"] is False
    assert policy.format_eur(standard["total"]) == "89,70 EUR"

    alto = policy.calculate_refund(policy.find_order("ORD-1005", "C-001"))
    assert alto["total"] == pytest.approx(749.00)
    assert alto["requires_escalation"] is True

    difettoso = policy.calculate_refund(policy.find_order("ORD-1008", "C-001"))
    assert difettoso["items_total"] == pytest.approx(37.00)
    assert difettoso["shipping_refund"] == pytest.approx(4.90)
    assert difettoso["total"] == pytest.approx(41.90)


def test_liste_ordini_separate_per_cliente(sandbox):
    miei = policy.list_orders("C-001")
    altrui = policy.list_orders("C-002")
    assert miei and altrui
    assert all(order["customer_id"] == "C-001" for order in miei)
    assert {order["order_id"] for order in miei}.isdisjoint(
        {order["order_id"] for order in altrui}
    )
    assert "ORD-1004" not in {order["order_id"] for order in miei}


def test_corpus_e_chunking():
    stats = corpus_stats()
    assert stats["documenti"] == 10
    assert stats["chunk"] > 50
    chunks = split_documents(load_corpus())
    assert all(chunk.metadata.get("source") for chunk in chunks)
    assert len({chunk.metadata["chunk_id"] for chunk in chunks}) == len(chunks)


@pytest.mark.parametrize(
    ("query", "attese"),
    [
        ("quanto costa la spedizione", {"spedizioni.md", "faq.md"}),
        ("quando arriva il rimborso", {"rimborsi.md", "faq.md", "resi.md"}),
        ("come traccio il pacco", {"tracciamento.md", "spedizioni.md"}),
        ("posso pagare con paypal", {"pagamenti.md"}),
    ],
)
def test_retrieval_bm25_trova_il_documento(query, attese):
    fonti = {doc.metadata["source"] for doc in retrieve(query, k=3)}
    assert fonti & attese
