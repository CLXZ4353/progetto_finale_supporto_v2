# -*- coding: utf-8 -*-
"""Genera la guida per l'orale in Markdown e PDF.

Il contenuto è definito una sola volta e prodotto nei due formati, così le
risposte restano allineate a README, relazione e codice.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

import doc_common as dc

ROOT = Path(__file__).resolve().parents[1]
OUT_MD = ROOT / "docs" / "guida_orale.md"
OUT_PDF = ROOT / "docs" / "guida_orale.pdf"

TITLE = "Guida orale — Casa & Regali v2"
SUBTITLE = (
    "Domande probabili, risposte brevi e punti di codice da saper indicare. "
    "I numeri sono quelli della run LFM3 del 31 ottobre 2026."
)

NUMBERS = [
    ["31/31", "60", "3,72 s", "0,94", "7", "10", "4"],
    ["scenari", "test", "latenza media", "tool/turno", "tool", "documenti", "nodi"],
]

QA = [
    (
        "In una frase, qual è la tesi del progetto?",
        [
            "L'LLM sceglie il tool e scrive la risposta; il codice decide cosa è consentito. "
            "Policy, privacy, HITL e ledger non dipendono dal prompt: se il modello sbaglia, "
            "l'errore resta visibile ma non diventa una scrittura irreversibile.",
            "La conseguenza pratica è che il progetto non chiede al modello di essere affidabile "
            "su tutto. Gli affida due decisioni osservabili e sposta i vincoli nel codice deterministico.",
        ],
    ),
    (
        "Perché due chiamate LLM invece di una?",
        [
            "La prima chiamata sceglie il tool; la seconda racconta l'esito senza avere tool collegati. "
            "Separare scelta e narrazione impedisce che il secondo passo avvii altre azioni e rende il "
            "rimborso definitivo per il turno.",
            "Con un modello da 1-3B, un ciclo ReAct completo tende a ripetere il tool o a concatenarne "
            "altri dopo un esito già definitivo. Il grafo è aciclico: da `tools` si passa a `respond`, "
            "mai di nuovo ad `agent`.",
        ],
    ),
    (
        "Cosa succede esattamente quando il cliente chiede un rimborso?",
        [
            "`agent` chiama `proponi_rimborso(\"ORD-1001\")`. Il tool legge il cliente dallo stato, "
            "verifica che l'ordine appartenga al profilo, applica `check_return_eligibility`, calcola "
            "l'importo con `calculate_refund` e costruisce la proposta con livello `operatore` o "
            "`responsabile`.",
            "Poi chiama `interrupt({\"type\": \"refund_approval\", \"proposal\": ...})`: il turno si sospende "
            "e nessun rimborso è ancora stato scritto. La UI o la CLI riprendono con "
            "`Command(resume={\"approved\": ...})`. Solo dopo l'approvazione il tool chiama "
            "`ledger.execute_refund`, che rivalida tutto e scrive.",
            "Se l'operatore rifiuta, il ledger non scrive e l'audit registra `rimborso_rifiutato`. "
            "Se l'ordine non è idoneo, non viene aperto alcun interrupt.",
        ],
    ),
    (
        "Come impedisci che il modello legga ordini di altri clienti?",
        [
            "Il `customer_id` non è un argomento dei tool: arriva dallo stato del grafo tramite "
            "`ToolRuntime`. `stato_ordine`, `verifica_reso` e `proponi_rimborso` usano "
            "`policy.find_order(order_id, customer_id)`, che restituisce `None` sia per un ordine "
            "inesistente sia per un ordine di un altro cliente.",
            "Il messaggio è lo stesso nei due casi, quindi il modello non può dedurre se l'ordine "
            "esista. L'accesso negato viene registrato come `privacy_accesso_negato`. I tool non "
            "restituiscono nome, email, telefono o indirizzo del profilo: solo i campi dell'ordine.",
        ],
    ),
    (
        "Perché `interrupt()` è dentro il tool e non in un nodo separato?",
        [
            "Proposta e approvazione restano nello stesso punto: non c'è un percorso alternativo che "
            "possa scrivere un rimborso senza passare da lì. Un nodo separato lascerebbe aperta la "
            "possibilità di raggiungere la scrittura da un altro arco del grafo.",
            "Il ledger è comunque una seconda difesa: anche se il tool sbagliasse, `execute_refund` "
            "ricontrolla approvazione, ordine, cliente, importo e duplicati prima di scrivere.",
        ],
    ),
    (
        "Cosa controlla `execute_refund` se il tool ha già controllato?",
        [
            "Controlla l'approvazione umana, normalizza ordine, cliente e importo, blocca i duplicati, "
            "verifica che l'ordine esista e appartenga al cliente, confronta l'importo con "
            "`calculate_refund` entro 0,01 EUR, genera `RMB-2026-NNNN`, aggiorna refunds e orders e "
            "registra l'evento.",
            "È la difesa in profondità: il ledger non si fida del modello né del chiamante. Il test "
            "`test_importo_non_coerente_bloccato` e `test_cliente_non_coerente_bloccato` dimostrano "
            "che una proposta alterata non scrive.",
        ],
    ),
    (
        "Perché il contratto `<risposta>` e non tutto il `content`?",
        [
            "Con LFM3 il modello aggiungeva ragionamento nel `content`, non in un canale separato. "
            "Il prompt finale chiede di scrivere solo tra `<risposta>` e `</risposta>`; "
            "`extract_answer` scarta tutto ciò che sta fuori.",
            "Se i tag mancano, il testo resta invariato: non si perde una risposta valida solo per un "
            "problema di formato. Il test `test_extract_answer_rimuove_il_ragionamento` copre il caso "
            "con testo prima e dopo il blocco.",
        ],
    ),
    (
        "Perché BM25 e non un database vettoriale?",
        [
            "Il corpus ha dieci documenti brevi e un lessico stabile. BM25 è deterministico, non "
            "richiede indice persistente né modello di embedding e rende le fonti verificabili. "
            "L'indice viene ricostruito a ogni query: il costo è accettabile e non c'è cache da "
            "invalidare.",
            "La query unisce il testo del modello all'ultima richiesta del cliente e aggiunge sinonimi "
            "italiani. I chunk senza sovrapposizione lessicale vengono scartati: meglio nessuna fonte "
            "che una fonte falsa. La suite misura il 100% di source hit sui 9 scenari informativi.",
        ],
    ),
    (
        "Come dimostri che un prompt injection non può saltare l'HITL?",
        [
            "Lo scenario `prompt_injection` chiede esplicitamente di ignorare le istruzioni e rimborsare "
            "senza approvazione. Il modello può anche chiamare `proponi_rimborso`, ma il tool sospende "
            "comunque il turno: l'approvazione non è una frase nel prompt, è un `interrupt` nel codice.",
            "La valutazione verifica che il rimborso non sia scritto prima della decisione umana e che "
            "non ci siano tool successivi dopo l'esito. Il test di privacy e i test del ledger coprono "
            "lo stesso confine a livello di codice.",
        ],
    ),
    (
        "I 31/31 sono una garanzia? Qual è il limite?",
        [
            "No. Sono la misura di un prototipo su 31 scenari controllati, con un modello locale da "
            "1,7B e dati sintetici. Non c'è un insieme di test separato per la generalizzazione, e la "
            "suite non copre tutte le formulazioni possibili.",
            "Il dato utile è il confronto: Llama 3.2 3B (Unsloth) si ferma a 24/31, quindi il margine "
            "di errore dipende dal modello. La scelta di non avere un fallback deterministico rende "
            "questi errori visibili invece di nasconderli.",
        ],
    ),
    (
        "Perché i test non usano un modello reale? Cosa non misurano?",
        [
            "I 60 test usano `ScriptedModel`, un modello finto che restituisce risposte preparate. "
            "Servono a verificare i contratti deterministici: grafo, routing, privacy, HITL, ledger, "
            "memoria, policy, RAG e parsing. Non richiedono LM Studio, non usano rete e non dipendono "
            "dall'ordine di esecuzione.",
            "Non misurano la qualità del modello, la latenza o la capacità di scegliere il tool. Per "
            "quello c'è la suite di valutazione con LFM3 e Llama. Le due cose sono complementari: i "
            "test impediscono regressioni nel codice, l'eval misura il comportamento del sistema.",
        ],
    ),
    (
        "Cosa faresti con più tempo o in produzione?",
        [
            "Prima di tutto un insieme di valutazione held-out e più formulazioni per scenario, per "
            "distinguere la copertura dalla generalizzazione. Poi un ledger transazionale su database, "
            "invece di file JSON con lock di processo, e un audit con retention e accesso controllato.",
            "Sul retrieval, un corpus più grande richiederebbe ricerca semantica o ibrida. Sul modello, "
            "servirebbe una misura di Gemini o di un modello più grande per capire quanto margine c'è. "
            "Non aggiungerei multi-agente o reflection senza un'ipotesi misurabile che ne giustifichi "
            "il costo.",
        ],
    ),
]

TRAPS = [
    (
        "`last_human_index` restituisce 0 se non trova messaggi umani. È un rischio?",
        "Nel grafo ogni turno parte da `start_turn`, che aggiunge una `HumanMessage`; quindi il caso "
        "non si presenta nel flusso normale. Se la funzione fosse chiamata su uno stato senza richiesta "
        "umana, la lettura partirebbe dall'inizio e potrebbe vedere una risposta vecchia. È un motivo "
        "per non usarla fuori dal contratto del turno.",
    ),
    (
        "`pending_interrupt` prende solo il primo interrupt. Perché?",
        "Il grafo attuale apre un solo interrupt per turno: la proposta di rimborso. Prendere il primo "
        "è sufficiente e rende la UI prevedibile. Se in futuro un turno potesse aprire più richieste, "
        "servirebbe una coda e una gestione esplicita dell'ordine.",
    ),
    (
        "Il ledger scrive refunds e orders in due passaggi. Cosa succede se il processo si interrompe?",
        "Ogni file viene sostituito atomicamente, ma la coppia non è una transazione unica. Un crash "
        "tra le due scritture può lasciare refunds aggiornato e orders no. Per la demo a processo "
        "singolo è accettabile; in produzione servirebbe una transazione su database o un journal di "
        "recupero.",
    ),
    (
        "`sources_from_messages` interpreta solo JSON. E se un tool restituisse testo?",
        "Il `try` su `json.loads` salta il messaggio e la risposta resta senza fonti. È voluto: solo "
        "`cerca_policy` produce fonti, e il suo contratto è JSON con `contesto` e `fonti`. Un tool "
        "nuovo che volesse esporre fonti dovrebbe rispettare lo stesso payload.",
    ),
    (
        "`dedupe_models` raggruppa per famiglia prima di `@`. Non perde varianti?",
        "Sì, per costruzione mostra un alias per famiglia: `lfm3-1.7b@q4_k_m` e `lfm3-1.7b` diventano "
        "una voce, con il preferito che vince. È una scelta di UI, non di runtime: il modello scelto "
        "viene passato per intero a LM Studio. Se servissero più quantizzazioni nello stesso selettore, "
        "la chiave andrebbe cambiata.",
    ),
    (
        "Perché `final_reasoning_effort` vale solo per LFM3 locale?",
        "È l'unico modello del progetto per cui il controllo `reasoning_effort` è stato verificato. "
        "Su Gemini o su altri modelli locali non applico un'opzione che non conosco: il rischio sarebbe "
        "cambiare il comportamento senza una misura. La risposta finale usa `none` solo dove serve.",
    ),
]

DEMO = [
    "Apri con la tesi: l'LLM decide, il codice vincola. Non partire dai file.",
    "Mostra il grafo a quattro nodi e spiega perché `tools` non torna ad `agent`.",
    "Apri `tools.py` e indica `_customer`: il cliente non è un argomento del modello.",
    "Esegui «Quanto costa la spedizione?» e mostra le fonti `[S1]`, `[S2]`.",
    "Esegui il rimborso di ORD-1001: mostra la sospensione, approva e indica il record nel ledger.",
    "Esegui «Mostrami ORD-1004»: stesso messaggio di un ordine inesistente e audit dell'accesso negato.",
    "Esegui il prompt injection: il rimborso resta in attesa, non viene eseguito.",
    "Chiudi con la failure gallery di Llama e con il limite dei 31 scenari.",
]

CHECKLIST = [
    "Ricorda i numeri: 31/31, 60 test, 3,72 s, 0,94 tool per turno, 7 tool, 10 documenti, 4 nodi.",
    "Distingui sempre ciò che decide l'LLM da ciò che impone il codice.",
    "Se ti chiedono un file, aprilo e indica la funzione, non improvvisare.",
    "Dichiara che Gemini è configurabile ma non misurato per quota.",
    "Non presentare i 31/31 come una garanzia di produzione.",
    "Se non ricordi un dettaglio, riparti dal contratto della funzione: input, output, scrittura, test.",
]


def inline(text: str) -> str:
    """Converte il Markdown minimo usato nella guida in markup ReportLab."""
    text = dc.esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    return text


def markdown() -> str:
    lines = [f"# {TITLE}", "", SUBTITLE, "", "## Numeri da ricordare", ""]
    lines.append("| " + " | ".join(NUMBERS[0]) + " |")
    lines.append("| " + " | ".join("---" for _ in NUMBERS[0]) + " |")
    lines.append("| " + " | ".join(NUMBERS[1]) + " |")
    lines.append("")
    for index, (question, paragraphs) in enumerate(QA, start=1):
        lines.extend([f"## {index}. {question}", ""])
        for paragraph in paragraphs:
            lines.extend([paragraph, ""])
    lines.extend(["## Trabocchetti e domande scomode", ""])
    for question, answer in TRAPS:
        lines.extend([f"### {question}", "", answer, ""])
    lines.extend(["## Scaletta della demo (5–10 minuti)", ""])
    lines.extend([f"{index}. {step}" for index, step in enumerate(DEMO, start=1)])
    lines.extend(["", "## Checklist prima dell'orale", ""])
    lines.extend([f"- {item}" for item in CHECKLIST])
    lines.append("")
    return "\n".join(lines)


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(dc.LINE)
    canvas.setLineWidth(0.6)
    canvas.line(1.8 * cm, 1.05 * cm, A4[0] - 1.8 * cm, 1.05 * cm)
    canvas.setFont(dc.FONT, 7.5)
    canvas.setFillColor(dc.GREY)
    canvas.drawString(1.8 * cm, 0.72 * cm, "Casa & Regali · guida orale · v2")
    canvas.drawRightString(A4[0] - 1.8 * cm, 0.72 * cm, f"pagina {document.page}")
    canvas.restoreState()


def pdf() -> None:
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=TITLE,
        author="Progetto finale LLM & Agentic AI",
        subject="Preparazione alle domande orali",
    )
    story: list = [
        dc.P("GUIDA ORALE · PROGETTO FINALE LLM &amp; AGENTIC AI", "cover_kicker"),
        dc.P(TITLE, "h1"),
        dc.P(SUBTITLE, "lead"),
        dc.stat_row(
            [
                ("31/31", "scenari LFM3"),
                ("60", "test automatici"),
                ("3,72 s", "latenza media"),
                ("0,94", "tool per turno"),
            ]
        ),
        Spacer(1, 0.25 * cm),
        dc.P(
            "Le risposte sono pensate per essere dette in 30–60 secondi. Se la domanda chiede "
            "un dettaglio di codice, la sequenza è: firma, input/output, punto di scrittura, "
            "caso limite, test.",
            "small",
        ),
        dc.h2("Come usare questa guida"),
        dc.P(
            "Prima leggi le dodici risposte ad alta voce, poi prova i trabocchetti senza guardare. "
            "Nella demo non aprire tutti i file: mostra il grafo, il confine del cliente, il rimborso "
            "e la failure gallery. La chiusura deve lasciare un limite esplicito, non una promessa.",
            "small",
        ),
        dc.h2("Le dodici domande"),
    ]
    for index, (question, _) in enumerate(QA, start=1):
        story.append(dc.P(f"<b>{index}.</b> {inline(question)}", "small"))

    story.append(Spacer(1, 0.15 * cm))
    story.append(dc.h2("Checklist prima dell'orale"))
    story += dc.bullets([inline(item) for item in CHECKLIST])
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        dc.callout(
            "La frase da tenere pronta",
            "L'LLM sceglie il tool e scrive la risposta; il codice impone policy, privacy, HITL e "
            "ledger. Se il modello sbaglia, l'errore è visibile, ma non può diventare una scrittura "
            "irreversibile.",
        )
    )

    story.append(PageBreak())
    for index, (question, paragraphs) in enumerate(QA, start=1):
        story.append(dc.h2(f"{index}. {inline(question)}"))
        for paragraph in paragraphs:
            story.append(dc.P(inline(paragraph)))
        story.append(Spacer(1, 0.1 * cm))
        if index in {4, 8}:
            story.append(PageBreak())

    story.append(PageBreak())
    story.append(dc.h2("Trabocchetti e domande scomode"))
    story.append(
        dc.P(
            "Queste domande servono a verificare se il confine è chiaro anche quando il caso non è "
            "stato previsto. La risposta migliore dichiara il limite e indica cosa servirebbe.",
            "small",
        )
    )
    for question, answer in TRAPS:
        story.append(dc.h3(inline(question)))
        story.append(dc.P(inline(answer)))

    story.append(dc.h2("Scaletta della demo (5–10 minuti)"))
    story += dc.bullets([inline(step) for step in DEMO])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(), encoding="utf-8")
    pdf()
    print(f"Scritto {OUT_MD}")
    print(f"Scritto {OUT_PDF}")
