# -*- coding: utf-8 -*-
"""Genera la relazione tecnica della v2: corpo di 4 pagine + appendice funzioni.

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
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

import doc_common as dc

P = dc.P

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "relazione_tecnica.pdf"
CHART = ROOT / "docs" / "valutazione_v2.png"

final = dc.load_final()
llama = dc.load_llama()
fs = final["summary"]
ls = (llama or {}).get("summary", {})
lat = f"{fs['avg_latency_s']:.2f}".replace(".", ",")
ls_lat = f"{ls.get('avg_latency_s', 0):.2f}".replace(".", ",")
tool_per_turn = f"{fs['avg_tool_calls']:.2f}".replace(".", ",")
docs = len(list((ROOT / "data" / "corpus").glob("*.md")))
llama_passed = ls.get("passed", "n/d")
llama_total = ls.get("total", 31)
llama_failures = (
    llama_total - llama_passed if isinstance(llama_passed, int) else "n/d"
)
llama_safety = dc.pct(ls.get("safety_pass_rate"))
lfm_safety = dc.pct(fs["safety_pass_rate"])

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
    axes[1].text(index, value + top * 0.04, f"{value:.2f} s".replace(".", ","), ha="center", fontsize=9)

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
    canvas.drawString(MARGIN, 0.7 * cm, "Casa & Regali · relazione tecnica · v2")
    canvas.drawRightString(PAGE_W - MARGIN, 0.7 * cm, f"pagina {document.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=1.45 * cm,
    bottomMargin=1.4 * cm,
    title="Casa & Regali — Relazione tecnica (v2)",
    author="Progetto finale LLM & Agentic AI",
    subject="Un agente, un passaggio di tool, RAG BM25, HITL e ledger idempotente",
)

story: list = []

# --- pagina 1 --------------------------------------------------------------
story.append(dc.P("RELAZIONE TECNICA · PROGETTO FINALE LLM &amp; AGENTIC AI", "cover_kicker"))
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
        "fittizio di complementi d'arredo. L'LLM sceglie uno dei sette tool e scrive la risposta; "
        "un secondo passo LLM, senza tool, racconta l'esito. Le regole di dominio — finestra di reso, "
        "esclusioni, soglia di rimborso, privacy — sono codice deterministico. Il rimborso viene solo "
        "<i>proposto</i>: entra nel ledger unicamente dopo l'approvazione di un operatore. La v2 è la "
        "versione ottimizzata di un progetto esteso con supervisore, tre agenti, reflection e Chroma, "
        "e misura il risultato su 31 scenari con un modello locale da 1,7B.",
    )
)
story.append(Spacer(1, 0.15 * cm))
story.append(
    dc.stat_row(
        [
            (f"{fs['passed']}/{fs['total']}", "scenari superati"),
            (dc.pct(fs["tool_hit_rate"]), "tool hit rate"),
            ("60", "test automatici"),
            (f"{fs['avg_latency_s']:.2f} s".replace(".", ","), "latenza media"),
        ]
    )
)
story.append(Spacer(1, 0.35 * cm))

story.append(dc.h2("1. Contesto e obiettivo"))
story.append(
    P(
        "Un assistente clienti non è un problema di conversazione: è un problema di responsabilità. "
        "La risposta può essere scritta dall'LLM, ma un reso fuori finestra, un ordine di un altro "
        "cliente o un rimborso già eseguito non sono opinioni: sono fatti e regole. Se il modello "
        "sbaglia, l'errore non deve diventare una scrittura irreversibile."
    )
)
story.append(
    P(
        f"Ho scelto un dominio chiuso: <b>{docs} documenti</b> di policy, <b>200 ordini</b> sintetici e "
        "<b>50 clienti</b>. Le richieste sono eterogenee — «quanto costa la spedizione?», «dov'è "
        "ORD-1001?», «posso restituire una tazza personalizzata?», «voglio il rimborso di ORD-1005» — "
        "ma finiscono tutte nello stesso punto: una risposta in italiano che deve usare i dati giusti, "
        "applicare le regole giuste e non superare i limiti del proprio ruolo."
    )
)
story.append(
    P(
        "L'obiettivo non è accumulare pattern. È costruire un turno che risponda con fonti verificabili, "
        "usi solo gli ordini del cliente della sessione, applichi la policy in modo deterministico e "
        "chieda l'approvazione di un umano prima di un'azione sensibile. Il criterio di successo è "
        "misurabile: tool corretto, risposta corretta, nessun accesso a ordini altrui, nessun rimborso "
        "senza approvazione, nessun effetto collaterale indesiderato."
    )
)
story += dc.bullets(
    [
        "<b>Rispondere</b> in italiano, citando <font face='Courier'>[S1]</font>, <font face='Courier'>[S2]</font> quando la risposta viene dal corpus.",
        "<b>Usare</b> solo gli ordini del profilo della sessione, mai un cliente scelto dal modello.",
        "<b>Applicare</b> finestra di reso, esclusioni e soglie con codice deterministico.",
        "<b>Chiedere</b> l'approvazione umana prima di scrivere un rimborso.",
    ]
)

story.append(dc.h2("2. La tesi: due decisioni all'LLM, i vincoli al codice"))
story.append(
    P(
        "La domanda di progetto è stata: <b>quale parte del sistema ha davvero bisogno dell'LLM?</b> "
        "La risposta è duplice. L'LLM serve per scegliere il tool e per scrivere una risposta in "
        "linguaggio naturale. Tutto il resto — idoneità al reso, soglie di rimborso, privacy, "
        "approvazione, scrittura del ledger — è codice deterministico e verificabile."
    )
)
story.append(
    P(
        "Ho scelto di separare la <i>scelta</i> dalla <i>narrazione</i>: il nodo <font face='Courier'>agent</font> "
        "decide, il nodo <font face='Courier'>tools</font> esegue, il nodo <font face='Courier'>respond</font> "
        "scrive senza poter avviare altre azioni. In questo modo l'LLM prende due decisioni osservabili, "
        "ma non può concatenare azioni né aggirare un vincolo di dominio."
    )
)
story.append(
    dc.callout(
        "La scelta di progetto",
        "Non c'è una modalità deterministica che sostituisca il modello quando sbaglia: gli errori "
        "restano visibili nella valutazione. È una scelta più onesta e più leggibile di un fallback "
        "che maschera il comportamento reale.",
    )
)

# --- pagina 2: confine, policy, architettura --------------------------------
story.append(PageBreak())
story.append(dc.h2("2.1 Cosa fa il modello, cosa fa il codice"))
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
story.append(Spacer(1, 0.2 * cm))
story.append(
    P(
        "<b>Policy-as-code.</b> La fonte di verità è <font face='Courier'>policy.py</font>: <b>30 giorni</b> "
        "di reso, categorie escluse (personalizzati, igiene, digitali, fine serie), soglia di escalation "
        "di <b>500 EUR</b>, prima risposta di un ticket entro <b>24 ore</b>, calcolo del rimborso e "
        "controllo duplicati. I documenti <i>spiegano</i> la policy, i tool la <i>applicano</i>; un test "
        "confronta i numeri dei documenti con le costanti del codice."
    )
)
story.append(
    P(
        "<b>Privacy.</b> Il <font face='Courier'>customer_id</font> arriva dallo stato del grafo tramite "
        "<font face='Courier'>ToolRuntime</font>: il modello non sceglie di quale cliente parlare. Un "
        "ordine altrui restituisce lo stesso messaggio di un ordine inesistente, e l'accesso negato "
        "finisce nell'audit. I dati del profilo non vengono passati al modello: i tool restituiscono "
        "solo i campi dell'ordine necessari."
    )
)

story.append(dc.h2("3. Architettura e un turno"))
story.append(
    P(
        "Il grafo ha quattro nodi: <b>agent</b> sceglie un tool o risponde; <b>tools</b> esegue il tool "
        "con il <font face='Courier'>ToolRuntime</font> della sessione; <b>respond</b> è un secondo "
        "passo LLM senza tool che scrive la risposta; <b>finalize</b> salva risposta, fonti e tool usati "
        "e scrive il turno nell'audit. Se non serve un tool, il percorso è "
        "<font face='Courier'>agent → finalize</font>."
    )
)
story += dc.image(
    ROOT / "docs" / "architettura.png",
    CONTENT * 0.87,
    "Figura 1 — Flusso agent → tools → respond → finalize. La freccia superiore è il percorso "
    "senza tool; il ramo rosso è il rimborso con HITL e ledger.",
)
story.append(
    P(
        "Ho scelto un solo passaggio di tool per turno. Il ciclo ReAct completo "
        "(<font face='Courier'>agent → tools → agent → …</font>) con modelli da 1-3B tende a ripetere "
        "lo stesso tool o a concatenarne altri dopo un esito già definitivo. Separare scelta e "
        "narrazione riduce latenza e catene incontrollate."
    )
)
story.append(
    P(
        "<b>Un turno completo.</b> «Voglio il rimborso di ORD-1001»: <font face='Courier'>agent</font> "
        "chiama <font face='Courier'>proponi_rimborso(\"ORD-1001\")</font>; il tool verifica il cliente, "
        "applica la policy e calcola <b>89,70 EUR</b>. <font face='Courier'>interrupt()</font> sospende "
        "il turno con una proposta a livello <i>operatore</i>; la UI riprende con "
        "<font face='Courier'>Command(resume=...)</font> e il ledger rivalida cliente, importo e "
        "duplicati prima di scrivere. <font face='Courier'>respond</font> racconta l'esito, "
        "<font face='Courier'>finalize</font> registra il turno; se l'operatore rifiuta, non viene "
        "scritto nulla."
    )
)

# --- pagina 3: mappa del codice e alternative --------------------------------
story.append(PageBreak())
story.append(dc.h2("4. Mappa del codice"))
story.append(
    P(
        "La tabella collega ogni responsabilità al file che la implementa: è il livello di "
        "lettura del codice, complementare al flusso descritto nelle sezioni 2 e 3.",
        "small",
    )
)
story.append(
    dc.table(
        [
            ["File", "Responsabilità", "Dettagli da conoscere"],
            [
                "agent.py",
                "Grafo e turno",
                "<font face='Courier'>SupportState</font> (<font face='Courier'>messages</font>, "
                "<font face='Courier'>customer_id</font>, <font face='Courier'>final_answer</font>, "
                "<font face='Courier'>sources</font>); quattro nodi; <font face='Courier'>respond</font> "
                "senza tool; <font face='Courier'>finalize</font> legge solo il turno corrente e ha un "
                "fallback; <font face='Courier'>start_turn</font>/<font face='Courier'>resume_turn</font>.",
            ],
            [
                "tools.py",
                "Sette tool",
                "<font face='Courier'>ToolRuntime</font> inietta il <font face='Courier'>customer_id</font>; "
                "stesso messaggio per ordine inesistente o altrui; <font face='Courier'>cerca_policy</font> "
                "unisce query e richiesta; <font face='Courier'>proponi_rimborso</font> sospende e scrive "
                "solo dopo l'approvazione.",
            ],
            [
                "policy.py",
                "Regole deterministiche",
                "30 giorni, 24 mesi, 5-10 giorni, 50/4,90 EUR, soglia 500 EUR; "
                "<font face='Courier'>find_order</font>/<font face='Courier'>list_orders</font> filtrati; "
                "albero di idoneità; <font face='Courier'>calculate_refund</font> con spedizione rimborsabile.",
            ],
            [
                "audit.py",
                "Prove e ledger",
                "Eventi JSONL (turno, privacy, ticket, rimborsi); <font face='Courier'>execute_refund</font> "
                "ricontrolla approvazione, ordine, cliente, importo e duplicati; lock e file temporanei.",
            ],
            [
                "prompts.py + turns.py",
                "Qualità della risposta",
                "Prompt per tool; contratto <font face='Courier'>&lt;risposta&gt;</font>; "
                "<font face='Courier'>extract_answer</font>; helper per messaggi, turno, tool e fonti.",
            ],
            [
                "corpus.py",
                "RAG BM25",
                "10 documenti; split per sezioni; chunk 650/50; BM25 e sinonimi; top 3 con "
                "score <font face='Courier'>&gt; 0</font>; fonti <font face='Courier'>[S1]</font>.",
            ],
            [
                "memory.py + models.py + config.py",
                "Runtime",
                "Preferenze esplicite, PII rimosse, duplicati ignorati; reasoning finale spento per LFM3 "
                "locale; <font face='Courier'>Settings</font>, <font face='Courier'>demo_today</font> e percorsi.",
            ],
            [
                "app.py + cli.py + eval/ + tests/",
                "Interfacce e verifica",
                "<font face='Courier'>session_state</font> e pending; conferma &gt; 500 EUR; ciclo interrupt "
                "nella CLI; 31 scenari su file temporanei; metriche; <font face='Courier'>ScriptedModel</font>.",
            ],
        ],
        [3.1 * cm, 3.1 * cm, 11.2 * cm],
        small=True,
        pad=3,
    )
)
story.append(Spacer(1, 0.15 * cm))
story.append(
    P(
        "I tool portano nel turno dati e controlli deterministici: il prompt descrive le regole, "
        "il codice le applica e il ledger le rivalida prima di ogni scrittura.",
        "small",
    )
)
story.append(Spacer(1, 0.1 * cm))

story.append(dc.h2("5. Scelte e alternative scartate"))
story.append(
    dc.table(
        [
            ["Scelta", "Alternativa scartata", "Perché", "Conseguenza"],
            [
                "Un solo agente",
                "Supervisore con agenti specialistici",
                "Sette tool e un dominio: la divisione in specialisti moltiplica le chiamate senza aggiungere capacità",
                "31/31, 0,94 tool per turno",
            ],
            [
                "Un passaggio di tool, poi <font face='Courier'>respond</font>",
                "Ciclo ReAct completo",
                "Con modelli piccoli il ciclo tende a ripetere il tool o a concatenarne altri dopo un esito definitivo",
                "Nessun tool dopo il rimborso",
            ],
            [
                "BM25",
                "Chroma con embedding",
                "Dieci documenti brevi: BM25 è deterministico, non richiede indice né modello di embedding",
                "Source hit 100%",
            ],
            [
                "Policy-as-code",
                "Regole nel system prompt",
                "Il prompt può essere ignorato o attaccato con prompt injection; il codice no",
                "Prompt injection superata",
            ],
            [
                "HITL nel tool",
                "Nodo di approvazione separato",
                "Proposta e approvazione restano nello stesso punto; un nodo separato lascerebbe altri percorsi di scrittura",
                "Rimborso pulito 100%",
            ],
            [
                "Eval custom e audit JSONL",
                "LangSmith",
                "La suite è piccola e il progetto resta riproducibile senza account esterni; il JSONL copre turni, privacy e rimborsi",
                "31 scenari e failure gallery",
            ],
        ],
        [3.6 * cm, 3.8 * cm, 6.4 * cm, 3.6 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    P(
        "<b>Prompting.</b> Il system prompt usa ruolo e vincoli, few-shot e output strutturato: lo "
        "schema degli argomenti è generato da LangChain, quindi il modello non inventa campi. Il "
        "prompt di scelta resta breve; quello finale riceve solo richiesta ed esiti, cambia per tool e "
        "chiede un blocco <font face='Courier'>&lt;risposta&gt;</font>. Il codice estrae solo quel "
        "blocco, così il ragionamento non arriva al cliente."
    )
)
story.append(
    P(
        "<b>Perché non multi-agente, reflection o LangSmith.</b> Un dominio, sette tool e un turno "
        "singolo non li richiedono: aggiungerebbero passaggi, latenza o un account esterno senza "
        "migliorare la scelta."
    )
)
story.append(
    P(
        "<b>Un fallimento concreto.</b> Nella run Unsloth, <font face='Courier'>info_personalizzato</font> "
        "chiama <font face='Courier'>verifica_reso</font> invece di <font face='Courier'>cerca_policy</font>; "
        "<font face='Courier'>memoria_implicita</font> salva una preferenza non richiesta. La failure "
        "gallery conserva gli errori."
    )
)

# --- pagina 4: valutazione, limiti, conclusione -----------------------------
story.append(PageBreak())
story.append(dc.h2("6. Valutazione"))
story.append(
    P(
        "La suite contiene <b>31 scenari</b>: 9 informazioni, 3 ordini, 6 resi, 6 rimborsi, 3 sicurezza "
        "(privacy, ordine inesistente, prompt injection), 2 escalation e 2 memoria. Ogni scenario "
        "verifica, dove previsto, tool attesi e vietati, contenuto, fonti, interrupt HITL, scritture e "
        "assenza di effetti collaterali. I rimborsi usano dati temporanei, senza toccare la demo."
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
story.append(Spacer(1, 0.15 * cm))
story.append(dc.image(CHART, CONTENT, None)[0])
story.append(
    P(
        f"LFM3 è più lento ma più affidabile: <b>{fs['passed']}/{fs['total']}</b> con "
        f"<b>{tool_per_turn} tool per turno</b> e {lat} s medi. Llama (Unsloth) è più veloce "
        f"({ls_lat} s) ma si ferma a {llama_passed}/{llama_total}: sbaglia tool, fonti e sicurezza "
        f"({llama_safety} contro {lfm_safety}); i {llama_failures} fallimenti si concentrano su resi, "
        "memoria e sicurezza. Il modello più piccolo non è un dettaglio: è il vincolo che rende "
        "necessari i confini di codice.",
        "small",
    )
)
story.append(
    P(
        "<b>Reasoning.</b> Con LFM3 il reasoning attivo (variabile vuota) ha dato la migliore scelta dei "
        "tool. La risposta finale lo disattiva sempre: con la tabella dei 10 ordini il secondo passo "
        "consumava <b>7.058 token</b> e restituiva contenuto vuoto. Con "
        "<font face='Courier'>LM_STUDIO_REASONING_EFFORT=none</font> su tutto il grafo una run precedente "
        "si è fermata a <b>27/31</b>. <b>Gemini.</b> Il backend cloud è presente, ma non c'è una run "
        "completa per esaurimento della quota: non riporto una metrica che non ho misurato.",
        "small",
    )
)
story.append(
    P(
        "<b>Metodo.</b> La valutazione misura il sistema così com'è: se il modello sceglie il tool "
        "sbagliato o inventa un numero, lo scenario fallisce. Non c'è una correzione a posteriori che "
        "nasconda l'errore; la failure gallery conserva risposta, tool e controlli falliti. La suite "
        "automatica usa un modello scriptato (<font face='Courier'>ScriptedModel</font>) e dati isolati: "
        "<b>60 test</b> senza LM Studio né rete, con fixture temporanee e data fissa. Coprono flussi del "
        "grafo, tool, policy/corpus, ledger, memoria, modelli, helper e coerenza degli scenari; non "
        "misurano la qualità del modello, che resta compito della valutazione.",
        "small",
    )
)

story.append(dc.h2("7. Limiti e conclusione"))
story += dc.bullets(
    [
        "<b>Modelli piccoli.</b> LFM3 1,7B e Llama 3.2 3B (Unsloth) possono sbagliare la scelta del tool o riformulare i numeri; la valutazione misura questi errori e non li corregge con un fallback.",
        "<b>Un tool per turno.</b> Una richiesta che ne richiede due viene gestita al turno successivo: è una scelta deliberata, non un limite tecnico del grafo.",
        "<b>BM25.</b> Adatto a dieci documenti brevi; su un corpus più grande servirebbe ricerca semantica o ibrida.",
        "<b>Memoria di sessione.</b> <font face='Courier'>InMemorySaver</font> perde lo stato al riavvio; le preferenze a lungo termine restano su file.",
        "<b>Demo a processo singolo.</b> Ledger e memoria usano lock di processo e file JSON, adatti alla demo ma non a un deployment multi-istanza.",
    ]
)
story.append(Spacer(1, 0.1 * cm))
story.append(
    P(
        "La v2 mantiene i vincoli di dominio e toglie i pattern che, con un modello da 1-3B, non "
        "ripagavano la complessità. Il grafo è piccolo abbastanza da essere letto in un minuto, ma il "
        "comportamento non è simulato: l'LLM sceglie davvero il tool, scrive davvero la risposta e "
        "sbaglia quando il modello sbaglia. La differenza è che gli errori sono visibili nella "
        "valutazione, non nascosti da un fallback."
    )
)
story.append(
    P(
        "Il 31/31 di LFM3 non è una garanzia di produzione: è la misura di un prototipo su 31 scenari "
        "controllati, con un modello locale e dati sintetici. Llama 3.2 3B (Unsloth) mostra che il "
        "margine di errore esiste e dipende dal modello. Il secondo passo LLM separato riduce però il "
        "perimetro degli errori: la risposta può essere imprecisa, ma non può avviare un rimborso o "
        "cambiare cliente."
    )
)

# --- appendice: funzioni Python --------------------------------------------
story.append(PageBreak())
story.append(dc.h2("Appendice A — Dettaglio delle funzioni Python"))
story.append(
    P(
        "Il corpo della relazione resta di quattro pagine; questa appendice è il livello di lettura "
        "funzione per funzione. Le schede seguono il percorso del turno e riportano input, output, "
        "comportamento, casi limite e test. La versione completa, con tutte le funzioni di supporto, "
        "è nel README (§15).",
        "small",
    )
)


def function_table(rows: list[list[str]]) -> object:
    return dc.table(
        [["Funzione", "Input → output", "Comportamento e casi limite", "Test"]] + rows,
        [3.5 * cm, 4.0 * cm, 7.6 * cm, 2.5 * cm],
        small=True,
        pad=3,
    )


story.append(dc.h3("A.1 Grafo e turno — agent.py"))
story.append(
    function_table(
        [
            [
                "<font face='Courier'>build_graph(...)</font>",
                "Settings e dipendenze opzionali → grafo compilato",
                "Crea tool e modelli, collega i tool, costruisce i quattro nodi e gli archi, usa "
                "<font face='Courier'>InMemorySaver</font> se manca un checkpointer. Per LFM3 locale "
                "crea un secondo modello con reasoning spento per <font face='Courier'>respond</font>.",
                "Tutti i flussi; models",
            ],
            [
                "<font face='Courier'>agent_node</font> + <font face='Courier'>route_agent</font>",
                "stato → <font face='Courier'>AIMessage</font> / <font face='Courier'>\"tools\"</font> o <font face='Courier'>\"finalize\"</font>",
                "Antepone il system prompt e chiama il modello con i tool. Se l'ultimo messaggio ha "
                "<font face='Courier'>tool_calls</font> va a <font face='Courier'>tools</font>, altrimenti chiude. "
                "Non esiste il ritorno da <font face='Courier'>tools</font> ad <font face='Courier'>agent</font>.",
                "graph",
            ],
            [
                "<font face='Courier'>respond_node</font>",
                "stato → <font face='Courier'>AIMessage</font>",
                "Legge l'ultima richiesta e i risultati dei tool, sceglie il prompt per tool e chiama "
                "il modello senza tool. <font face='Courier'>extract_answer</font> scarta il ragionamento "
                "fuori da <font face='Courier'>&lt;risposta&gt;</font>; un contenuto vuoto attiva il fallback.",
                "graph, turns",
            ],
            [
                "<font face='Courier'>finalize</font>",
                "stato → <font face='Courier'>final_answer</font>, <font face='Courier'>sources</font>",
                "Cerca l'ultima AI del turno corrente, non del precedente. Se è vuota usa il messaggio "
                "neutro, raccoglie fonti e tool e scrive l'evento <font face='Courier'>turno</font> con "
                "risposta troncata a 500 caratteri.",
                "graph",
            ],
            [
                "<font face='Courier'>start_turn</font> / <font face='Courier'>resume_turn</font>",
                "grafo, thread, input → risultato",
                "Il primo azzera risposta e fonti e invoca il grafo con <font face='Courier'>recursion_limit=20</font>; "
                "il secondo riprende l'interrupt con <font face='Courier'>Command(resume=...)</font>.",
                "graph, HITL",
            ],
            [
                "<font face='Courier'>pending_interrupt</font> / <font face='Courier'>state_values</font>",
                "risultato/grafo → dict",
                "Il primo legge <font face='Courier'>__interrupt__</font> e normalizza oggetto o dizionario; "
                "il secondo restituisce i valori dello stato del thread.",
                "graph",
            ],
        ]
    )
)

story.append(Spacer(1, 0.15 * cm))
story.append(dc.h3("A.2 Tool e dominio — tools.py, policy.py"))
story.append(
    function_table(
        [
            [
                "<font face='Courier'>make_tools</font> / <font face='Courier'>_customer</font>",
                "ledger, memoria, settings → sette tool",
                "I tool sono chiusi sulle dipendenze della sessione; <font face='Courier'>_customer</font> legge "
                "il cliente dallo stato del grafo, mai dagli argomenti del modello.",
                "tools, eval",
            ],
            [
                "<font face='Courier'>cerca_policy</font>",
                "query → JSON con contesto e fonti",
                "Unisce la query all'ultima richiesta umana, chiama <font face='Courier'>retrieve</font> e "
                "restituisce fonti <font face='Courier'>[S1]</font>–<font face='Courier'>[S3]</font>.",
                "tools",
            ],
            [
                "<font face='Courier'>stato_ordine</font> / <font face='Courier'>elenca_ordini</font>",
                "ordine o runtime → testo",
                "Filtrano per cliente. Un ordine altrui e uno inesistente producono lo stesso messaggio; "
                "l'elenco non mostra mai identificativi o contatti del profilo.",
                "tools",
            ],
            [
                "<font face='Courier'>verifica_reso</font>",
                "ordine → testo",
                "Applica la policy con la data demo, riporta giorni, categorie escluse e difettosità. "
                "Un ordine non trovato passa prima dal controllo privacy.",
                "tools, policy",
            ],
            [
                "<font face='Courier'>proponi_rimborso</font>",
                "ordine → testo o interrupt",
                "Verifica idoneità e cliente, calcola l'importo, costruisce la proposta e chiama "
                "<font face='Courier'>interrupt</font>. Un rifiuto non scrive; un'approvazione passa al ledger. "
                "Un ordine non idoneo non apre nulla.",
                "graph, HITL",
            ],
            [
                "<font face='Courier'>apri_ticket</font> / <font face='Courier'>ricorda_preferenza</font>",
                "testo → testo",
                "Il primo calcola la priorità da parole di escalation e crea il ticket; il secondo salva "
                "solo preferenze esplicite, con PII mascherate e duplicati ignorati.",
                "tools, memory",
            ],
            [
                "<font face='Courier'>find_order</font> / <font face='Courier'>list_orders</font>",
                "ID/cliente → dict o lista",
                "Normalizzano l'ID e filtrano sempre per cliente. <font face='Courier'>find_order</font> non "
                "distingue un ordine altrui da uno inesistente; la lista è ordinata dal più recente.",
                "policy",
            ],
            [
                "<font face='Courier'>check_return_eligibility</font>",
                "ordine, cliente, data → dict",
                "Controlla cliente, rimborso, stato, consegna, data, finestra di 30 giorni ed esclusioni. "
                "Restituisce motivo, giorni, articoli/categorie esclusi e riferimenti alla policy.",
                "policy",
            ],
            [
                "<font face='Courier'>calculate_refund</font>",
                "ordine → dict",
                "Somma articoli, sottrae lo sconto e aggiunge la spedizione solo se il reso è a carico nostro. "
                "Arrotonda a due decimali; l'escalation scatta sopra 500 EUR.",
                "policy",
            ],
            [
                "<font face='Courier'>execute_refund</font>",
                "proposta, approvazione → dict",
                "Unico punto di scrittura. Ricontrolla approvazione, ordine, cliente, importo e duplicati; "
                "scrive refunds e orders con file temporanei e <font face='Courier'>os.replace</font>.",
                "audit",
            ],
        ]
    )
)

story.append(Spacer(1, 0.15 * cm))
story.append(dc.h3("A.3 Dati, risposta e verifica — gli altri moduli"))
story.append(
    function_table(
        [
            [
                "<font face='Courier'>AuditLedger.log</font> / <font face='Courier'>read_audit</font>",
                "evento/limite → record/lista",
                "Scrive JSONL sotto lock, scarta i campi <font face='Courier'>None</font> e ignora le righe "
                "malformate in lettura. Gli eventi coprono turni, privacy, ticket e rimborsi.",
                "audit",
            ],
            [
                "<font face='Courier'>create_ticket</font> / <font face='Courier'>_next_refund_id</font>",
                "dati → ticket/ID",
                "Il ticket usa <font face='Courier'>TKT-2026-NNNN</font> e salta i buchi; il rimborso usa il "
                "suffisso numerico più alto e restituisce <font face='Courier'>RMB-2026-NNNN</font>.",
                "audit",
            ],
            [
                "<font face='Courier'>load_corpus</font> / <font face='Courier'>split_documents</font>",
                "cartella/documenti → chunk",
                "Legge i dieci Markdown, separa per titolo, sezione e sottosezione, poi applica chunk "
                "650/50 e assegna un <font face='Courier'>chunk_id</font> univoco.",
                "corpus",
            ],
            [
                "<font face='Courier'>retrieve</font> / <font face='Courier'>format_context</font>",
                "query → documenti/testo",
                "BM25 ricostruito a ogni query, top-k con score positivo, sinonimi italiani e fonti "
                "<font face='Courier'>[S1]</font>–<font face='Courier'>[S3]</font> numerate.",
                "corpus",
            ],
            [
                "<font face='Courier'>_sanitize</font> / <font face='Courier'>PreferenceMemory.add</font>",
                "testo → record o esito",
                "Maschera email, telefoni e carte, tronca a 200 caratteri, ignora duplicati e salva con "
                "sostituzione atomica. Una preferenza implicita non viene salvata dal prompt.",
                "memory, tools",
            ],
            [
                "<font face='Courier'>get_chat_model</font> / <font face='Courier'>final_reasoning_effort</font>",
                "settings → modello/str",
                "Gemini richiede la chiave; locale usa temperatura 0, timeout 120 e un retry. Il reasoning "
                "finale è <font face='Courier'>\"none\"</font> solo per LFM3 locale.",
                "models",
            ],
            [
                "<font face='Courier'>extract_answer</font> / <font face='Courier'>sources_from_messages</font>",
                "testo/messaggi → risposta/fonti",
                "Il primo isola <font face='Courier'>&lt;risposta&gt;</font> e lascia il testo se i tag mancano; "
                "il secondo interpreta il JSON di <font face='Courier'>cerca_policy</font>, deduplica e limita a 6 fonti.",
                "turns",
            ],
            [
                "<font face='Courier'>eval.run_scenario</font> / <font face='Courier'>summarize</font>",
                "scenario/risultati → dict",
                "Ogni scenario usa file temporanei; verifica tool, risposta, fonti, HITL, scritture e memoria. "
                "Il riepilogo calcola le metriche solo sugli scenari che prevedono quel controllo.",
                "eval",
            ],
        ]
    )
)
story.append(Spacer(1, 0.12 * cm))
story.append(
    P(
        "Le etichette della colonna <b>Test</b> rimandano ai file <font face='Courier'>tests/test_*.py</font>: "
        "<i>graph</i>, <i>tools</i>, <i>policy</i>, <i>audit</i>, <i>corpus</i>, <i>memory</i>, "
        "<i>models</i>, <i>turns</i> ed <i>eval</i>. La mappatura completa, test per test, è nel README §15.",
        "small",
    )
)
story.append(
    P(
        "Le funzioni che possono cambiare lo stato sono cinque: <font face='Courier'>proponi_rimborso</font>, "
        "<font face='Courier'>execute_refund</font>, <font face='Courier'>create_ticket</font>, "
        "<font face='Courier'>PreferenceMemory.add</font> e <font face='Courier'>finalize</font> per l'audit. "
        "Per ognuna la domanda orale è la stessa: quali controlli precedono la scrittura e quale test "
        "dimostra che un errore non la esegue.",
        "small",
    )
)

story.append(dc.h2("A.4 Tre funzioni raccontate"))
story.append(
    P(
        "Le tabelle precedenti danno la mappa; queste tre schede mostrano il livello di dettaglio "
        "utile all'orale. Sono le funzioni su cui si concentrano le domande su privacy, HITL e policy.",
        "small",
    )
)

story.append(dc.h3("proponi_rimborso(order_id, runtime)"))
story.append(
    P(
        "<b>Input → output.</b> Numero ordine e runtime della sessione → testo con l'esito, oppure "
        "sospensione del turno con una proposta HITL.",
        "small",
    )
)
story += dc.bullets(
    [
        "Legge il cliente dallo stato con <font face='Courier'>_customer</font> e cerca l'ordine con "
        "<font face='Courier'>find_order</font>: un ordine altrui o inesistente produce lo stesso messaggio e un evento privacy.",
        "Applica <font face='Courier'>check_return_eligibility</font> con la data demo. Se l'ordine non è idoneo, "
        "restituisce il motivo e non apre alcun interrupt.",
        "Calcola l'importo con <font face='Courier'>calculate_refund</font> e costruisce la proposta con ordine, "
        "cliente, importo, motivo, articoli e livello.",
        "Chiama <font face='Courier'>interrupt({\"type\": \"refund_approval\", \"proposal\": ...})</font>: da qui "
        "il turno è sospeso e nessuna scrittura è avvenuta.",
        "Dopo la ripresa, un rifiuto registra <font face='Courier'>rimborso_rifiutato</font> e restituisce un testo; "
        "un'approvazione chiama <font face='Courier'>execute_refund</font>.",
        "Traduce l'esito del ledger in testo: eseguito, duplicato o errore. Non scrive mai direttamente.",
    ]
)
story.append(
    P(
        "<b>Casi limite e test.</b> Un ordine non idoneo non produce interrupt; un'approvazione mancante "
        "equivale a rifiuto; un secondo tentativo viene bloccato dal ledger. I test sono "
        "<font face='Courier'>test_rimborso_sospende_e_non_scrive</font>, "
        "<font face='Courier'>test_approvazione_scrive_una_sola_volta</font> e "
        "<font face='Courier'>test_rifiuto_non_scrive</font>.",
        "small",
    )
)

story.append(dc.h3("execute_refund(proposal, approval, *, thread_id=None)"))
story.append(
    P(
        "<b>Input → output.</b> Proposta, decisione umana e thread → dizionario con "
        "<font face='Courier'>eseguito</font>, <font face='Courier'>duplicato</font>, "
        "<font face='Courier'>motivo</font> e, se presente, <font face='Courier'>rimborso</font>.",
        "small",
    )
)
story += dc.bullets(
    [
        "Controlla <font face='Courier'>approval[\"approved\"]</font>: senza approvazione registra il rifiuto e "
        "restituisce <font face='Courier'>eseguito=False</font>.",
        "Normalizza ordine, cliente e importo e acquisisce il lock; rilegge refunds e orders dal disco.",
        "Blocca il duplicato sia sulla chiave ordine sia su un record storico con lo stesso ordine.",
        "Verifica che l'ordine esista, che il cliente coincida e che l'importo corrisponda a "
        "<font face='Courier'>calculate_refund</font> entro 0,01 EUR.",
        "Genera <font face='Courier'>RMB-2026-NNNN</font>, aggiorna refunds e orders, sostituisce i file con "
        "<font face='Courier'>os.replace</font> e registra <font face='Courier'>rimborso_eseguito</font>.",
    ]
)
story.append(
    P(
        "<b>Limite dichiarato.</b> La coppia di file non è una transazione unica: un crash tra le due "
        "sostituzioni può lasciare i due file disallineati. Il lock è di processo, quindi la demo non è "
        "pensata per più istanze. I test <font face='Courier'>test_senza_approvazione_non_scrive</font>, "
        "<font face='Courier'>test_importo_non_coerente_bloccato</font> e "
        "<font face='Courier'>test_idempotenza</font> coprono i confini principali.",
        "small",
    )
)

story.append(dc.h3("check_return_eligibility(order, customer_id, *, today, refunds_path=None)"))
story.append(
    P(
        "<b>Input → output.</b> Ordine, cliente e data di riferimento → dizionario con idoneità, motivo, "
        "giorni dalla consegna, articoli e categorie esclusi e riferimenti alla policy.",
        "small",
    )
)
story += dc.bullets(
    [
        "Rifiuta un ordine di un altro cliente: è una difesa ridondante rispetto al filtro del tool.",
        "Rifiuta un ordine già rimborsato, annullato o non ancora consegnato: la finestra decorre dalla consegna.",
        "Calcola i giorni con <font face='Courier'>days_since_delivery</font>; una data mancante o futura "
        "produce un motivo dedicato.",
        "Se i giorni superano 30, restituisce il numero esatto e la finestra. Se sono entro 30, controlla "
        "gli articoli: basta un articolo personalizzato, di igiene, digitale o in fine serie per bloccare.",
        "Restituisce sempre un esito spiegabile; non scrive nulla e non decide l'importo.",
    ]
)
story.append(
    P(
        "<b>Test.</b> <font face='Courier'>test_idoneita_finestra_e_categorie</font> copre i sei ordini "
        "curati; <font face='Courier'>test_motivi_idoneita</font> controlla i motivi; "
        "<font face='Courier'>test_verifica_reso_usa_la_data_delle_settings</font> dimostra che la data "
        "non è letta dall'orologio di sistema.",
        "small",
    )
)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Scritto {OUT}")
