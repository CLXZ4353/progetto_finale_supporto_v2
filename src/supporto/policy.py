# -*- coding: utf-8 -*-
"""Policy-as-code di "Casa & Regali".

Questo modulo e' la fonte unica di verita' per le regole di reso e rimborso:
i documenti RAG spiegano le regole, qui vengono applicate in modo
deterministico. Il test `test_policy_docs.py` controlla che i numeri presenti
nei documenti coincidano con le costanti di questo file.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .config import (
    CUSTOMERS_PATH,
    ORDERS_PATH,
    PRODUCTS_PATH,
    REFUNDS_PATH,
)

# --- parametri pubblici (devono coincidere con data/corpus/*.md) -------------
RETURN_WINDOW_DAYS = 30
WARRANTY_MONTHS = 24
REFUND_PROCESSING_DAYS = "5-10"
FREE_SHIPPING_THRESHOLD_EUR = 50.0
SHIPPING_COST_EUR = 4.90
ESCALATION_THRESHOLD_EUR = 500.0
ESCALATION_FIRST_RESPONSE_HOURS = 24
EXCLUDED_CATEGORIES = {
    "personalizzato": "articolo personalizzato",
    "igiene": "articolo di igiene",
    "digitale": "prodotto digitale",
    "fine_serie": "articolo in fine serie",
}

POLICY_REFS = {
    "spedizioni": "spedizioni.md#2",
    "resi": "resi.md#2",
    "rimborsi": "rimborsi.md#1",
    "garanzia": "garanzia.md#1",
    "escalation": "escalation.md#1",
    "catalogo": "catalogo.md#1",
}


def _read_json(path: Path | str | None, default: Any) -> Any:
    if path is None:
        return default
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def load_orders(path: Path | str | None = None) -> list[dict]:
    return _read_json(path or ORDERS_PATH, [])


def load_customers(path: Path | str | None = None) -> list[dict]:
    return _read_json(path or CUSTOMERS_PATH, [])


def load_products(path: Path | str | None = None) -> list[dict]:
    return _read_json(path or PRODUCTS_PATH, [])


def load_refunds(path: Path | str | None = None) -> dict[str, dict]:
    return _read_json(path or REFUNDS_PATH, {})


def get_customer(customer_id: str, path: Path | str | None = None) -> dict | None:
    for c in load_customers(path):
        if c.get("customer_id") == customer_id:
            return c
    return None


def get_product(product_id: str, path: Path | str | None = None) -> dict | None:
    for p in load_products(path):
        if p.get("product_id") == product_id:
            return p
    return None


def find_order(
    order_id: str,
    customer_id: str,
    path: Path | str | None = None,
) -> dict | None:
    """Restituisce l'ordine solo se appartiene al cliente.

    Un ordine esistente ma di un altro cliente restituisce None: il messaggio
    verso l'utente deve essere identico a quello di un ordine inesistente, per
    non rivelare l'esistenza di ordini altrui.
    """
    if not order_id or not customer_id:
        return None
    wanted = str(order_id).strip().upper()
    for order in load_orders(path):
        if str(order.get("order_id", "")).upper() == wanted and order.get("customer_id") == customer_id:
            return order
    return None


def list_orders(customer_id: str, path: Path | str | None = None) -> list[dict]:
    """Restituisce solo gli ordini del cliente, dal piu' recente.

    E' il filtro usato dalla vista tabellare e dalla chat: non esiste una
    variante "tutti gli ordini" accessibile al cliente. L'ordinamento e'
    stabile per data e numero d'ordine.
    """
    if not customer_id:
        return []
    wanted = str(customer_id)
    orders = [
        order
        for order in load_orders(path)
        if str(order.get("customer_id", "")) == wanted
    ]
    return sorted(
        orders,
        key=lambda order: (
            str(order.get("order_date") or ""),
            str(order.get("order_id") or ""),
        ),
        reverse=True,
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def days_since_delivery(order: dict, today: date) -> int | None:
    delivered = _parse_date(order.get("delivery_date"))
    if delivered is None:
        return None
    return (today - delivered).days


def refund_for_order(order_id: str, path: Path | str | None = None) -> dict | None:
    return load_refunds(path).get(str(order_id).strip().upper())


def check_return_eligibility(
    order: dict,
    customer_id: str,
    *,
    today: date,
    refunds_path: Path | str | None = None,
) -> dict:
    """Applica le regole di reso e restituisce un esito spiegabile."""
    order_id = str(order.get("order_id", "")).upper()
    result: dict[str, Any] = {
        "order_id": order_id,
        "eligible": False,
        "reason": "",
        "days_since_delivery": None,
        "excluded_items": [],
        "excluded_categories": [],
        "policy_refs": [POLICY_REFS["resi"]],
    }

    if order.get("customer_id") != customer_id:
        result["reason"] = "Ordine non trovato per questo cliente."
        return result

    if refund_for_order(order_id, refunds_path):
        result["reason"] = "L'ordine risulta gia' rimborsato."
        result["policy_refs"] = [POLICY_REFS["rimborsi"]]
        return result

    if order.get("refund_id"):
        result["reason"] = "L'ordine risulta gia' rimborsato."
        result["policy_refs"] = [POLICY_REFS["rimborsi"]]
        return result

    status = str(order.get("status", "")).lower()
    if status == "annullato":
        result["reason"] = "L'ordine e' stato annullato: non e' possibile avviare un reso."
        return result
    if status != "consegnato":
        result["reason"] = "L'ordine non risulta ancora consegnato: il reso potra' essere richiesto dopo la consegna."
        return result

    days = days_since_delivery(order, today)
    result["days_since_delivery"] = days
    if days is None:
        result["reason"] = "Manca la data di consegna: non posso verificare la finestra di reso."
        return result
    if days < 0:
        result["reason"] = "La data di consegna e' successiva alla data odierna: ordine non ancora consegnato."
        return result
    if days > RETURN_WINDOW_DAYS:
        result["reason"] = (
            f"Sono trascorsi {days} giorni dalla consegna; il reso e' possibile entro "
            f"{RETURN_WINDOW_DAYS} giorni."
        )
        return result

    excluded: list[str] = []
    excluded_categories: set[str] = set()
    for item in order.get("items", []):
        category = str(item.get("category", "")).lower()
        flags = [k for k in EXCLUDED_CATEGORIES if item.get(k)]
        if category in EXCLUDED_CATEGORIES:
            flags.append(category)
        if flags:
            excluded.append(str(item.get("name") or item.get("product_id") or "articolo"))
            excluded_categories.update(EXCLUDED_CATEGORIES[flag] for flag in flags)
    if excluded:
        result["excluded_items"] = sorted(set(excluded))
        result["excluded_categories"] = sorted(excluded_categories)
        result["reason"] = (
            "Il reso non e' disponibile per: " + ", ".join(result["excluded_items"]) +
            ". Sono esclusi gli articoli personalizzati, di igiene, digitali e in fine serie."
        )
        result["policy_refs"] = [POLICY_REFS["resi"], POLICY_REFS["catalogo"]]
        return result

    result["eligible"] = True
    result["reason"] = (
        f"Reso entro la finestra di {RETURN_WINDOW_DAYS} giorni "
        f"({days} giorni dalla consegna)."
    )
    return result


def calculate_refund(order: dict, *, requires_escalation_threshold: float = ESCALATION_THRESHOLD_EUR) -> dict:
    """Calcola l'importo in modo deterministico. Non decide l'idoneita'."""
    items_total = 0.0
    for item in order.get("items", []):
        items_total += float(item.get("quantity", 0)) * float(item.get("unit_price", 0.0))
    discount = float(order.get("discount", 0.0) or 0.0)
    shipping = float(order.get("shipping", 0.0) or 0.0)
    shipping_refund = shipping if (order.get("defective") or order.get("shipping_refundable")) else 0.0
    total = max(0.0, round(items_total - discount + shipping_refund, 2))
    return {
        "order_id": str(order.get("order_id", "")).upper(),
        "items_total": round(items_total, 2),
        "discount": round(discount, 2),
        "shipping_refund": round(shipping_refund, 2),
        "total": total,
        "currency": "EUR",
        "threshold_eur": requires_escalation_threshold,
        "requires_escalation": total > requires_escalation_threshold,
        "policy_refs": [POLICY_REFS["rimborsi"], POLICY_REFS["resi"]],
    }


def format_eur(value: float | int | str) -> str:
    return f"{float(value):.2f} EUR".replace(".", ",")


def policy_snapshot() -> dict:
    """Valori mostrati nella UI e usati dai test di coerenza dei documenti."""
    return {
        "return_window_days": RETURN_WINDOW_DAYS,
        "warranty_months": WARRANTY_MONTHS,
        "refund_processing_days": REFUND_PROCESSING_DAYS,
        "free_shipping_threshold_eur": FREE_SHIPPING_THRESHOLD_EUR,
        "shipping_cost_eur": SHIPPING_COST_EUR,
        "escalation_threshold_eur": ESCALATION_THRESHOLD_EUR,
        "escalation_first_response_hours": ESCALATION_FIRST_RESPONSE_HOURS,
        "excluded_categories": sorted(EXCLUDED_CATEGORIES),
    }
