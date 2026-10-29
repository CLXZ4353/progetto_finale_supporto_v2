# -*- coding: utf-8 -*-
"""Audit log, ticket e ledger dei rimborsi.

Il ledger e' l'unico punto del progetto che scrive un rimborso. Il grafo lo
chiama solo dopo l'approvazione umana (HITL) e il ledger rivalida comunque
importo, cliente e assenza di duplicati: difesa in profondita', non fiducia
cieca nel modello.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from . import policy
from .config import (
    AUDIT_PATH,
    ORDERS_PATH,
    REFUNDS_PATH,
    TICKETS_PATH,
)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


class AuditLedger:
    """Scritture transazionali minime per la demo (un solo processo)."""

    def __init__(
        self,
        *,
        audit_path: Path | str | None = None,
        refunds_path: Path | str | None = None,
        orders_path: Path | str | None = None,
        tickets_path: Path | str | None = None,
    ):
        self.audit_path = Path(audit_path or AUDIT_PATH)
        self.refunds_path = Path(refunds_path or REFUNDS_PATH)
        self.orders_path = Path(orders_path or ORDERS_PATH)
        self.tickets_path = Path(tickets_path or TICKETS_PATH)
        self._lock = threading.RLock()
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    # --- audit -------------------------------------------------------------
    def log(self, event: str, **fields: Any) -> dict[str, Any]:
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            **{k: v for k, v in fields.items() if v is not None},
        }
        with self._lock:
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return record

    def read_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    # --- ticket ------------------------------------------------------------
    def create_ticket(
        self,
        *,
        customer_id: str,
        reason: str,
        message: str,
        priority: str = "normale",
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            tickets = _read_json(self.tickets_path, {})
            if not isinstance(tickets, dict):
                tickets = {}
            next_number = len(tickets) + 1
            ticket_id = f"TKT-2026-{next_number:04d}"
            while ticket_id in tickets:
                next_number += 1
                ticket_id = f"TKT-2026-{next_number:04d}"
            ticket = {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "reason": reason,
                "message": message[:1000],
                "priority": priority,
                "status": "aperto",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "thread_id": thread_id,
                "assigned_to": "operatore-demo",
            }
            tickets[ticket_id] = ticket
            _write_json(self.tickets_path, tickets)
        self.log(
            "ticket_creato",
            ticket_id=ticket_id,
            customer_id=customer_id,
            reason=reason,
            priority=priority,
            thread_id=thread_id,
        )
        return ticket

    # --- rimborso ---------------------------------------------------------
    @staticmethod
    def _next_refund_id(refunds: dict[str, dict]) -> str:
        highest = 1000
        for record in refunds.values():
            raw = str(record.get("refund_id", ""))
            suffix = raw.rsplit("-", 1)[-1]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"RMB-2026-{highest + 1:04d}"

    def execute_refund(
        self,
        proposal: dict[str, Any],
        approval: dict[str, Any],
        *,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Esegue il rimborso solo se approvato e coerente con la policy.

        Ritorna sempre un dizionario con `eseguito`. Un secondo tentativo sullo
        stesso ordine restituisce `duplicato=True` senza scrivere nulla.
        """
        if not approval.get("approved"):
            self.log("rimborso_rifiutato", order_id=proposal.get("order_id"), thread_id=thread_id)
            return {"eseguito": False, "motivo": "Approvazione umana assente.", "duplicato": False}

        order_id = str(proposal.get("order_id", "")).upper()
        customer_id = str(proposal.get("customer_id", ""))
        amount = round(float(proposal.get("amount", 0.0)), 2)

        with self._lock:
            refunds = _read_json(self.refunds_path, {})
            orders = _read_json(self.orders_path, [])
            if not isinstance(refunds, dict):
                refunds = {}

            if order_id in refunds or any(
                str(r.get("order_id", "")).upper() == order_id for r in refunds.values()
            ):
                existing = refunds.get(order_id) or next(
                    r for r in refunds.values() if str(r.get("order_id", "")).upper() == order_id
                )
                self.log(
                    "rimborso_duplicato_bloccato",
                    order_id=order_id,
                    refund_id=existing.get("refund_id"),
                    thread_id=thread_id,
                )
                return {
                    "eseguito": False,
                    "duplicato": True,
                    "motivo": "Rimborso gia' registrato per questo ordine.",
                    "rimborso": existing,
                }

            order = next(
                (o for o in orders if str(o.get("order_id", "")).upper() == order_id), None
            )
            if order is None:
                self.log("rimborso_errore", order_id=order_id, motivo="ordine inesistente", thread_id=thread_id)
                return {"eseguito": False, "duplicato": False, "motivo": "Ordine inesistente."}

            if str(order.get("customer_id")) != customer_id:
                self.log("rimborso_errore", order_id=order_id, motivo="cliente non coerente", thread_id=thread_id)
                return {
                    "eseguito": False,
                    "duplicato": False,
                    "motivo": "Ordine non associato al cliente della proposta.",
                }

            if order.get("refund_id"):
                self.log(
                    "rimborso_duplicato_bloccato",
                    order_id=order_id,
                    refund_id=order.get("refund_id"),
                    thread_id=thread_id,
                )
                return {
                    "eseguito": False,
                    "duplicato": True,
                    "motivo": "L'ordine risulta gia' rimborsato.",
                    "rimborso": {"refund_id": order.get("refund_id"), "order_id": order_id},
                }

            expected = policy.calculate_refund(order)["total"]
            if abs(expected - amount) > 0.01:
                self.log(
                    "rimborso_errore",
                    order_id=order_id,
                    motivo="importo non coerente",
                    atteso=expected,
                    proposto=amount,
                    thread_id=thread_id,
                )
                return {
                    "eseguito": False,
                    "duplicato": False,
                    "motivo": f"Importo non coerente con la policy (atteso {expected:.2f} EUR).",
                }

            refund_id = self._next_refund_id(refunds)
            record = {
                "refund_id": refund_id,
                "order_id": order_id,
                "customer_id": customer_id,
                "amount": amount,
                "currency": "EUR",
                "reason": proposal.get("reason", "Rimborso approvato da operatore."),
                "approved_by": approval.get("approver", "operatore-demo"),
                "approved_at": datetime.now().isoformat(timespec="seconds"),
                "status": "eseguito",
                "approval_level": approval.get("level", "operatore"),
                "note": approval.get("note", ""),
                "thread_id": thread_id,
            }
            refunds[order_id] = record
            for item in orders:
                if str(item.get("order_id", "")).upper() == order_id:
                    item["refund_id"] = refund_id
                    break
            _write_json(self.refunds_path, refunds)
            _write_json(self.orders_path, orders)

        self.log(
            "rimborso_eseguito",
            order_id=order_id,
            refund_id=refund_id,
            amount=amount,
            approved_by=record["approved_by"],
            level=record["approval_level"],
            thread_id=thread_id,
        )
        return {"eseguito": True, "duplicato": False, "rimborso": record}

    def refunds(self) -> dict[str, dict]:
        data = _read_json(self.refunds_path, {})
        return data if isinstance(data, dict) else {}

    def tickets(self) -> dict[str, dict]:
        data = _read_json(self.tickets_path, {})
        return data if isinstance(data, dict) else {}
