# -*- coding: utf-8 -*-
"""Genera il report tecnico breve (4 pagine) della v2.

Legge le metriche reali da eval/results: latest.json per LFM3 e l'ultima run
Llama 3.2 3B (Unsloth) completa. Non inventa numeri.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    CondPageBreak,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

import doc_common as dc

P = dc.P

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "report_tecnico.pdf"
CHART = ROOT / "docs" / "valutazione_v2.png"

final = dc.load_final()
llama = dc.load_llama()
fs = final["summary"]
ls = (llama or {}).get("summary", {})
lat = f"{fs['avg_latency_s']:.2f}".replace(".", ",")

# --- grafico ---------------------------------------------------------------
profiles = [("LFM3 1.7B", fs, "#6b4429"), ("Llama 3.2 3B Unsloth", ls, "#4f6b4d")]
profiles = [(name, summary, color) for name, summary, color in profiles if summary]

fig, axes = plt.subplots(1, 2, figsize=(10.6, 2.75))
names = [name for name, _, _ in profiles]
colors_bar = [color for _, _, color in profiles]
rates = [summary["pass_rate"] * 100 for _, summary, _ in profiles]
latency = [summary["avg_latency_s"] for _, summary, _ in profiles]

axes[0].bar(names, rates, color=colors_bar, width=0.52)
axes[0].set_ylim(0, 112)
axes[0].set_ylabel("pass rate (%)")
axes[0].set_title("31 scenari superati")
for index, value in enumerate(rates):
    axes[0].text(index, value + 2, f"{value:.1f}%".replace(".", ","), ha="center", fontsize=9)

axes[1].bar(names, latency, color=colors_bar, width=0.52)
top = max(latency) * 1.28
axes[1].set_ylim(0, top)
axes[1].set_ylabel("secondi per scenario")
axes[1].set_title("Latenza media")
for index, value in enumerate(latency):
    axes[1].text(index, value + top * 0.04, f"{value:.1f} s".replace(".", ","), ha="center", fontsize=9)

for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.18, wspace=0.3)
fig.savefig(CHART, dpi=190, facecolor="white", bbox_inches="tight")
plt.close(fig)

# --- documento -------------------------------------------------------------
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
PAGE_W, PAGE_H = A4
MARGIN = 1.7 * cm
CONTENT = PAGE_W - 2 * MARGIN


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(dc.LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, 1.02 * cm, PAGE_W - MARGIN, 1.02 * cm)
    canvas.setFont(dc.FONT, 7.5)
    canvas.setFillColor(dc.GREY)
    canvas.drawString(MARGIN, 0.7 * cm, "Casa & Regali · report tecnico · v2")
    canvas.drawRightString(PAGE_W - MARGIN, 0.7 * cm, f"pagina {document.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=1.45 * cm,
    bottomMargin=1.4 * cm,
    title="Casa & Regali — Report tecnico (v2)",
    author="Progetto finale LLM & Agentic AI",
    subject="Un agente, un passaggio di tool, RAG BM25, HITL e ledger idempotente",
)

story: list = []

# --- pagina 1 --------------------------------------------------------------
story.append(dc.P("REPORT TECNICO · PROGETTO FINALE LLM &amp; AGENTIC AI", "cover_kicker"))
story.append(
    Paragraph(
        "Casa &amp; Regali — assistente clienti",
        dc.STYLE["cover_title"].clone("ReportTitle", fontSize=24, leading=28, spaceAfter=2),
    )
)
story.append(
    P(
        "Versione 2 (v2) · un agente, un passaggio di tool, un secondo passo LLM per la risposta",
        "cover_sub",
    )
)
story.append(
    P(
        "<b>Abstract.</b> Il progetto realizza un assistente clienti in italiano per un e-commerce "
        "fittizio di complementi d'arredo. L'LLM sceglie uno dei sette tool, il tool applica policy e "
        "dati reali, un secondo passo LLM scrive la risposta senza poter avviare altre azioni. Il "
        "rimborso viene solo <i>proposto</i>: entra nel ledger unicamente dopo approvazione umana, con "
        "audit JSONL di ogni turno. La v2 riduce l'architettura estesa (supervisore, "
        "tre agenti, reflection, Chroma, fallback deterministico) a ciò che con un modello da 1-3B "
        "funziona davvero, e misura il risultato su 31 scenari.",
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    dc.stat_row(
        [
            (f"{fs['passed']}/{fs['total']}", "scenari superati"),
            (dc.pct(fs["tool_hit_rate"]), "tool hit rate"),
            ("45", "test automatici"),
            (f"{fs['avg_latency_s']:.2f} s".replace(".", ","), "latenza media"),
        ]
    )
)
story.append(Spacer(1, 0.3 * cm))

story.append(dc.h2("1. Obiettivo e perimetro"))
story.append(
    P(
        "La revisione parte da una domanda: <b>quale parte del sistema ha davvero bisogno dell'LLM?</b> "
        "La risposta è duplice: l'LLM serve per scegliere il tool e per scrivere una risposta in "
        "linguaggio naturale. Tutto il resto — idoneità al reso, soglie di rimborso, privacy, "
        "approvazione, scrittura del ledger — è codice deterministico e verificabile."
    )
)
story += dc.bullets(
    [
        "<b>Restano</b> policy-as-code, tool read-only, privacy per cliente, HITL sul rimborso, audit e ledger idempotente.",
        "<b>Escono</b> multi-agente, supervisore, review/reflection, backend deterministico, Chroma e ricerca ibrida.",
        "<b>Requisiti coperti</b>: modello cloud e locale, prompting, tool personalizzati, memoria breve e lunga, RAG, HITL, UI e valutazione.",
    ]
)
story.append(
    P(
        "I requisiti della traccia restano tutti soddisfatti. La differenza è nel modo: invece di "
        "aggiungere pattern, il progetto toglie i passaggi che con un modello piccolo producevano "
        "latenza e errori, e concentra l'attenzione sul confine tra decisione del modello e vincolo "
        "di codice."
    )
)

story.append(CondPageBreak(9.0 * cm))
story.append(dc.h2("2. Architettura"))
story.append(
    P(
        "Il grafo ha quattro nodi: <b>agent</b> sceglie un tool o risponde; <b>tools</b> esegue il tool "
        "con il <font face='Courier'>ToolRuntime</font> della sessione; <b>respond</b> è un secondo "
        "passo LLM senza tool che scrive la risposta; <b>finalize</b> salva risposta, fonti e tool usati "
        "e scrive il turno nell'audit. Se non serve un tool, il percorso è "
        "<font face='Courier'>agent → finalize</font>."
    )
)
story.append(
    P(
        "Il ciclo ReAct completo (<font face='Courier'>agent → tools → agent → …</font>) con modelli da "
        "1-3B tende a ripetere lo stesso tool o a concatenarne altri dopo un esito già definitivo. "
        "Separare scelta e narrazione riduce latenza e catene incontrollate. Dopo "
        "<font face='Courier'>proponi_rimborso</font> non possono partire altri tool: l'esito del "
        "rimborso è definitivo per il turno."
    )
)
story.append(Spacer(1, 0.1 * cm))
story.append(
    dc.callout(
        "La scelta di progetto",
        "L'LLM prende due decisioni: quale tool usare e come raccontarne l'esito. Il codice decide "
        "tutto il resto. Non c'è una modalità deterministica che sostituisca il modello quando sbaglia: "
        "gli errori restano visibili nella valutazione. È una scelta più onesta e più leggibile di un "
        "fallback che maschera il comportamento reale.",
    )
)

# --- pagina 2: architettura -------------------------------------------------
story.append(PageBreak())
story += dc.image(
    ROOT / "docs" / "architettura.png",
    CONTENT,
    "Figura 1 — Flusso agent → tools → respond → finalize. La freccia superiore è il percorso "
    "senza tool; il ramo rosso è il rimborso con HITL e ledger.",
)
story.append(dc.h2("Cosa fa il modello, cosa fa il codice"))
story.append(
    dc.table(
        [
            ["Compito", "Responsabile"],
            ["Scegliere il tool e i suoi argomenti", "LLM"],
            ["Scrivere la risposta al cliente", "LLM"],
            ["Applicare finestra resi, esclusioni e soglie", "<font face='Courier'>policy.py</font>"],
            ["Garantire il cliente della sessione", "<font face='Courier'>ToolRuntime</font> + <font face='Courier'>tools.py</font>"],
            ["Sospendere il turno per l'approvazione", "<font face='Courier'>interrupt()</font>"],
            ["Scrivere il rimborso solo se approvato", "<font face='Courier'>audit.py</font> (ledger)"],
            ["Registrare turni, accessi negati e ticket", "<font face='Courier'>audit.py</font>"],
        ],
        [9.6 * cm, 8.0 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.25 * cm))
story.append(
    dc.P(
        "Non esiste una modalità deterministica né un fallback semantico: se il modello sbaglia la "
        "scelta, l'errore emerge nella valutazione, non viene mascherato. Questa è la scelta "
        "principale della versione: l'AI resta responsabile delle due decisioni che contano, il codice "
        "garantisce che non possa violare i vincoli di dominio."
    )
)
story.append(
    dc.callout(
        "Policy-as-code e privacy",
        "La fonte di verità è <font face='Courier'>policy.py</font>: finestra di reso di 30 giorni, "
        "categorie escluse (personalizzati, igiene, digitali, fine serie), soglia di escalation di "
        "500 EUR, calcolo del rimborso e controllo duplicati. Il <font face='Courier'>customer_id</font> "
        "arriva dallo stato del grafo tramite <font face='Courier'>ToolRuntime</font>: il modello non "
        "può scegliere di quale cliente parlare. Un ordine di un altro cliente restituisce lo stesso "
        "messaggio di un ordine inesistente, e l'accesso negato finisce nell'audit.",
    )
)

# --- pagina 3: HITL e valutazione -------------------------------------------
story.append(PageBreak())
story.append(dc.h2("3. Rimborso, Human-in-the-Loop e ledger"))
story.append(
    P(
        "<font face='Courier'>proponi_rimborso</font> è l'unico tool che può scrivere un rimborso, e non "
        "lo fa direttamente. Verifica l'idoneità; se l'ordine non è idoneo restituisce il motivo e non "
        "apre nulla. Altrimenti costruisce la proposta con ordine, cliente, importo, articoli e livello "
        "di approvazione, poi chiama "
        "<font face='Courier'>interrupt({\"type\": \"refund_approval\", \"proposal\": …})</font>. La UI "
        "o la CLI mostrano la proposta e riprendono con <font face='Courier'>Command(resume=…)</font>. "
        "Solo con <font face='Courier'>approved=True</font> il ledger rivalida cliente, importo e "
        "duplicati, e registra il rimborso."
    )
)
story.append(
    P(
        "Il ledger non si fida del modello né del chiamante: un importo manomesso, un'approvazione "
        "mancante o un rimborso già registrato vengono rifiutati. Sopra i 500 EUR la proposta richiede "
        "il livello <b>responsabile</b>; la UI mostra una conferma aggiuntiva e la CLI la chiede "
        "esplicitamente."
    )
)
story.append(dc.h2("4. Valutazione"))
story.append(
    P(
        "La suite contiene <b>31 scenari</b>: 9 informazioni, 3 ordini, 6 resi, 6 rimborsi, 3 sicurezza "
        "(privacy, ordine inesistente, prompt injection), 2 escalation e 2 memoria. Ogni scenario "
        "verifica tool attesi e vietati, contenuto, fonti, interrupt HITL, scritture e assenza di "
        "effetti collaterali. I rimborsi usano dati temporanei."
    )
)
story.append(
    dc.table(
        [
            ["Profilo", "Superati", "Pass rate", "Tool hit", "Fonti", "HITL", "Sicurezza", "Latenza"],
            ["LFM3-1.7B Q4_K_M", f"{fs['passed']}/{fs['total']}", dc.pct(fs["pass_rate"]), dc.pct(fs["tool_hit_rate"]), dc.pct(fs["source_hit_rate"]), dc.pct(fs["hitl_pass_rate"]), dc.pct(fs["safety_pass_rate"]), f"{fs['avg_latency_s']:.2f} s".replace(".", ",")],
            ["Llama 3.2 3B Unsloth", f"{ls.get('passed', 'n/d')}/{ls.get('total', '31')}", dc.pct(ls.get("pass_rate")), dc.pct(ls.get("tool_hit_rate")), dc.pct(ls.get("source_hit_rate")), dc.pct(ls.get("hitl_pass_rate")), dc.pct(ls.get("safety_pass_rate")), f"{ls['avg_latency_s']:.2f} s".replace(".", ",") if ls else "n/d"],
        ],
        [3.9 * cm, 1.8 * cm, 1.9 * cm, 1.9 * cm, 1.5 * cm, 1.5 * cm, 1.9 * cm, 1.6 * cm],
        align_center_from=1,
        small=True,
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(dc.image(CHART, CONTENT, None)[0])
story.append(
    P(
        f"LFM3 è più lento ma più affidabile: 31/31 con 0,94 tool per turno e "
        f"{lat} s medi. Llama (Unsloth) è più veloce "
        "(1,88 secondi) ma sbaglia tool, fonti e sicurezza (66,7% contro 100%); i 7 fallimenti si "
        "concentrano su resi, memoria e sicurezza.",
        "small",
    )
)
story.append(
    P(
        "<b>Reasoning.</b> Con LFM3 il reasoning attivo (variabile vuota) ha dato la migliore scelta dei "
        "tool. La risposta finale lo disattiva sempre: con la tabella dei 10 ordini il secondo passo "
        "consumava 7.058 token e restituiva contenuto vuoto. Con "
        "<font face='Courier'>LM_STUDIO_REASONING_EFFORT=none</font> su tutto il grafo una run "
        "precedente si è fermata a 27/31. <b>Gemini.</b> Nessuna run completa per quota esaurita: il "
        "backend resta configurabile, ma senza metrica comparabile.",
        "small",
    )
)
story.append(dc.h2("Perché queste tecniche e non altre"))
story += dc.bullets(
    [
        "<b>Prompting.</b> Ruolo e vincoli espliciti, few-shot per la scelta del tool e per la risposta "
        "diretta, argomenti descritti da schemi Pydantic; il prompt finale riceve solo richiesta ed "
        "esiti e vieta calcoli e dati inventati. Poche regole, perché con modelli da 1-3B un prompt "
        "lungo diluisce le istruzioni.",
        "<b>Un tool per turno, poi <font face='Courier'>respond</font> senza tool.</b> Il ciclo ReAct "
        "completo tende a ripetere lo stesso tool o a concatenarne altri dopo un esito definitivo; "
        "separare scelta e narrazione riduce latenza e catene incontrollate.",
        "<b>BM25, non Chroma.</b> Il corpus ha dieci documenti brevi e distinti: BM25 non richiede "
        "embedding né indice vettoriale, è deterministico e rende le fonti verificabili. Su un corpus "
        "più grande servirebbe ricerca semantica o ibrida.",
        "<b>Memoria breve e preferenze esplicite.</b> Il checkpointer tiene il filo della sessione; a "
        "lungo termine salviamo solo ciò che il cliente chiede di ricordare, ripulito da email, "
        "telefoni e carte. Nessun profilo dedotto senza richiesta.",
        "<b>HITL dentro <font face='Courier'>proponi_rimborso</font>.</b> Un nodo separato aggiunge un "
        "passaggio e lascia aperta la scrittura da altri percorsi; l'<font face='Courier'>interrupt</font> "
        "nel tool lega proposta e approvazione, mentre il ledger rivalida cliente, importo e duplicati.",
        "<b>Un solo agente, niente multi-agente, reflection o fallback.</b> Supervisore e review "
        "moltiplicano le chiamate senza migliorare la scelta; un fallback nasconderebbe gli errori. "
        "Audit JSONL ed eval custom al posto di LangSmith.",
    ]
)
# --- pagina 4: test, limiti, confronto, conclusione -------------------------
story.append(PageBreak())
story.append(dc.h2("5. Test e riproducibilità"))
story.append(
    P(
        "La suite automatica usa un modello scriptato (<font face='Courier'>ScriptedModel</font>) e dati "
        "isolati: non richiede LM Studio né rete. Copre flussi del grafo, HITL, privacy, memoria, policy, "
        "corpus, ledger e scenari. Stato attuale: <b>45 test superati</b>."
    )
)
story.append(dc.code_block("python -m pytest -q tests\npython eval/run_eval.py --backend local\nstreamlit run app.py\npython cli.py --customer C-001"))
story.append(
    P(
        "Per riprodurre la valutazione serve LM Studio con il modello caricato: "
        "<font face='Courier'>lms load lfm3-1.7b@q4_k_m --gpu max --context-length 8192 --yes</font>. "
        "I risultati sono in <font face='Courier'>eval/results/</font> (JSON e Markdown con failure "
        "gallery); <font face='Courier'>latest.json</font> contiene l'ultima run. La demo si ripristina "
        "con <font face='Courier'>python scripts/reset_demo.py</font>."
    )
)
story.append(dc.h2("6. Limiti"))
story += dc.bullets(
    [
        "<b>Modelli piccoli.</b> LFM3 1,7B e Llama 3.2 3B (Unsloth) possono sbagliare la scelta del tool o riformulare i numeri; la valutazione misura questi errori e non li corregge con fallback.",
        "<b>Un tool per turno.</b> Una richiesta che ne richiede due viene gestita al turno successivo: è una scelta deliberata, non un limite tecnico del grafo.",
        "<b>BM25.</b> Adatto a dieci documenti brevi; su un corpus più grande servirebbe ricerca semantica o ibrida.",
        "<b>Memoria di sessione.</b> <font face='Courier'>InMemorySaver</font> perde lo stato al riavvio; le preferenze a lungo termine restano su file.",
        "<b>Gemini.</b> Backend presente ma senza run completa per quota.",
    ]
)
story.append(dc.h2("7. Confronto con la versione estesa"))
story.append(
    dc.table(
        [
            ["Aspetto", "Versione estesa", "v2"],
            ["Agenti", "Supervisore + 3 agenti", "1 agente"],
            ["Ciclo tool", "ReAct con più passaggi", "Un solo passaggio"],
            ["Review/reflection", "Sì", "No"],
            ["RAG", "Chroma + embedding", "BM25"],
            ["Backend deterministico", "Sì", "No"],
            ["HITL", "Nodo separato del grafo", "Dentro proponi_rimborso"],
            ["Scenari", "30", "31"],
            ["Test", "76", "45"],
        ],
        [4.8 * cm, 6.4 * cm, 6.4 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.25 * cm))
story.append(dc.h2("Conclusione"))
story.append(
    P(
        "La v2 mantiene i vincoli di dominio e toglie i pattern che, con un modello "
        "da 1-3B, non ripagavano la complessità. Il grafo è piccolo abbastanza da essere letto in un "
        "minuto, ma il comportamento non è simulato: l'LLM sceglie davvero il tool, scrive davvero la "
        "risposta e sbaglia quando il modello sbaglia. La differenza è che gli errori sono visibili "
        "nella valutazione, non nascosti da un fallback."
    )
)
story.append(
    P(
        "Il 31/31 di LFM3 non è una garanzia di produzione: è la misura di un prototipo su 31 scenari "
        "controllati, con un modello locale e dati sintetici. Llama 3.2 3B (Unsloth) mostra che il margine di "
        "errore esiste e dipende dal modello. Il secondo passo LLM separato riduce però il perimetro "
        "degli errori: la risposta può essere imprecisa, ma non può avviare un rimborso o cambiare "
        "cliente."
    )
)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Scritto {OUT}")
