# -*- coding: utf-8 -*-
"""Grafo a un solo passaggio di tool: agent → tools → respond → finalize.

L'LLM sceglie il tool; il tool esegue e restituisce un esito; un secondo passo
LLM, senza tool, scrive la risposta finale a partire dall'esito. Se non servono
tool, il percorso è agent → finalize. È il ciclo del Laboratorio 6 senza catene
di tool, supervisore, review/reflection o fallback semantico: il modello sceglie
i tool e scrive le risposte; il codice impone solo i vincoli di dominio (policy,
privacy, HITL, ledger).
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from .audit import AuditLedger
from .config import Settings, get_settings
from .memory import PreferenceMemory
from .models import final_reasoning_effort, get_chat_model
from .prompts import FINAL_ANSWER_PROMPT, SYSTEM_PROMPT
from .tools import make_tools
from .turns import last_human_index, message_text, sources_from_messages, tool_messages

RECURSION_LIMIT = 20


class SupportState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    customer_id: str
    final_answer: str
    sources: list[dict[str, Any]]


def new_thread_id() -> str:
    return uuid.uuid4().hex


def _format_tool_result(message: ToolMessage) -> str:
    """Trasforma il risultato di un tool in testo leggibile per la risposta."""
    name = str(message.name or "tool")
    text = message_text(message)
    if name == "cerca_policy":
        try:
            payload = json.loads(message.content or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        else:
            text = str(payload.get("contesto") or text)
    return f"Tool: {name}\n{text}"


def build_graph(
    settings: Settings | None = None,
    *,
    model: Any | None = None,
    ledger: AuditLedger | None = None,
    memory: PreferenceMemory | None = None,
    checkpointer: Any | None = None,
):
    settings = settings or get_settings()
    ledger = ledger or AuditLedger()
    memory = memory or PreferenceMemory()
    tools = make_tools(ledger, memory, settings)
    injected_model = model is not None
    model = model or get_chat_model(settings)
    # Con LFM3 il reasoning aiuta la scelta del tool, ma sul passo finale può
    # esaurire il contesto e lasciare `content` vuoto (finish_reason=length).
    # La risposta finale è solo copia dei risultati: reasoning disattivato.
    final_model = model
    effort = final_reasoning_effort(settings)
    if not injected_model and effort:
        final_model = get_chat_model(settings, reasoning_effort=effort)
    bound = model.bind_tools(tools)

    def agent_node(state: SupportState) -> dict[str, Any]:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        response = bound.invoke(messages)
        return {"messages": [response]}

    def route_agent(state: SupportState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else "finalize"

    def respond_node(state: SupportState) -> dict[str, Any]:
        """Scrive la risposta finale a partire dagli esiti dei tool del turno.

        Il modello è chiamato senza tool: non può avviare nuove azioni, deve
        solo raccontare al cliente quello che i tool hanno restituito.
        """
        messages = state["messages"]
        request = ""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                request = message_text(message)
                break
        results = "\n\n".join(
            _format_tool_result(message) for message in tool_messages(messages)
        )
        response = final_model.invoke(
            [
                SystemMessage(content=FINAL_ANSWER_PROMPT),
                HumanMessage(
                    content=(
                        f"Richiesta del cliente: {request}\n\n"
                        f"Risultati dei tool:\n{results}"
                    )
                ),
            ]
        )
        return {"messages": [response]}

    def finalize(state: SupportState) -> dict[str, Any]:
        messages = list(state["messages"])
        start = last_human_index(messages)
        answer = ""
        # Solo il turno corrente: una risposta vuota non deve mai far
        # riemergere l'answer del turno precedente.
        for message in reversed(messages[start:]):
            if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
                answer = message_text(message)
                if answer:
                    break
        if not answer:
            answer = (
                "Non ho potuto completare la richiesta. Posso aprire un ticket "
                "per un operatore."
            )
        sources = sources_from_messages(messages)
        tool_names = [
            str(message.name)
            for message in messages[start:]
            if isinstance(message, ToolMessage) and message.name
        ]
        ledger.log(
            "turno",
            customer_id=state.get("customer_id"),
            tools=tool_names,
            answer=answer[:500],
        )
        return {"final_answer": answer, "sources": sources}

    builder = StateGraph(SupportState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("respond", respond_node)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent", route_agent, {"tools": "tools", "finalize": "finalize"}
    )
    builder.add_edge("tools", "respond")
    builder.add_edge("respond", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def _config(thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }


def start_turn(graph, thread_id: str, customer_id: str, message: str):
    return graph.invoke(
        {
            "messages": [HumanMessage(content=message)],
            "customer_id": customer_id,
            "final_answer": "",
            "sources": [],
        },
        _config(thread_id),
    )


def resume_turn(graph, thread_id: str, decision: dict[str, Any]):
    return graph.invoke(Command(resume=decision), _config(thread_id))


def pending_interrupt(result: dict[str, Any] | None) -> dict[str, Any] | None:
    interrupts = (result or {}).get("__interrupt__") or []
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    return value if isinstance(value, dict) else {"value": value}


def state_values(graph, thread_id: str) -> dict[str, Any]:
    return dict(graph.get_state(_config(thread_id)).values)


def latest_answer(graph, thread_id: str) -> str:
    state = state_values(graph, thread_id)
    if state.get("final_answer"):
        return str(state["final_answer"])
    for message in reversed(state.get("messages") or []):
        if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
            return message_text(message)
    return ""
