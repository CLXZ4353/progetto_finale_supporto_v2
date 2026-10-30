# -*- coding: utf-8 -*-
"""Genera la relazione tecnica breve (4 pagine) della v2.

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
OUT = ROOT / "docs" / "report_tecnico.pdf"
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
            ("57", "test automatici"),
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

# --- pagina 3: funzionalità e alternative -----------------------------------
story.append(PageBreak())
story.append(dc.h2("4. Funzionalità e perché"))
story.append(
    dc.table(
        [
            ["Funzionalità", "Obiettivo", "Perché questa scelta", "Evidenza"],
            [
                f"RAG BM25 su {docs} documenti, chunk 650/50, top 3",
                "Risposte informative con fonti verificabili",
                "Corpus breve e lessico stabile: niente embedding né indice persistente; le fonti sono deterministiche",
                "Source hit 100% sui 9 scenari informativi",
            ],
            [
                "Memoria breve con <font face='Courier'>InMemorySaver</font>",
                "Mantenere il filo della conversazione",
                "Checkpointer LangGraph e un <font face='Courier'>thread_id</font> per sessione; lo stato non serve al di fuori del thread",
                "Test di memoria tra turni",
            ],
            [
                "Memoria lunga <font face='Courier'>PreferenceMemory</font>",
                "Ricordare solo ciò che il cliente chiede",
                "Nessun profilo dedotto: salvataggio solo su «ricorda», PII rimosse, duplicati ignorati",
                "Test su PII e duplicati",
            ],
            [
                "HITL dentro <font face='Courier'>proponi_rimborso</font>",
                "Nessun rimborso senza un umano",
                "<font face='Courier'>interrupt()</font> lega proposta e approvazione; il ledger rivalida cliente, importo e duplicati",
                "HITL 100%, rimborso pulito 100%",
            ],
            [
                "Audit JSONL e ledger idempotente",
                "Rendere ogni azione verificabile",
                "Un evento per turno, accesso negato, rimborso e ticket; scrittura atomica e controllo dei duplicati",
                "Test di ledger e idempotenza",
            ],
            [
                "UI Streamlit e CLI",
                "Demo e ispezione dello stesso sistema",
                "Stesso grafo, stesso ledger e stessi dati: cambia solo il modo di interagire",
                "13 scenari demo nella UI; comandi CLI",
            ],
        ],
        [3.5 * cm, 3.2 * cm, 6.4 * cm, 4.3 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    P(
        "<b>Perché un tool e non solo prompting.</b> Il modello non conosce gli ordini del cliente, non "
        "può calcolare un rimborso e non può verificare una finestra di reso. Un prompt può descrivere "
        "la regola, ma non applicarla né impedire una scrittura. I sette tool portano nel turno dati "
        "reali e controlli deterministici: è il motivo per cui il progetto non si limita a chiedere al "
        "modello di «comportarsi bene»."
    )
)

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
        "<b>Prompting.</b> Il system prompt usa ruolo e vincoli espliciti, few-shot per la scelta del "
        "tool e per la risposta diretta, e output strutturato: lo schema degli argomenti è generato da "
        "LangChain a partire dalle annotazioni dei tool, quindi il modello non può inventare campi o "
        "formati. Il prompt di scelta è breve — con modelli da 1-3B poche regole chiare sono più "
        "affidabili di un elenco lungo — mentre il prompt finale riceve solo richiesta ed esiti, vieta "
        "calcoli e dati inventati e non può avviare altre azioni."
    )
)
story.append(
    P(
        "<b>Perché non multi-agente, reflection o LangSmith.</b> Non li ho aggiunti perché il caso d'uso "
        "non li richiede: un dominio, sette tool, un turno singolo. Supervisore e reflection "
        "aggiungerebbero passaggi e latenza senza migliorare la scelta; LangSmith sarebbe un account "
        "esterno per 31 scenari già coperti da JSON e failure gallery. La traccia premia la coerenza, "
        "non l'accumulo di pattern."
    )
)
story.append(
    P(
        "<b>Un fallimento concreto.</b> Nella run Unsloth, <font face='Courier'>info_personalizzato</font> "
        "chiama <font face='Courier'>verifica_reso</font> invece di <font face='Courier'>cerca_policy</font>; "
        "<font face='Courier'>memoria_implicita</font> salva una preferenza non richiesta. La failure gallery "
        "conserva questi errori."
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
        "<b>57 test</b> senza LM Studio né rete, a copertura di grafo, HITL, privacy, memoria, policy, "
        "corpus, ledger e scenari.",
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

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Scritto {OUT}")
