# -*- coding: utf-8 -*-
"""Genera l'ambiente di supporto sintetico di "Casa & Regali".

I dati sono completamente fittizi (nomi, email, ordini, indirizzi) e servono
per una demo riproducibile. I pattern di valore ordine e di reso sono
calibrati sull'EDA del dataset UCI Online Retail, ma nessun record reale
viene copiato qui.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from .config import get_settings

SUPPORT_FILES = (
    "products",
    "customers",
    "orders",
    "refunds",
    "tickets",
    "preferences",
)

PRODUCTS = [
    {"product_id": "P-001", "name": "Candela profumata Vaniglia", "category": "casa", "price": 24.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-002", "name": "Vaso in ceramica Bianco", "category": "complementi", "price": 39.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-003", "name": "Plaid in lana Grigio", "category": "tessili", "price": 49.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-004", "name": "Diffusore ambiente Legno", "category": "casa", "price": 32.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-005", "name": "Cuscino decorativo Foglia", "category": "tessili", "price": 29.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-006", "name": "Cornice in legno Natura", "category": "complementi", "price": 22.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-007", "name": "Candela profumata Cannella", "category": "casa", "price": 15.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-008", "name": "Set tovagliette Lino", "category": "tessili", "price": 34.50, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-009", "name": "Lampada da tavolo Aurora", "category": "complementi", "price": 189.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-010", "name": "Tazza personalizzata con nome", "category": "personalizzato", "price": 18.90, "personalized": True, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-011", "name": "Lampada da terra Luna", "category": "complementi", "price": 749.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-012", "name": "Set skincare Delicato", "category": "igiene", "price": 27.50, "personalized": False, "hygiene": True, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-013", "name": "Buono regalo digitale 25 EUR", "category": "digitale", "price": 25.00, "personalized": False, "hygiene": False, "digital": True, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-014", "name": "Cesto regalo Primavera", "category": "casa", "price": 59.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-015", "name": "Sciarpa in seta Blu", "category": "tessili", "price": 44.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-016", "name": "Orologio da parete Minimal", "category": "complementi", "price": 65.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 24},
    {"product_id": "P-017", "name": "Set candele Aroma", "category": "casa", "price": 36.00, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-018", "name": "Runner tavola Ricamo", "category": "tessili", "price": 28.50, "personalized": False, "hygiene": False, "digital": False, "final_sale": True, "warranty_months": 0},
    {"product_id": "P-019", "name": "Portafoto personalizzato", "category": "personalizzato", "price": 26.90, "personalized": True, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
    {"product_id": "P-020", "name": "Kit piante aromatiche", "category": "casa", "price": 31.90, "personalized": False, "hygiene": False, "digital": False, "final_sale": False, "warranty_months": 0},
]

FIRST_NAMES = [
    "Giulia", "Marco", "Elena", "Luca", "Sara", "Andrea", "Chiara", "Matteo", "Francesca", "Davide",
    "Alessia", "Simone", "Marta", "Federico", "Valentina", "Stefano", "Silvia", "Riccardo", "Anna", "Paolo",
    "Beatrice", "Giorgio", "Ilaria", "Nicola", "Laura", "Fabio", "Serena", "Michele", "Alice", "Roberto",
    "Camilla", "Antonio", "Federica", "Enrico", "Cristina", "Massimo", "Sofia", "Pietro", "Greta", "Claudio",
    "Noemi", "Alberto", "Irene", "Daniele", "Veronica", "Mauro", "Elisa", "Tommaso", "Rebecca", "Gabriele",
]
LAST_NAMES = [
    "Bianchi", "Rossi", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci", "Marino", "Greco", "Bruno",
    "Gallo", "Conti", "De Luca", "Costa", "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti", "Barbieri",
    "Fontana", "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini", "Leone", "Longo",
    "Gentile", "Martinelli", "Vitale", "Lombardo", "Serra", "Coppola", "De Santis", "D'Angelo", "Marchetti", "Parisi",
    "Villa", "Conte", "Ferraro", "Ferri", "Fabbri", "Bianco", "Marini", "Grasso", "Valentini", "Messina",
]

DEMO_CUSTOMER = "C-001"


def _customer(idx: int) -> dict:
    first = FIRST_NAMES[idx % len(FIRST_NAMES)]
    last = LAST_NAMES[(idx * 7 + 3) % len(LAST_NAMES)]
    cid = f"C-{idx + 1:03d}"
    return {
        "customer_id": cid,
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower().replace(' ', '').replace(chr(39), '')}@example.it",
        "phone": f"+39 333 000{idx + 1:04d}",
        "tier": "vip" if idx in {0, 4, 17, 29, 41} else "standard",
        "preferred_contact": "email" if idx % 3 else "telefono",
        "city": ["Milano", "Roma", "Torino", "Bologna", "Firenze", "Napoli", "Padova", "Genova"][idx % 8],
        "joined": f"202{3 + idx % 3}-{1 + idx % 12:02d}-{1 + idx % 27:02d}",
    }


def _item(product: dict, quantity: int = 1) -> dict:
    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "category": product["category"],
        "quantity": quantity,
        "unit_price": product["price"],
        "personalized": product["personalized"],
        "hygiene": product["hygiene"],
        "digital": product["digital"],
        "final_sale": product["final_sale"],
        "warranty_months": product["warranty_months"],
    }


def _order(
    order_id: str,
    customer_id: str,
    order_date: date,
    *,
    delivery_date: date | None,
    status: str,
    items: list[dict],
    shipping: float,
    defective: bool = False,
    refund_id: str | None = None,
    tracking: str | None = None,
) -> dict:
    subtotal = round(sum(i["quantity"] * i["unit_price"] for i in items), 2)
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "order_date": order_date.isoformat(),
        "delivery_date": delivery_date.isoformat() if delivery_date else None,
        "status": status,
        "items": items,
        "subtotal": subtotal,
        "shipping": round(shipping, 2),
        "discount": 0.0,
        "total": round(subtotal + shipping, 2),
        "defective": defective,
        "shipping_refundable": defective,
        "payment_method": "carta",
        "tracking": tracking or f"TRK-{order_id.replace('ORD-', '')}-IT",
        "refund_id": refund_id,
        "notes": "",
    }


def build_support_data(seed: int = 7) -> dict:
    settings = get_settings()
    today = settings.demo_today
    rng = random.Random(seed)
    products = [dict(p) for p in PRODUCTS]
    by_id = {p["product_id"]: p for p in products}
    customers = [_customer(i) for i in range(50)]
    orders: list[dict] = []

    # --- scenari curati (la demo e i test li conoscono per nome) --------------
    orders.append(
        _order(
            "ORD-1001", DEMO_CUSTOMER, today - timedelta(days=13),
            delivery_date=today - timedelta(days=10), status="consegnato",
            items=[_item(by_id["P-001"], 2), _item(by_id["P-002"], 1)], shipping=0.0,
        )
    )
    orders.append(
        _order(
            "ORD-1002", DEMO_CUSTOMER, today - timedelta(days=50),
            delivery_date=today - timedelta(days=45), status="consegnato",
            items=[_item(by_id["P-003"], 1)], shipping=4.90,
        )
    )
    orders.append(
        _order(
            "ORD-1003", DEMO_CUSTOMER, today - timedelta(days=11),
            delivery_date=today - timedelta(days=8), status="consegnato",
            items=[_item(by_id["P-010"], 1)], shipping=4.90,
        )
    )
    orders.append(
        _order(
            "ORD-1004", "C-002", today - timedelta(days=8),
            delivery_date=today - timedelta(days=5), status="consegnato",
            items=[_item(by_id["P-004"], 1)], shipping=4.90,
            refund_id="RMB-2026-1004",
        )
    )
    orders.append(
        _order(
            "ORD-1005", DEMO_CUSTOMER, today - timedelta(days=15),
            delivery_date=today - timedelta(days=12), status="consegnato",
            items=[_item(by_id["P-011"], 1)], shipping=0.0,
        )
    )
    orders.append(
        _order(
            "ORD-1006", DEMO_CUSTOMER, today - timedelta(days=2),
            delivery_date=None, status="in_transito",
            items=[_item(by_id["P-005"], 1)], shipping=4.90,
        )
    )
    orders.append(
        _order(
            "ORD-1007", DEMO_CUSTOMER, today - timedelta(days=10),
            delivery_date=today - timedelta(days=7), status="consegnato",
            items=[_item(by_id["P-012"], 1)], shipping=4.90,
        )
    )
    orders.append(
        _order(
            "ORD-1008", DEMO_CUSTOMER, today - timedelta(days=8),
            delivery_date=today - timedelta(days=5), status="consegnato",
            items=[_item(by_id["P-006"], 1), _item(by_id["P-007"], 1)], shipping=4.90,
            defective=True,
        )
    )

    # --- ordini casuali (200 in totale) --------------------------------------
    statuses = ["consegnato"] * 8 + ["in_transito"] * 1 + ["annullato"] * 1
    for i in range(9, 201):
        order_date = today - timedelta(days=rng.randint(1, 120))
        status = rng.choice(statuses)
        delivery = None
        if status == "consegnato":
            delivery = order_date + timedelta(days=rng.randint(2, 7))
            if delivery > today:
                status = "in_transito"
                delivery = None
        items = [_item(rng.choice(products), rng.randint(1, 2)) for _ in range(rng.randint(1, 3))]
        subtotal = sum(it["quantity"] * it["unit_price"] for it in items)
        shipping = 0.0 if subtotal >= 50 else 4.90
        defective = status == "consegnato" and rng.random() < 0.05
        orders.append(
            _order(
                f"ORD-{1000 + i}", f"C-{rng.randint(1, 50):03d}", order_date,
                delivery_date=delivery, status=status, items=items,
                shipping=shipping, defective=defective,
            )
        )

    # --- ledger iniziale: ORD-1004 + pochi rimborsi casuali -------------------
    refunds: dict[str, dict] = {
        "ORD-1004": {
            "refund_id": "RMB-2026-1004",
            "order_id": "ORD-1004",
            "customer_id": "C-002",
            "amount": 36.90,
            "currency": "EUR",
            "reason": "Reso entro i termini, articolo integro.",
            "approved_by": "operatore-demo",
            "approved_at": (today - timedelta(days=3)).isoformat() + "T10:00:00",
            "status": "eseguito",
        }
    }
    # inserisce qualche rimborso storico per rendere il ledger realistico
    for order in orders[8:]:
        if len(refunds) >= 6:
            break
        if order["status"] == "consegnato" and not order["refund_id"] and rng.random() < 0.015:
            amount = round(order["subtotal"] + order["shipping"], 2)
            rid = f"RMB-2026-{order['order_id'].replace('ORD-', '')}"
            order["refund_id"] = rid
            refunds[order["order_id"]] = {
                "refund_id": rid,
                "order_id": order["order_id"],
                "customer_id": order["customer_id"],
                "amount": amount,
                "currency": "EUR",
                "reason": "Rimborso storico (dati demo).",
                "approved_by": "operatore-demo",
                "approved_at": (today - timedelta(days=rng.randint(10, 80))).isoformat() + "T15:30:00",
                "status": "eseguito",
            }

    return {
        "products": products,
        "customers": customers,
        "orders": orders,
        "refunds": refunds,
        "tickets": {},
        "preferences": {},
    }


def write_support_data(target_dir: Path | str, *, seed: int = 7) -> dict:
    """Scrive i sei JSON della demo in `target_dir` e restituisce i dati."""
    folder = Path(target_dir)
    folder.mkdir(parents=True, exist_ok=True)
    data = build_support_data(seed)
    for name in SUPPORT_FILES:
        (folder / f"{name}.json").write_text(
            json.dumps(data[name], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return data
