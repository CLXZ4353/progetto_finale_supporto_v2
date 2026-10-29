# -*- coding: utf-8 -*-
"""Memoria a lungo termine delle preferenze, su file e senza PII."""
from __future__ import annotations

from supporto.memory import PreferenceMemory


def test_salva_e_rilegge(tmp_path):
    path = tmp_path / "preferences.json"
    memory = PreferenceMemory(path)
    result = memory.add("C-001", "Preferisco la consegna il sabato")
    assert result["salvata"] is True
    assert "sabato" in memory.get_profile("C-001")

    ricaricata = PreferenceMemory(path)
    assert "sabato" in ricaricata.get_profile("C-001")


def test_duplicato_non_salvato(tmp_path):
    memory = PreferenceMemory(tmp_path / "preferences.json")
    assert memory.add("C-001", "Preferisco le email")["salvata"] is True
    assert memory.add("C-001", "preferisco le email")["salvata"] is False
    assert len(memory.get_preferences("C-001")) == 1


def test_pii_rimosse(tmp_path):
    memory = PreferenceMemory(tmp_path / "preferences.json")
    memory.add("C-001", "Scrivimi a mario@example.com o al 333 123 4567")
    profile = memory.get_profile("C-001")
    assert "@" not in profile
    assert "333" not in profile
    assert "email rimossa" in profile
    assert "telefono rimosso" in profile


def test_clear_per_cliente(tmp_path):
    memory = PreferenceMemory(tmp_path / "preferences.json")
    memory.add("C-001", "Preferisco le email")
    memory.add("C-002", "Preferisco il telefono")
    memory.clear("C-001")
    assert memory.get_profile("C-001") == ""
    assert "telefono" in memory.get_profile("C-002")
