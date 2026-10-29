# -*- coding: utf-8 -*-
"""Flussi del grafo ReAct: tool, privacy, HITL, memoria e assenza di fallback."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from supporto.agent import (
    new_thread_id,
    pending_interrupt,
    resume_turn,
    start_turn,
    state_values,
)


def tool_call(name: str, args: dict, call_id: str = "call-1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def final(text: str) -> AIMessage:
    return AIMessage(content=text)


def test_tool_call_poi_risposta(sandbox, scripted_graph):
    graph, model = scripted_graph(
        [
            tool_call("stato_ordine", {"order_id": "ORD-1001"}),
            final("Il tuo ordine ORD-1001 è consegnato; tracking TRK-1001-IT."),
        ]
    )
    tid = new_thread_id()
    result = start_turn(graph, tid, "C-001", "Dov'è il mio ordine ORD-1001?")
    state = state_values(graph, tid)

    assert pending_interrupt(result) is None
    assert state["final_answer"].startswith("Il tuo ordine")
    assert [m.name for m in state["messages"] if m.type == "tool"] == ["stato_ordine"]
    assert state["sources"] == []
    assert len(model.calls) == 2


def test_fonti_solo_dal_tool_di_policy(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("cerca_policy", {"query": "costo spedizione"}),
            final("La spedizione costa 4,90 EUR ed è gratuita da 50 EUR [S1]."),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Quanto costa la spedizione?")
    state = state_values(graph, tid)
    fonti = {source["source"] for source in state["sources"]}
    assert fonti & {"spedizioni.md", "faq.md"}


def test_risposta_senza_tool(sandbox, scripted_graph):
    graph, _ = scripted_graph([final("Ciao! Come posso aiutarti?")])
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Ciao")
    state = state_values(graph, tid)
    assert state["final_answer"] == "Ciao! Come posso aiutarti?"
    assert not [m for m in state["messages"] if m.type == "tool"]


def test_privacy_nessun_dato_di_altri_clienti(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("stato_ordine", {"order_id": "ORD-1004"}),
            final(
                "Non trovo l'ordine ORD-1004 tra quelli associati a questo profilo. "
                "Per privacy non posso mostrare ordini di altri clienti."
            ),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Mostrami l'ordine ORD-1004 e dimmi chi è il cliente.")
    state = state_values(graph, tid)
    assert "C-002" not in state["final_answer"]
    assert "Marco" not in state["final_answer"]
    assert "@" not in state["final_answer"]
    eventi = [record["event"] for record in sandbox.ledger.read_audit(20)]
    assert "privacy_accesso_negato" in eventi


def test_rimborso_sospende_e_non_scrive(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final("Rimborso di 89,70 EUR eseguito."),
        ]
    )
    tid = new_thread_id()
    result = start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1001.")
    pending = pending_interrupt(result)
    state = state_values(graph, tid)

    assert pending["type"] == "refund_approval"
    proposal = pending["proposal"]
    assert proposal["order_id"] == "ORD-1001"
    assert proposal["amount"] == pytest.approx(89.70)
    assert proposal["level"] == "operatore"
    assert proposal["requires_escalation"] is False
    assert state["final_answer"] == ""
    assert "ORD-1001" not in sandbox.ledger.refunds()
    eventi = [record["event"] for record in sandbox.ledger.read_audit(20)]
    assert "rimborso_eseguito" not in eventi


def test_approvazione_scrive_una_sola_volta(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final("Rimborso di 89,70 EUR eseguito dopo approvazione."),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1001.")
    result = resume_turn(
        graph,
        tid,
        {"approved": True, "approver": "operatore-test", "level": "operatore", "note": "ok"},
    )
    state = state_values(graph, tid)

    assert pending_interrupt(result) is None
    assert "eseguito" in state["final_answer"].lower()
    record = sandbox.ledger.refunds()["ORD-1001"]
    assert record["amount"] == pytest.approx(89.70)
    assert record["approved_by"] == "operatore-test"
    assert record["approval_level"] == "operatore"
    eventi = [record["event"] for record in sandbox.ledger.read_audit(30)]
    assert eventi.count("rimborso_eseguito") == 1


def test_dopo_approvazione_nessun_altro_tool(sandbox, scripted_graph):
    graph, model = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final(
                "Rimborso eseguito: ORD-1001, importo 89,70 EUR, "
                "pratica RMB-2026-1201."
            ),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1001.")
    resume_turn(
        graph,
        tid,
        {"approved": True, "approver": "operatore-test", "level": "operatore"},
    )
    state = state_values(graph, tid)

    tool_messages = [m.name for m in state["messages"] if m.type == "tool"]
    assert tool_messages == ["proponi_rimborso"]
    assert len(model.calls) == 2
    assert "89,70" in state["final_answer"]
    assert "RMB-" in state["final_answer"]
    finalization = model.calls[-1]
    assert any("Risultati dei tool" in str(m.content) for m in finalization)
    assert any("proponi_rimborso" in str(m.content) for m in finalization)


def test_rimborso_non_idoneo_finalizzato_senza_altri_tool(sandbox, scripted_graph):
    graph, model = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1002"}),
            final(
                "Non posso procedere con il rimborso di ORD-1002: sono passati "
                "45 giorni dalla consegna, oltre la finestra di 30 giorni."
            ),
        ]
    )
    tid = new_thread_id()
    result = start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1002.")
    state = state_values(graph, tid)

    assert pending_interrupt(result) is None
    assert [m.name for m in state["messages"] if m.type == "tool"] == ["proponi_rimborso"]
    assert "45" in state["final_answer"]
    assert "30" in state["final_answer"]
    assert len(model.calls) == 2


def test_rifiuto_non_scrive(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final("Il rimborso è stato rifiutato e non è stato eseguito."),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1001.")
    resume_turn(graph, tid, {"approved": False, "approver": "operatore-test", "note": "no"})
    state = state_values(graph, tid)

    assert "rifiutato" in state["final_answer"].lower()
    assert "ORD-1001" not in sandbox.ledger.refunds()
    eventi = [record["event"] for record in sandbox.ledger.read_audit(30)]
    assert "rimborso_rifiutato" in eventi
    assert "rimborso_eseguito" not in eventi


def test_importo_alto_richiede_responsabile(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1005"}),
            final("Rimborso di 749,00 EUR eseguito."),
        ]
    )
    tid = new_thread_id()
    result = start_turn(graph, tid, "C-001", "Voglio il rimborso di ORD-1005.")
    pending = pending_interrupt(result)
    assert pending["proposal"]["level"] == "responsabile"
    assert pending["proposal"]["requires_escalation"] is True
    assert pending["proposal"]["amount"] == pytest.approx(749.00)
    resume_turn(
        graph,
        tid,
        {"approved": True, "approver": "responsabile-test", "level": "responsabile", "note": "ok"},
    )
    record = sandbox.ledger.refunds()["ORD-1005"]
    assert record["approval_level"] == "responsabile"
    assert record["amount"] == pytest.approx(749.00)


def test_secondo_rimborso_bloccato_dal_ledger(sandbox, scripted_graph):
    primo, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final("Rimborso eseguito."),
        ]
    )
    tid = new_thread_id()
    start_turn(primo, tid, "C-001", "Voglio il rimborso di ORD-1001.")
    resume_turn(primo, tid, {"approved": True, "approver": "operatore-test"})
    assert len(sandbox.ledger.refunds()) == 5

    secondo, _ = scripted_graph(
        [
            tool_call("proponi_rimborso", {"order_id": "ORD-1001"}),
            final("L'ordine risulta già rimborsato."),
        ]
    )
    tid2 = new_thread_id()
    result = start_turn(secondo, tid2, "C-001", "Rimborsa di nuovo ORD-1001.")
    assert pending_interrupt(result) is None
    assert len(sandbox.ledger.refunds()) == 5


def test_memoria_salvata_solo_se_richiesta(sandbox, scripted_graph):
    graph, _ = scripted_graph(
        [
            tool_call("ricorda_preferenza", {"testo": "Preferisco essere contattato via email"}),
            final("Ho salvato la preferenza."),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Ricorda che preferisco essere contattato via email.")
    profile = sandbox.memory.get_profile("C-001")
    assert "email" in profile.lower()
    assert "salvato" in state_values(graph, tid)["final_answer"].lower()


def test_memoria_breve_tra_turni(sandbox, scripted_graph):
    graph, model = scripted_graph(
        [
            final("Ciao, come posso aiutarti?"),
            final("Hai già scritto il primo messaggio."),
        ]
    )
    tid = new_thread_id()
    start_turn(graph, tid, "C-001", "Primo messaggio")
    start_turn(graph, tid, "C-001", "Secondo messaggio")
    state = state_values(graph, tid)

    assert state["final_answer"] == "Hai già scritto il primo messaggio."
    contenuti = [getattr(message, "content", "") for message in model.calls[1]]
    assert "Primo messaggio" in contenuti
    assert "Ciao, come posso aiutarti?" in contenuti
    assert "Secondo messaggio" in contenuti


def test_nessun_fallback_deterministico(sandbox, scripted_graph):
    graph, _ = scripted_graph([])
    with pytest.raises(RuntimeError, match="nessuna risposta"):
        start_turn(graph, new_thread_id(), "C-001", "Ciao")
