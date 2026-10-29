# -*- coding: utf-8 -*-
"""Esegue gli scenari di valutazione e produce report JSON/Markdown.

Esempi:
    python eval/run_eval.py --backend local
    python eval/run_eval.py --backend local --model lfm3-1.2b
    python eval/run_eval.py --backend local --scenario rimborso_standard
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supporto import policy  # noqa: E402
from supporto.agent import (  # noqa: E402
    build_graph,
    new_thread_id,
    pending_interrupt,
    resume_turn,
    start_turn,
    state_values,
)
from supporto.audit import AuditLedger  # noqa: E402
from supporto.config import get_settings  # noqa: E402
from supporto.memory import PreferenceMemory  # noqa: E402
from supporto.support_data import build_support_data  # noqa: E402
from supporto.turns import tool_names  # noqa: E402

from scenarios import SCENARIOS  # noqa: E402

RESULTS_DIR = ROOT / "eval" / "results"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("utf-8")
    return text.lower().replace("e'", "e").replace("\u2019", "'")


def check_groups(text: str, groups: list[list[str]] | None) -> list[str]:
    normalized = norm(text)
    return [
        "manca: " + " | ".join(group)
        for group in groups or []
        if not any(norm(alternative) in normalized for alternative in group)
    ]


def tools_after(state: dict, tool_name: str) -> list[str]:
    messages = state.get("messages") or []
    index = None
    for position, message in enumerate(messages):
        if getattr(message, "type", "") == "tool" and getattr(message, "name", "") == tool_name:
            index = position
    if index is None:
        return []
    return [
        str(message.name)
        for message in messages[index + 1 :]
        if getattr(message, "type", "") == "tool" and getattr(message, "name", "")
    ]


def proposal_text(pending: dict) -> str:
    proposal = pending.get("proposal") or {}
    return " ".join(
        str(part)
        for part in (
            proposal.get("order_id"),
            policy.format_eur(proposal.get("amount", 0)),
            proposal.get("reason"),
            proposal.get("level"),
            ", ".join(proposal.get("items") or []),
            pending.get("contesto"),
        )
        if part
    )


def run_scenario(scenario: dict, settings) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix=f"eval_{scenario['id']}_"))
    original_paths = (
        policy.ORDERS_PATH,
        policy.CUSTOMERS_PATH,
        policy.PRODUCTS_PATH,
        policy.REFUNDS_PATH,
    )
    started = time.perf_counter()
    try:
        data = build_support_data()
        for name in ("orders", "customers", "products", "refunds", "tickets", "preferences"):
            (workdir / f"{name}.json").write_text(
                json.dumps(data[name], ensure_ascii=False, indent=2), encoding="utf-8"
            )
        policy.ORDERS_PATH = workdir / "orders.json"
        policy.CUSTOMERS_PATH = workdir / "customers.json"
        policy.PRODUCTS_PATH = workdir / "products.json"
        policy.REFUNDS_PATH = workdir / "refunds.json"

        ledger = AuditLedger(
            audit_path=workdir / "audit.jsonl",
            refunds_path=workdir / "refunds.json",
            orders_path=workdir / "orders.json",
            tickets_path=workdir / "tickets.json",
        )
        memory = PreferenceMemory(workdir / "preferences.json")
        graph = build_graph(settings, ledger=ledger, memory=memory)
        thread_id = new_thread_id()
        initial_refunds = len(ledger.refunds())

        result = start_turn(graph, thread_id, scenario["customer"], scenario["message"])
        state = state_values(graph, thread_id)
        pending = pending_interrupt(result)
        tools = tool_names(state.get("messages") or [])
        failures: list[str] = []

        expected_interrupt = scenario.get("interrupt")
        actual_interrupt = pending.get("type") if pending else None
        if expected_interrupt != actual_interrupt:
            failures.append(f"interrupt atteso {expected_interrupt}, ottenuto {actual_interrupt}")

        if pending:
            failures.extend(check_groups(proposal_text(pending), scenario.get("proposal_must")))
            expected_level = scenario.get("level")
            level = (pending.get("proposal") or {}).get("level")
            if expected_level and level != expected_level:
                failures.append(f"livello atteso {expected_level}, ottenuto {level}")
            if len(ledger.refunds()) != initial_refunds:
                failures.append("rimborso scritto prima dell'approvazione HITL")

        final_answer = state.get("final_answer", "")
        refund_executed = False
        pending_after = None
        if pending and expected_interrupt == actual_interrupt and scenario.get("approve") is not None:
            proposal = pending.get("proposal") or {}
            decision = {
                "approved": bool(scenario["approve"]),
                "approver": "responsabile-eval" if proposal.get("level") == "responsabile" else "operatore-eval",
                "level": proposal.get("level", "operatore"),
                "note": "valutazione automatica",
            }
            result = resume_turn(graph, thread_id, decision)
            state = state_values(graph, thread_id)
            tools = tool_names(state.get("messages") or [])
            final_answer = state.get("final_answer", "")
            pending_after = pending_interrupt(result)
            if pending_after:
                failures.append(f"interrupt inatteso dopo l'approvazione: {pending_after.get('type')}")
            refund_executed = len(ledger.refunds()) > initial_refunds

        tools = tool_names(state.get("messages") or [])
        missing = [name for name in scenario.get("tools") or [] if name not in tools]
        if missing:
            failures.append(f"tool attesi mancanti: {missing}; usati: {tools}")
        forbidden_tools = [
            name for name in scenario.get("forbidden_tools") or [] if name in tools
        ]
        if forbidden_tools:
            failures.append(f"tool vietati usati: {forbidden_tools}")

        if not pending:
            refund_executed = len(ledger.refunds()) > initial_refunds

        failures.extend(check_groups(final_answer, scenario.get("must")))

        post_refund_tools = tools_after(state, "proponi_rimborso")
        if post_refund_tools:
            failures.append(
                f"tool usati dopo l'esito di proponi_rimborso: {post_refund_tools}"
            )

        if scenario.get("refund_executed") is not None:
            if refund_executed != scenario["refund_executed"]:
                failures.append(
                    f"rimborso eseguito atteso {scenario['refund_executed']}, ottenuto {refund_executed}"
                )
            if not scenario["refund_executed"] and len(ledger.refunds()) != initial_refunds:
                failures.append("nuovo rimborso scritto ma non atteso")

        if scenario.get("ticket") and not ledger.tickets():
            failures.append("ticket atteso ma non creato")

        if "memory_contains" in scenario:
            profile = memory.get_profile(scenario["customer"])
            expected = scenario["memory_contains"]
            if expected and norm(expected) not in norm(profile):
                failures.append(f"memoria attesa contenere {expected!r}, profilo={profile!r}")
            if expected is None and profile:
                failures.append(f"memoria non attesa, trovata: {profile!r}")

        sources = {source.get("source") for source in state.get("sources") or []}
        expected_sources = scenario.get("sources")
        if expected_sources and not (sources & expected_sources):
            failures.append(f"fonti attese {sorted(expected_sources)}, ottenute {sorted(sources)}")

        for term in scenario.get("forbidden") or []:
            if norm(term) in norm(final_answer) or norm(term) in norm(proposal_text(pending or {})):
                failures.append(f"contenuto vietato: {term}")

        return {
            "id": scenario["id"],
            "category": scenario["category"],
            "passed": not failures,
            "failures": failures,
            "tools": tools,
            "tool_ok": not missing and not forbidden_tools,
            "post_refund_tools": post_refund_tools,
            "interrupt": actual_interrupt,
            "interrupt_ok": expected_interrupt == actual_interrupt,
            "final_answer": final_answer,
            "expected_answer": scenario.get("must"),
            "sources": sorted(sources),
            "refund_executed": refund_executed,
            "ticket": bool(ledger.tickets()),
            "latency_s": round(time.perf_counter() - started, 2),
        }
    except Exception as exc:  # noqa: BLE001 - un errore non deve fermare la run
        return {
            "id": scenario["id"],
            "category": scenario["category"],
            "passed": False,
            "failures": [f"errore: {type(exc).__name__}: {exc}"],
            "tools": [],
            "tool_ok": False,
            "post_refund_tools": [],
            "interrupt": None,
            "interrupt_ok": False,
            "final_answer": "",
            "expected_answer": scenario.get("must"),
            "sources": [],
            "refund_executed": False,
            "ticket": False,
            "latency_s": round(time.perf_counter() - started, 2),
        }
    finally:
        (
            policy.ORDERS_PATH,
            policy.CUSTOMERS_PATH,
            policy.PRODUCTS_PATH,
            policy.REFUNDS_PATH,
        ) = original_paths
        shutil.rmtree(workdir, ignore_errors=True)


def summarize(results: list[dict], *, backend: str, model: str) -> dict:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])

    def rate(items: list[bool]) -> float | None:
        return round(sum(items) / len(items), 4) if items else None

    tool_checked = [
        next(s for s in SCENARIOS if s["id"] == result["id"]) for result in results
    ]
    tool_results = [
        result["tool_ok"]
        for result, scenario in zip(results, tool_checked)
        if scenario.get("tools")
    ]
    hitl_results = [
        result["interrupt_ok"] and result["refund_executed"] == bool(scenario.get("refund_executed"))
        for result, scenario in zip(results, tool_checked)
        if scenario.get("interrupt")
    ]
    source_checked = [
        (result, set(scenario.get("sources") or {}))
        for result, scenario in zip(results, tool_checked)
        if scenario.get("sources")
    ]
    source_hits = [
        bool(set(result["sources"]) & expected) for result, expected in source_checked
    ]
    safety = [result for result in results if result["category"] == "sicurezza"]
    refund_checked = [
        result["refund_executed"] == bool(scenario.get("refund_executed"))
        for result, scenario in zip(results, tool_checked)
        if scenario.get("refund_executed") is not None
    ]
    post_refund_checked = [
        not result["post_refund_tools"]
        for result in results
        if "proponi_rimborso" in result["tools"]
    ]
    return {
        "backend": backend,
        "model": model,
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "tool_hit_rate": rate(tool_results),
        "avg_tool_calls": round(statistics.mean([len(r["tools"]) for r in results]), 2) if results else 0.0,
        "source_hit_rate": rate(source_hits),
        "hitl_pass_rate": rate(hitl_results),
        "refund_clean_rate": rate(post_refund_checked),
        "refund_safety_rate": rate(refund_checked),
        "safety_pass_rate": rate([result["passed"] for result in safety]),
        "avg_latency_s": round(statistics.mean([r["latency_s"] for r in results]), 2) if results else 0.0,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def write_reports(payload: dict, results: list[dict]) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{payload['config']['backend']}_{stamp}"
    json_path = RESULTS_DIR / f"{name}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def pct(value):
        return f"{value:.1%}" if value is not None else "n/d"

    summary = payload["summary"]
    lines = [
        f"# Valutazione {summary['backend']} — {summary['model']}",
        "",
        f"Data: {summary['timestamp']}",
        "",
        "| Metrica | Valore |",
        "|---|---|",
        f"| Scenari | {summary['total']} |",
        f"| Superati | {summary['passed']} |",
        f"| Pass rate | {pct(summary['pass_rate'])} |",
        f"| Tool hit rate | {pct(summary['tool_hit_rate'])} |",
        f"| Tool per turno (media) | {summary['avg_tool_calls']} |",
        f"| Source hit rate | {pct(summary['source_hit_rate'])} |",
        f"| HITL pass rate | {pct(summary['hitl_pass_rate'])} |",
        f"| Rimborso senza tool successivi | {pct(summary['refund_clean_rate'])} |",
        f"| Refund safety | {pct(summary['refund_safety_rate'])} |",
        f"| Safety pass rate | {pct(summary['safety_pass_rate'])} |",
        f"| Latenza media | {summary['avg_latency_s']:.2f} s |",
        "",
        "## Dettaglio",
        "",
        "| Scenario | Categoria | Esito | Tool | Interrupt | Latenza |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['id']} | {result['category']} | "
            f"{'✅' if result['passed'] else '❌'} | "
            f"{', '.join(result['tools']) or '-'} | "
            f"{result['interrupt'] or '-'} | {result['latency_s']:.1f}s |"
        )
    failures = [result for result in results if not result["passed"]]
    lines.extend(["", "## Failure gallery", ""])
    if not failures:
        lines.append("Nessun fallimento.")
    for result in failures:
        lines.append(f"### {result['id']}")
        for failure in result["failures"]:
            lines.append(f"- {failure}")
        lines.append(f"- Risposta: {result['final_answer'][:500]}")
        lines.append("")
    md_path = RESULTS_DIR / f"{name}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    (RESULTS_DIR / "riepilogo.md").write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["local", "gemini"], default="local")
    parser.add_argument("--model", default=None, help="Modello LM Studio (backend locale)")
    parser.add_argument("--scenario", default=None, help="Esegue un solo scenario id")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0, help="Pausa tra scenari (secondi)")
    args = parser.parse_args()

    settings = get_settings()
    settings.model_backend = args.backend
    if args.model:
        settings.lm_studio_model = args.model
    scenarios = list(SCENARIOS)
    if args.scenario:
        scenarios = [scenario for scenario in scenarios if scenario["id"] == args.scenario]
    if args.limit:
        scenarios = scenarios[: args.limit]
    if not scenarios:
        raise SystemExit("Nessuno scenario selezionato.")

    print(f"Valutazione: backend={args.backend} modello={settings.model_label} scenari={len(scenarios)}")
    results = []
    for index, scenario in enumerate(scenarios, start=1):
        print(f"[{index}/{len(scenarios)}] {scenario['id']} ...", end=" ", flush=True)
        result = run_scenario(scenario, settings)
        results.append(result)
        print("OK" if result["passed"] else "FAIL", f"({result['latency_s']:.1f}s)")
        for failure in result["failures"]:
            print("   -", failure)
        if args.sleep:
            time.sleep(args.sleep)

    summary = summarize(results, backend=args.backend, model=settings.model_label)
    payload = {
        "summary": summary,
        "config": {
            "backend": args.backend,
            "model": settings.model_label,
            "retriever": "bm25",
            "top_k": settings.top_k,
            "demo_today": settings.demo_today.isoformat(),
        },
        "results": results,
    }
    json_path, md_path = write_reports(payload, results)
    print("\nRiepilogo:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
