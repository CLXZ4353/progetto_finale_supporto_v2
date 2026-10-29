# -*- coding: utf-8 -*-
"""Helper condivisi per leggere i messaggi e il turno corrente.

Il grafo, i tool, la CLI, la UI e la valutazione devono interpretare allo
stesso modo l'ultima richiesta del cliente e i risultati dei tool. Queste
funzioni evitano che ogni punto del progetto reimplementi la stessa logica.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage


def message_text(message: BaseMessage | Any) -> str:
    """Estrae il testo da un messaggio, anche quando il contenuto è a blocchi."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type", "text") == "text":
            parts.append(str(block.get("text", "")))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(part for part in parts if part).strip()


def last_human_index(messages: list[BaseMessage]) -> int:
    """Indice dell'ultimo messaggio umano; 0 se non ce ne sono."""
    start = 0
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            start = index
    return start


def turn_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Messaggi dell'ultimo turno, dalla richiesta del cliente in poi."""
    return list(messages[last_human_index(messages) :])


def last_human_text(messages: list[BaseMessage]) -> str:
    """Testo dell'ultima richiesta del cliente."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message_text(message)
    return ""


def tool_messages(messages: list[BaseMessage]) -> list[ToolMessage]:
    """Risultati dei tool prodotti nell'ultimo turno."""
    return [
        message
        for message in turn_messages(messages)
        if isinstance(message, ToolMessage)
    ]


def tool_names(messages: list[BaseMessage]) -> list[str]:
    """Nomi dei tool usati nell'ultimo turno, nell'ordine di esecuzione."""
    return [str(message.name) for message in tool_messages(messages) if message.name]


def sources_from_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Raccoglie le fonti restituite dai tool di policy nell'ultimo turno."""
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for message in tool_messages(messages):
        try:
            payload = json.loads(message.content or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        for source in payload.get("fonti") or []:
            key = (str(source.get("source", "")), str(source.get("chunk_id", "")))
            if key in seen:
                continue
            seen.add(key)
            sources.append(source)
    return sources[:6]
