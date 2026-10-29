# -*- coding: utf-8 -*-
"""Comportamento dei tool, chiamati direttamente con un runtime finto."""
from __future__ import annotations

import json
from datetime import date

from supporto.config import Settings
from supporto.tools import make_tools


def _tools(sandbox, settings=None):
    return {
        tool.name: tool
        for tool in make_tools(sandbox.ledger, sandbox.memory, settings or sandbox.settings)
    }


def test_cerca_policy_restituisce_fonti(sandbox, runtime):
    payload = json.loads(
        _tools(sandbox)["cerca_policy"].func("costo spedizione", runtime)
    )
    assert payload["fonti"]
    assert "[S1]" in payload["contesto"]


def test_stato_ordine_del_cliente(sandbox, runtime):
    testo = _tools(sandbox)["stato_ordine"].func("ORD-1001", runtime)
    assert "Ordine ORD-1001" in testo
    assert "Consegnato" in testo
    assert "TRK-1001-IT" in testo
    assert "89,70 EUR" in testo
    assert "C-001" not in testo
    assert "@" not in testo


def test_ordine_altrui_uguale_a_ordine_inesistente(sandbox, runtime):
    tool = _tools(sandbox)["stato_ordine"]
    altro = tool.func("ORD-1004", runtime)
    inesistente = tool.func("ORD-9999", runtime)
    assert "Non trovo" in altro
    assert altro.replace("1004", "9999") == inesistente
    assert "C-002" not in altro
    eventi = [record["event"] for record in sandbox.ledger.read_audit(20)]
    assert eventi.count("privacy_accesso_negato") == 2


def test_elenca_ordini_filtrato(sandbox, runtime):
    testo = _tools(sandbox)["elenca_ordini"].func(runtime)
    assert "| Ordine |" in testo
    assert "ORD-1001" in testo
    assert "ORD-1004" not in testo
    assert "C-001" not in testo
    assert "C-002" not in testo


def test_verifica_reso_casi_principali(sandbox, runtime):
    tool = _tools(sandbox)["verifica_reso"]
    idoneo = tool.func("ORD-1001", runtime)
    assert "idoneo al reso" in idoneo
    assert "30 giorni" in idoneo
    assert "Giorni dalla consegna" in idoneo

    fuori = tool.func("ORD-1002", runtime)
    assert "non idoneo" in fuori
    assert "30 giorni" in fuori

    personalizzato = tool.func("ORD-1003", runtime)
    assert "non idoneo" in personalizzato
    assert "personalizzati" in personalizzato.lower()

    igiene = tool.func("ORD-1007", runtime)
    assert "non idoneo" in igiene
    assert "Categoria esclusa: articolo di igiene" in igiene

    difettoso = tool.func("ORD-1008", runtime)
    assert "idoneo al reso" in difettoso
    assert "difettoso" in difettoso


def test_verifica_reso_usa_la_data_delle_settings(sandbox, runtime):
    settings = Settings(
        model_backend="local",
        lm_studio_model="modello-finto",
        demo_today=date(2026, 11, 30),
    )
    testo = _tools(sandbox, settings)["verifica_reso"].func("ORD-1001", runtime)
    assert "non idoneo" in testo
    assert "48 giorni" in testo


def test_proponi_rimborso_non_idoneo_non_scrive(sandbox, runtime):
    prima = dict(sandbox.ledger.refunds())
    testo = _tools(sandbox)["proponi_rimborso"].func("ORD-1002", runtime)
    assert "Rimborso non eseguito" in testo
    assert "30 giorni" in testo
    assert sandbox.ledger.refunds() == prima


def test_ricorda_preferenza_rimuove_pii(sandbox, runtime):
    tool = _tools(sandbox)["ricorda_preferenza"]
    testo = tool.func(
        "Contattami a mario.rossi@example.com, preferisco le email", runtime
    )
    assert "Preferenza salvata" in testo
    profile = sandbox.memory.get_profile("C-001")
    assert "email rimossa" in profile
    assert "@" not in profile
    assert "mario.rossi" not in profile

    duplicato = tool.func(
        "Contattami a mario.rossi@example.com, preferisco le email", runtime
    )
    assert "Preferenza non salvata" in duplicato


def test_apri_ticket(sandbox, runtime):
    testo = _tools(sandbox)["apri_ticket"].func(
        "Voglio un responsabile, è urgente", runtime
    )
    assert "TKT-" in testo
    assert "priorità alta" in testo
    assert "24 ore" in testo
    assert len(sandbox.ledger.tickets()) == 1
