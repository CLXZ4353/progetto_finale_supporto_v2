# -*- coding: utf-8 -*-
"""CLI di demo per il servizio clienti Casa & Regali.

Uso:
    python cli.py
    python cli.py --backend gemini
    python cli.py --customer C-002 --model unsloth/llama-3.2-3b-instruct
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from supporto import policy  # noqa: E402
from supporto.audit import AuditLedger  # noqa: E402
from supporto.agent import (  # noqa: E402
    build_graph,
    new_thread_id,
    pending_interrupt,
    resume_turn,
    start_turn,
    state_values,
)
from supporto.config import get_settings  # noqa: E402


def _last_turn(state: dict) -> list:
    messages = state.get("messages") or []
    start = 0
    for index, message in enumerate(messages):
        if getattr(message, "type", "") == "human":
            start = index
    return messages[start:]


def _tools_used(state: dict) -> list[str]:
    return [
        str(message.name)
        for message in _last_turn(state)
        if getattr(message, "type", "") == "tool" and getattr(message, "name", "")
    ]


def _print_sources(state: dict) -> None:
    sources = state.get("sources") or []
    if not sources:
        return
    print("  fonti:")
    for source in sources:
        print(f"   - {source.get('id')} {source.get('source')} ({source.get('section') or 'sezione'})")


def _print_state(state: dict) -> None:
    print("\n--- stato turno ---")
    print("cliente:", state.get("customer_id"), "| tool:", _tools_used(state) or "nessuno")
    print("risposta:", state.get("final_answer") or "(nessuna)")
    _print_sources(state)


def _ask_yes_no(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer in {"s", "si", "sì", "y", "yes"}


def _handle_interrupts(graph, thread_id: str, result: dict) -> dict:
    while True:
        pending = pending_interrupt(result)
        if not pending:
            return result
        if pending.get("type") != "refund_approval":
            print("\nInterrupt non riconosciuto:", pending)
            return result

        proposal = pending.get("proposal") or {}
        level = proposal.get("level", "operatore")
        amount = policy.format_eur(proposal.get("amount", 0))
        print("\n=== APPROVAZIONE UMANA RICHIESTA ===")
        print(f"Ordine {proposal.get('order_id')} | importo {amount} | livello {level}")
        print("Motivo:", proposal.get("reason", ""))
        print("Nessun rimborso è stato eseguito finora.")

        approved = _ask_yes_no("Approvare il rimborso? [s/N] ")
        note = ""
        if approved:
            note = input("Nota per l'audit (facoltativa): ").strip()
            if level == "responsabile" and not _ask_yes_no(
                "Importo > 500 EUR: approvi come responsabile? [s/N] "
            ):
                approved = False
                note = "Approvazione del responsabile mancante."
        result = resume_turn(
            graph,
            thread_id,
            {
                "approved": approved,
                "approver": "responsabile-cli" if level == "responsabile" else "operatore-cli",
                "level": level,
                "note": note,
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo CLI Casa & Regali")
    parser.add_argument("--customer", default="C-001", help="Customer ID della sessione")
    parser.add_argument(
        "--backend", default=None, choices=["local", "gemini"], help="Backend del modello"
    )
    parser.add_argument("--model", default=None, help="Modello LM Studio (backend locale)")
    parser.add_argument("--thread", default=None, help="Thread ID (default: nuova sessione)")
    args = parser.parse_args()

    settings = get_settings()
    if args.backend:
        settings.model_backend = args.backend
    if args.model:
        settings.lm_studio_model = args.model
    if settings.model_backend == "gemini" and not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY assente: configura il .env o usa --backend local.")

    customer = policy.get_customer(args.customer)
    if customer is None:
        raise SystemExit(f"Cliente {args.customer} non trovato.")

    ledger = AuditLedger()
    graph = build_graph(settings, ledger=ledger)
    thread_id = args.thread or new_thread_id()

    print("=" * 68)
    print("Casa & Regali - assistenza clienti (demo)")
    print(f"Cliente: {customer['name']} ({args.customer}) | modello: {settings.model_label}")
    print(f"Thread: {thread_id}")
    print("Comandi: /nuova  /stato  /fonti  /audit  /esci")
    print("=" * 68)

    while True:
        try:
            message = input("\nTu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArrivederci.")
            break
        if not message:
            continue
        if message.lower() in {"/esci", "esci", "exit", "quit"}:
            print("Arrivederci.")
            break
        if message.lower() == "/nuova":
            thread_id = new_thread_id()
            print(f"Nuova conversazione: {thread_id}")
            continue
        if message.lower() == "/stato":
            _print_state(state_values(graph, thread_id))
            continue
        if message.lower() == "/fonti":
            _print_sources(state_values(graph, thread_id))
            continue
        if message.lower() == "/audit":
            for record in ledger.read_audit(12):
                print(
                    record.get("ts"), record.get("event"),
                    record.get("order_id", ""), record.get("ticket_id", ""),
                )
            continue

        try:
            result = start_turn(graph, thread_id, args.customer, message)
            result = _handle_interrupts(graph, thread_id, result)
            state = state_values(graph, thread_id)
            print("\nAssistente>", state.get("final_answer") or "(nessuna risposta finale)")
            print(f"\n[tool usati: {_tools_used(state) or 'nessuno'}]")
            _print_sources(state)
        except Exception as exc:  # noqa: BLE001 - la CLI deve restare viva
            print(f"\nErrore: {type(exc).__name__}: {exc}")
            print("Suggerimento: verifica che LM Studio sia avviato e il modello caricato.")


if __name__ == "__main__":
    main()
