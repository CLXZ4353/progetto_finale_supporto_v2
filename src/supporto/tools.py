# -*- coding: utf-8 -*-
"""Tool LangChain del servizio clienti.

Sono tutti read-only tranne `proponi_rimborso`, che sospende il turno con
`interrupt()` e scrive nel ledger solo dopo l'approvazione umana.
Il customer_id arriva dallo stato del grafo tramite `ToolRuntime`: il modello
non può scegliere di quale cliente parlare.
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import interrupt

from . import policy
from .audit import AuditLedger
from .config import get_settings
from .corpus import format_context, retrieve, source_payload
from .memory import PreferenceMemory
from .turns import last_human_text

PRIVACY_MESSAGE = (
    "Non trovo l'ordine {order_id} tra quelli associati a questo profilo. "
    "Controlla il numero e riprova: per privacy non posso mostrare ordini di altri clienti."
)

STATUS_LABELS = {
    "consegnato": "Consegnato",
    "in_transito": "In transito",
    "in_preparazione": "In preparazione",
    "annullato": "Annullato",
}


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _customer(runtime: ToolRuntime) -> str:
    return str((runtime.state or {}).get("customer_id") or "")


def _thread_id(runtime: ToolRuntime) -> str | None:
    configurable = (runtime.config or {}).get("configurable") or {}
    return configurable.get("thread_id")


def _status_label(status: Any) -> str:
    key = str(status or "").lower()
    return STATUS_LABELS.get(key, key.replace("_", " ").capitalize() or "—")


def _public_row(order: dict) -> dict:
    items = "; ".join(
        f"{item.get('name')} x{item.get('quantity')}" for item in order.get("items", [])
    )
    return {
        "Ordine": order.get("order_id") or "—",
        "Data": order.get("order_date") or "—",
        "Stato": _status_label(order.get("status")),
        "Consegna": order.get("delivery_date") or "—",
        "Articoli": items or "—",
        "Totale": policy.format_eur(order.get("total") or 0),
        "Tracking": order.get("tracking") or "—",
        "Rimborso": order.get("refund_id") or "—",
    }


def _markdown_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = [str(row[h]).replace("|", "\\|") for h in headers]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _format_order(order: dict) -> str:
    lines = [
        f"Ordine {order.get('order_id')}",
        f"Data ordine: {order.get('order_date') or '—'} | "
        f"Consegna: {order.get('delivery_date') or '—'} | "
        f"Stato: {_status_label(order.get('status'))}",
        "Articoli:",
    ]
    for item in order.get("items", []):
        lines.append(
            f"- {item.get('quantity')}x {item.get('name')}: "
            f"{policy.format_eur(item.get('unit_price') or 0)} cad."
        )
    lines.extend(
        [
            f"Totale: {policy.format_eur(order.get('total') or 0)}",
            f"Tracking: {order.get('tracking') or 'non disponibile'}",
            (
                f"Rimborso: già eseguito ({order.get('refund_id')})"
                if order.get("refund_id")
                else "Rimborso: nessuno"
            ),
        ]
    )
    return "\n".join(lines)


def make_tools(ledger: AuditLedger, memory: PreferenceMemory) -> list:
    """Crea i tool legati alle dipendenze della sessione/app."""

    @tool
    def cerca_policy(
        query: Annotated[str, "Domanda o parole chiave su spedizioni, resi, rimborsi, garanzia, pagamenti, privacy, catalogo."],
        runtime: ToolRuntime,
    ) -> str:
        """Cerca nelle policy scritte di Casa & Regali e restituisce passaggi con fonti [S1], [S2].

        Usalo per domande generali su spedizioni, resi, rimborsi, garanzia,
        pagamenti, privacy e catalogo; non per lo stato di un ordine specifico.
        La ricerca unisce la query del modello alla richiesta originale del
        cliente, così i termini specifici non vanno persi.
        """
        messages = (runtime.state or {}).get("messages") or []
        search = f"{query} {last_human_text(messages)}".strip()
        docs = retrieve(search, k=3)
        return _json(
            {"contesto": format_context(docs), "fonti": source_payload(docs)}
        )

    @tool
    def stato_ordine(
        order_id: Annotated[str, "Numero ordine nel formato ORD-1234."],
        runtime: ToolRuntime,
    ) -> str:
        """Restituisce stato, articoli, totale, tracking e rimborso di un ordine del cliente.

        Richiede un numero d'ordine esistente nel formato ORD-1234. Se l'ordine
        non esiste o appartiene a un altro cliente, restituisce lo stesso
        messaggio di non trovato (privacy).
        """
        customer_id = _customer(runtime)
        order = policy.find_order(order_id, customer_id)
        if order is None:
            ledger.log(
                "privacy_accesso_negato",
                order_id=str(order_id).upper(),
                customer_id=customer_id,
                tool="stato_ordine",
            )
            return PRIVACY_MESSAGE.format(order_id=str(order_id).upper())
        return _format_order(order)

    @tool
    def elenca_ordini(runtime: ToolRuntime) -> str:
        """Elenca gli ordini del profilo della sessione, dal più recente.

        Restituisce anche una tabella Markdown pronta da mostrare. Non esiste
        una vista degli ordini di altri clienti.
        """
        orders = policy.list_orders(_customer(runtime))
        rows = [_public_row(order) for order in orders]
        if not rows:
            return "Non risultano ordini associati a questo profilo."
        return f"Ordini del profilo ({len(rows)}):\n\n{_markdown_table(rows)}"

    @tool
    def verifica_reso(
        order_id: Annotated[str, "Numero ordine nel formato ORD-1234."],
        runtime: ToolRuntime,
    ) -> str:
        """Verifica se un ordine specifico è idoneo al reso secondo la policy.

        Richiede un numero d'ordine esistente. Controlla consegna, finestra di
        30 giorni, esclusioni e rimborsi già eseguiti. Restituisce un esito
        leggibile con i giorni trascorsi. Non usarlo per domande generali.
        """
        settings = get_settings()
        customer_id = _customer(runtime)
        order = policy.find_order(order_id, customer_id)
        if order is None:
            ledger.log(
                "privacy_accesso_negato",
                order_id=str(order_id).upper(),
                customer_id=customer_id,
                tool="verifica_reso",
            )
            return PRIVACY_MESSAGE.format(order_id=str(order_id).upper())

        eligibility = policy.check_return_eligibility(
            order, customer_id, today=settings.demo_today
        )
        lines = [
            f"Esito definitivo per l'ordine {eligibility['order_id']}: "
            f"{'idoneo' if eligibility['eligible'] else 'non idoneo'} al reso.",
            f"Finestra di reso: {policy.RETURN_WINDOW_DAYS} giorni dalla consegna.",
            eligibility["reason"],
        ]
        if eligibility["days_since_delivery"] is not None:
            lines.append(
                f"Giorni dalla consegna: {eligibility['days_since_delivery']}."
            )
        if eligibility["excluded_items"]:
            lines.append("Articoli esclusi: " + ", ".join(eligibility["excluded_items"]) + ".")
        if eligibility["excluded_categories"]:
            lines.append(
                "Categoria esclusa: "
                + ", ".join(eligibility["excluded_categories"])
                + "."
            )
        if order.get("defective"):
            lines.append(
                "L'articolo è segnalato come difettoso: la spedizione di ritorno è a "
                "carico nostro e puoi scegliere tra reso/rimborso o sostituzione."
            )
        return "\n".join(lines)

    @tool
    def proponi_rimborso(
        order_id: Annotated[str, "Numero ordine nel formato ORD-1234."],
        runtime: ToolRuntime,
    ) -> str:
        """Prepara la proposta di rimborso e chiede l'approvazione di un operatore.

        Usalo solo quando il cliente chiede un rimborso e fornisce un numero
        d'ordine. Se l'ordine non è idoneo non apre alcuna approvazione. Se è
        idoneo, sospende il turno con HITL: il rimborso viene scritto nel ledger
        solo dopo un'approvazione esplicita.
        """
        settings = get_settings()
        customer_id = _customer(runtime)
        order = policy.find_order(order_id, customer_id)
        if order is None:
            ledger.log(
                "privacy_accesso_negato",
                order_id=str(order_id).upper(),
                customer_id=customer_id,
                tool="proponi_rimborso",
            )
            return PRIVACY_MESSAGE.format(order_id=str(order_id).upper())
        eligibility = policy.check_return_eligibility(
            order, customer_id, today=settings.demo_today
        )
        if not eligibility["eligible"]:
            return (
                f"Rimborso non eseguito per {str(order_id).upper()}: "
                f"l'ordine non e' idoneo al rimborso. {eligibility['reason']}"
            )
        refund = policy.calculate_refund(order)
        proposal = {
            "order_id": str(order.get("order_id", "")).upper(),
            "customer_id": customer_id,
            "amount": refund["total"],
            "currency": "EUR",
            "reason": eligibility["reason"],
            "items": [
                f"{item.get('quantity')}x {item.get('name')}"
                for item in order.get("items", [])
            ],
            "requires_escalation": refund["requires_escalation"],
            "level": "responsabile" if refund["requires_escalation"] else "operatore",
        }
        decision = interrupt({"type": "refund_approval", "proposal": proposal})
        if not isinstance(decision, dict) or not decision.get("approved"):
            ledger.log(
                "rimborso_rifiutato",
                order_id=proposal["order_id"],
                customer_id=customer_id,
                thread_id=_thread_id(runtime),
            )
            return (
                f"Rimborso rifiutato dall'operatore: nessun importo è stato "
                f"accreditato per {proposal['order_id']}."
            )
        decision = {**decision, "level": decision.get("level") or proposal["level"]}
        result = ledger.execute_refund(
            proposal, decision, thread_id=_thread_id(runtime)
        )
        if result.get("eseguito"):
            record = result["rimborso"]
            return (
                f"Rimborso eseguito: {proposal['order_id']}, importo "
                f"{policy.format_eur(record['amount'])}, pratica {record['refund_id']}."
            )
        if result.get("duplicato"):
            return (
                f"Rimborso non eseguito per {proposal['order_id']}: "
                f"{result.get('motivo', 'rimborso già registrato')}."
            )
        return f"Rimborso non eseguito per {proposal['order_id']}: {result.get('motivo', 'errore')}."

    @tool
    def apri_ticket(
        motivo: Annotated[str, "Motivo del ticket, con il testo del cliente."],
        runtime: ToolRuntime,
    ) -> str:
        """Apre un ticket per un operatore umano e restituisce il numero TKT-....

        Usalo solo se il cliente chiede esplicitamente una persona, fa un
        reclamo o segnala un'urgenza. Non usarlo per preferenze o domande
        informative.
        """
        text = str(motivo or "").strip() or "Richiesta di assistenza"
        lower = text.lower()
        priority = "alta" if any(
            word in lower for word in ("responsabile", "reclamo", "vergognoso", "urgenza")
        ) else "normale"
        ticket = ledger.create_ticket(
            customer_id=_customer(runtime),
            reason=text[:200],
            message=text,
            priority=priority,
            thread_id=_thread_id(runtime),
        )
        return (
            f"Ticket {ticket['ticket_id']} aperto (priorità {priority}, "
            f"stato {ticket['status']}). Un operatore prende in carico la richiesta "
            f"entro {policy.ESCALATION_FIRST_RESPONSE_HOURS} ore lavorative."
        )

    @tool
    def ricorda_preferenza(
        testo: Annotated[str, "Preferenza da ricordare, nelle parole del cliente."],
        runtime: ToolRuntime,
    ) -> str:
        """Salva una preferenza durevole solo se il cliente lo chiede esplicitamente.

        Usalo solo se il cliente dice "ricorda" o "tieni presente". Non usarlo
        per una preferenza espressa di passaggio.
        """
        result = memory.add(_customer(runtime), testo)
        if result.get("salvata"):
            return f"Preferenza salvata: {result.get('text')}."
        return f"Preferenza non salvata: {result.get('motivo', 'motivo sconosciuto')}."

    return [
        cerca_policy,
        stato_ordine,
        elenca_ordini,
        verifica_reso,
        proponi_rimborso,
        apri_ticket,
        ricorda_preferenza,
    ]
