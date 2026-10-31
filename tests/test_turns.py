# -*- coding: utf-8 -*-
"""Test degli helper condivisi per messaggi e turni."""
from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from supporto.turns import (
    extract_answer,
    last_human_index,
    last_human_text,
    message_text,
    sources_from_messages,
    tool_messages,
    tool_names,
    turn_messages,
)


def test_message_text_gestisce_stringhe_e_blocchi():
    assert message_text(AIMessage(content="  ciao  ")) == "ciao"
    assert (
        message_text(
            AIMessage(
                content=[
                    {"type": "text", "text": "prima"},
                    {"type": "tool_use", "text": "ignorato"},
                    "seconda",
                ]
            )
        )
        == "prima\nseconda"
    )


def test_turn_messages_parte_dall_ultima_richiesta():
    messages = [
        HumanMessage(content="prima"),
        AIMessage(content="risposta vecchia"),
        HumanMessage(content="seconda"),
        AIMessage(content="risposta nuova"),
    ]
    assert last_human_index(messages) == 2
    assert [message_text(message) for message in turn_messages(messages)] == [
        "seconda",
        "risposta nuova",
    ]
    assert last_human_text(messages) == "seconda"


def test_tool_names_e_tool_messages_solo_ultimo_turno():
    vecchio = ToolMessage(
        content="vecchio", name="stato_ordine", tool_call_id="old"
    )
    nuovo = ToolMessage(
        content="nuovo", name="elenca_ordini", tool_call_id="new"
    )
    messages = [
        HumanMessage(content="prima"),
        vecchio,
        HumanMessage(content="seconda"),
        nuovo,
    ]
    assert [message.name for message in tool_messages(messages)] == ["elenca_ordini"]
    assert tool_names(messages) == ["elenca_ordini"]


def test_sources_from_messages_deduplica_e_limita():
    fonte = {"source": "resi.md", "chunk_id": "resi.md#1", "section": "Resi"}
    payload = {"fonti": [fonte, fonte]}
    messages = [
        HumanMessage(content="domanda"),
        ToolMessage(
            content=json.dumps(payload), name="cerca_policy", tool_call_id="call-1"
        ),
    ]
    sources = sources_from_messages(messages)
    assert sources == [fonte]


def test_extract_answer_rimuove_il_ragionamento():
    testo = (
        'Se il risultato contiene "Tracking", dobbiamo copiarlo.\n'
        "<risposta>Il tuo ordine è consegnato.</risposta>\n"
        "Ho risposto in italiano."
    )
    assert extract_answer(testo) == "Il tuo ordine è consegnato."


def test_extract_answer_senza_tag_lascia_il_testo():
    assert extract_answer("  Il tuo ordine è consegnato.  ") == (
        "Il tuo ordine è consegnato."
    )
    assert extract_answer("<risposta>Risposta senza chiusura") == (
        "Risposta senza chiusura"
    )
