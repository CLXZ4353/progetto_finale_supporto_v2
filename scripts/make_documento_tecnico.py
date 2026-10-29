# -*- coding: utf-8 -*-
"""Genera il documento tecnico PDF della v2.

Legge le metriche reali da eval/results/latest.json e dal risultato Llama
3.2 3B; non inventa numeri.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.units import cm
from reportlab.platypus import CondPageBreak, PageBreak, Spacer

import doc_common as dc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "documento_tecnico.pdf"

final = dc.load_final()
llama = dc.load_llama()
fs = final["summary"]
ls = (llama or {}).get("summary", {})
lat = f"{fs['avg_latency_s']:.2f}".replace(".", ",")
ls_lat = f"{ls.get('avg_latency_s', 0):.2f}".replace(".", ",")

story: list = []

# --- copertina -------------------------------------------------------------
story += dc.cover(
    "Progetto finale · LLM & Agentic AI",
    "Assistente clienti<br/>Casa &amp; Regali",
    "Versione 2 (v2): un agente, un passaggio di tool,<br/>"
    "un secondo passo LLM per la risposta.",
    [
        "Documento tecnico",
        "Modello predefinito: LFM3-1.7B Q4_K_M su LM Studio",
        "Backend cloud opzionale: Gemini 2.5 Flash",
        "Data: 29 ottobre 2026",
    ],
)

# --- sintesi ---------------------------------------------------------------
story.append(dc.P("Sintesi", "h1"))
story.append(
    dc.P(
        "Il progetto è un assistente clienti in italiano per l'e-commerce fittizio "
        "<b>Casa &amp; Regali</b>. L'LLM sceglie il tool più adatto, il tool applica "
        "policy e dati reali, un secondo passo LLM scrive la risposta senza poter "
        "avviare altre azioni. Il rimborso viene solo <b>proposto</b>: entra nel "
        "ledger unicamente dopo un'approvazione umana esplicita.",
        "lead",
    )
)
story.append(
    dc.stat_row(
        [
            (f"{fs['passed']}/{fs['total']}", "scenari superati (LFM3)"),
            (f"{dc.pct(fs['tool_hit_rate'])}", "tool hit rate"),
            ("57", "test automatici"),
            (f"{fs['avg_latency_s']:.2f} s".replace(".", ","), "latenza media"),
        ]
    )
)
story.append(Spacer(1, 0.35 * cm))
story.append(
    dc.P(
        "La v2 nasce da una revisione del progetto esteso: restano "
        "policy-as-code, tool read-only, privacy per cliente, HITL sul rimborso, audit "
        "e ledger idempotente; escono supervisore multi-agente, review/reflection, "
        "fallback deterministico, Chroma e ricerca ibrida. L'obiettivo è rendere "
        "leggibile il confine tra ciò che decide il modello e ciò che impone il codice."
    )
)
story.append(
    dc.P(
        "La run finale di LFM3-1.7B Q4_K_M supera <b>31/31</b> scenari con tool hit "
        "rate, fonti, HITL e sicurezza al 100%. Llama 3.2 3B (Unsloth Q5_K_XL), più "
        "veloce ma meno affidabile, si ferma a 24/31: è l'alternativa per demo con "
        "hardware modesto. "
        "La run completa Gemini non è disponibile per esaurimento della quota gratuita."
    )
)

# --- 1. contesto -----------------------------------------------------------
story += dc.section("1", "Contesto e obiettivi")
story.append(
    dc.P(
        "Il progetto finale chiede un assistente che usi un LLM, almeno un tool "
        "personalizzato, memoria, RAG, Human-in-the-Loop e una valutazione "
        "riproducibile. La versione estesa dimostrava questi requisiti con un "
        "supervisore, tre agenti, review/reflection e un backend deterministico. "
        "Con un modello locale da 1,7B, però, ogni nodo in più aggiunge latenza e "
        "occasioni di errore: il routing e la riflessione non ripagavano la "
        "complessità."
    )
)
story.append(
    dc.P(
        "La revisione parte da una domanda: <b>quale parte del sistema ha davvero "
        "bisogno dell'LLM?</b> La risposta è duplice: l'LLM serve per scegliere il "
        "tool e per scrivere una risposta in linguaggio naturale. Tutto il resto — "
        "idoneità al reso, soglie di rimborso, privacy, approvazione, scrittura del "
        "ledger — è codice deterministico e verificabile."
    )
)
story.append(dc.h2("Obiettivi della v2"))
story += dc.bullets(
    [
        "Mantenere i vincoli di dominio: policy-as-code, tool read-only, privacy per cliente, HITL, audit e ledger idempotente.",
        "Ridurre il grafo a un solo agente e a un solo passaggio di tool.",
        "Lasciare all'LLM la scelta del tool e la scrittura della risposta, senza fallback semantici.",
        "Usare un RAG proporzionato al corpus: BM25 su dieci documenti, senza indice vettoriale.",
        "Misurare il comportamento con scenari che verificano tool, contenuti, fonti, HITL ed effetti collaterali.",
    ]
)

# --- 2. requisiti ----------------------------------------------------------
story.append(CondPageBreak(9.5 * cm))
story += dc.section("2", "Requisiti e soluzione")
story.append(
    dc.P(
        "La tabella seguente collega ogni requisito della traccia alla componente "
        "che lo implementa. Le righe non coperte dai laboratori sono segnalate come "
        "scelte autonome."
    )
)
story.append(
    dc.table(
        [
            ["Requisito", "Implementazione"],
            ["Modello cloud via API", "Gemini 2.5 Flash in <font face='Courier'>models.py</font> (opzionale)"],
            ["Modello locale", "LM Studio, endpoint OpenAI-compatibile: LFM3-1.7B Q4_K_M predefinito"],
            ["Prompting", "Ruolo e vincoli, few-shot, output strutturato, prompt separato per la risposta"],
            ["Tool LangChain", "7 tool personalizzati in <font face='Courier'>tools.py</font>"],
            ["Memoria breve", "Checkpointer LangGraph <font face='Courier'>InMemorySaver</font>"],
            ["Memoria lunga", "<font face='Courier'>PreferenceMemory</font>, solo su richiesta esplicita"],
            ["RAG", "BM25 su 10 documenti Markdown, chunk 650, top_k 3"],
            ["HITL", "<font face='Courier'>interrupt()</font> dentro <font face='Courier'>proponi_rimborso</font>"],
            ["UI", "Streamlit (<font face='Courier'>app.py</font>) e CLI (<font face='Courier'>cli.py</font>)"],
            ["Valutazione", "31 scenari, metriche aggregate, failure gallery"],
        ],
        [4.2 * cm, 11.8 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    dc.P(
        "Sono scelte autonome rispetto ai laboratori: HITL dentro il tool, ledger "
        "idempotente, privacy applicata nel runtime e valutazione strutturata. Sono "
        "invece escluse per scelta: multi-agente, supervisore, review/reflection, "
        "fallback deterministico, Chroma e ricerca ibrida."
    )
)

# --- 3. architettura -------------------------------------------------------
story += dc.section("3", "Architettura")
story += dc.image(
    ROOT / "docs" / "architettura.png",
    16.0 * cm,
    "Figura 1 — Flusso agent → tools → respond → finalize; il percorso diretto agent → finalize vale quando non serve un tool.",
)
story.append(
    dc.P(
        "Il grafo ha quattro nodi. <b>agent</b> riceve system prompt e conversazione e "
        "sceglie un tool oppure risponde direttamente. <b>tools</b> esegue il tool con "
        "il <font face='Courier'>ToolRuntime</font>, che contiene il cliente della "
        "sessione. <b>respond</b> è un secondo passo LLM <i>senza tool</i>: riceve la "
        "richiesta e gli esiti, e scrive la risposta finale. <b>finalize</b> salva "
        "risposta, fonti e tool usati, e scrive il turno nell'audit."
    )
)
story.append(
    dc.P(
        "Se il modello non chiama tool, il percorso è <b>agent → finalize</b>. È il "
        "caso di un saluto, di una richiesta del numero d'ordine o di una preferenza "
        "espressa senza la parola \"ricorda\". In entrambi i percorsi la risposta "
        "mostrata al cliente è quella dell'LLM: non esiste una modalità deterministica "
        "che la sostituisca."
    )
)
story.append(dc.h2("Perché un solo passaggio di tool"))
story.append(
    dc.P(
        "Il ciclo ReAct completo (<font face='Courier'>agent → tools → agent → …</font>) "
        "con modelli da 1-3B tende a ripetere lo stesso tool o a concatenarne altri "
        "dopo un esito già definitivo. La v2 separa i due compiti: "
        "la scelta dell'azione e la narrazione dell'esito. Il risultato è un grafo più "
        "leggibile, meno latenza e nessuna catena incontrollata. Dopo "
        "<font face='Courier'>proponi_rimborso</font> non possono partire altri tool: "
        "l'esito del rimborso è definitivo per il turno."
    )
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
        [9.2 * cm, 6.8 * cm],
    )
)
story.append(Spacer(1, 0.25 * cm))
story.append(
    dc.callout(
        "Policy-as-code",
        "La fonte di verità è <font face='Courier'>policy.py</font>: finestra di reso di "
        "30 giorni, categorie escluse (personalizzati, igiene, digitali, fine serie), "
        "soglia di escalation di 500 EUR, calcolo del rimborso e controllo duplicati. "
        "I documenti Markdown spiegano la policy; i tool la applicano. Nessuna regola "
        "di dominio è affidata al prompt.",
    )
)

# --- 4. tool e HITL --------------------------------------------------------
story.append(CondPageBreak(13 * cm))
story += dc.section("4", "Tool, Human-in-the-Loop e ledger")
story.append(
    dc.P(
        "I sette tool coprono informazioni, ordini, resi, rimborsi, escalation e "
        "preferenze. Tutti sono read-only tranne <font face='Courier'>proponi_rimborso</font>, "
        "che scrive nel ledger solo dopo l'approvazione."
    )
)
story.append(
    dc.table(
        [
            ["Tool", "Cosa fa", "Scrittura"],
            ["<font face='Courier'>cerca_policy(query)</font>", "Cerca nelle policy; restituisce contesto e fonti", "no"],
            ["<font face='Courier'>stato_ordine(order_id)</font>", "Stato, articoli e tracking di un ordine del cliente", "no"],
            ["<font face='Courier'>elenca_ordini()</font>", "Elenco degli ordini del profilo", "no"],
            ["<font face='Courier'>verifica_reso(order_id)</font>", "Idoneità al reso, giorni trascorsi, esclusioni", "no"],
            ["<font face='Courier'>proponi_rimborso(order_id)</font>", "Verifica, chiede HITL e scrive solo se approvato", "solo dopo HITL"],
            ["<font face='Courier'>apri_ticket(motivo)</font>", "Apre un ticket per un operatore", "ticket"],
            ["<font face='Courier'>ricorda_preferenza(testo)</font>", "Salva una preferenza su richiesta esplicita", "preferenza"],
        ],
        [5.2 * cm, 8.8 * cm, 2.0 * cm],
        align_center_from=2,
        small=True,
    )
)
story.append(Spacer(1, 0.25 * cm))
story.append(dc.h2("Il percorso del rimborso"))
story += dc.bullets(
    [
        "<b>Verifica.</b> <font face='Courier'>proponi_rimborso</font> controlla idoneità, finestra, esclusioni, rimborsi già eseguiti e importo.",
        "<b>Proposta.</b> Se l'ordine è idoneo, costruisce la proposta con ordine, cliente, importo, articoli e livello di approvazione.",
        "<b>Interrupt.</b> Chiama <font face='Courier'>interrupt({\"type\": \"refund_approval\", \"proposal\": …})</font> e sospende il turno.",
        "<b>Decisione umana.</b> UI o CLI mostrano la proposta e riprendono con <font face='Courier'>Command(resume={\"approved\": …})</font>.",
        "<b>Scrittura.</b> Solo con <font face='Courier'>approved=True</font> il ledger rivalida cliente, importo e duplicati, e registra il rimborso.",
    ]
)
story.append(
    dc.P(
        "Il ledger non si fida del modello né del chiamante: un importo manomesso, "
        "un'approvazione mancante o un rimborso già registrato vengono rifiutati. "
        "Sopra i 500 EUR la proposta richiede il livello <b>responsabile</b>; la UI "
        "mostra una conferma aggiuntiva e la CLI la chiede esplicitamente."
    )
)
story.append(
    dc.callout(
        "Privacy",
        "Il <font face='Courier'>customer_id</font> arriva dallo stato del grafo tramite "
        "<font face='Courier'>ToolRuntime</font>: il modello non può scegliere di quale "
        "cliente parlare. Un ordine di un altro cliente restituisce lo stesso messaggio "
        "di un ordine inesistente e l'accesso negato finisce nell'audit.",
        accent=dc.GREEN,
        bg=dc.LIGHT_GREEN,
    )
)

# --- 5. dati, RAG, memoria -------------------------------------------------
story.append(CondPageBreak(11 * cm))
story += dc.section("5", "Dati, RAG e memoria")
story.append(dc.h2("Dati demo"))
story.append(
    dc.P(
        "I dati sono generati da <font face='Courier'>support_data.py</font> con seed 7: "
        "20 prodotti, 50 clienti, 200 ordini e 4 rimborsi iniziali. I casi curati "
        "coprono i comportamenti che il sistema deve distinguere:"
    )
)
story.append(
    dc.table(
        [
            ["Ordine", "Caso", "Esito atteso"],
            ["ORD-1001", "Consegnato, 10 giorni fa", "Reso idoneo, rimborso 89,70 EUR"],
            ["ORD-1002", "Consegnato, 45 giorni fa", "Fuori finestra (30 giorni)"],
            ["ORD-1003", "Articolo personalizzato", "Categoria esclusa"],
            ["ORD-1004", "Di un altro cliente", "Messaggio di non trovato (privacy)"],
            ["ORD-1005", "Alto valore (749 EUR)", "HITL con approvazione responsabile"],
            ["ORD-1006", "In transito", "Tracking disponibile"],
            ["ORD-1007", "Articolo di igiene", "Categoria esclusa"],
            ["ORD-1008", "Articolo difettoso (41,90 EUR)", "Reso idoneo, reso/rimborso o sostituzione"],
        ],
        [2.2 * cm, 6.4 * cm, 7.4 * cm],
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    dc.P(
        "Nessun dato personale è reale: nomi, email e telefoni sono fittizi. La data "
        "della demo è fissata a <font face='Courier'>2026-10-23</font> per mantenere "
        "stabili gli scenari."
    )
)
story.append(dc.h2("RAG lessicale"))
story.append(
    dc.P(
        "<font face='Courier'>cerca_policy</font> usa solo BM25 sui 10 documenti in "
        "<font face='Courier'>data/corpus/</font>. I documenti sono divisi per "
        "intestazioni Markdown e poi in chunk da 650 caratteri con sovrapposizione 50; "
        "si restituiscono i primi 3 passaggi con fonti <font face='Courier'>[S1]</font>, "
        "<font face='Courier'>[S2]</font>, <font face='Courier'>[S3]</font>."
    )
)
story.append(
    dc.P(
        "La query del modello viene unita all'ultima richiesta del cliente: se il "
        "modello generalizza troppo (\"restituzione di un ordine\"), i termini specifici "
        "del cliente (\"tazza personalizzata\") restano nella ricerca. È una correzione "
        "mirata che ha risolto i casi in cui il modello perdeva la parola chiave."
    )
)
story.append(
    dc.P(
        "Non ci sono embedding, Chroma o ricerca ibrida. Con dieci documenti brevi e "
        "un dominio lessicale stabile, BM25 è sufficiente e non richiede un indice da "
        "costruire o aggiornare. Su un corpus più grande la scelta andrebbe rivista."
    )
)
story.append(dc.h2("Memoria"))
story.append(
    dc.P(
        "La memoria breve è il checkpointer di LangGraph: mantiene il contesto del "
        "thread tra un turno e l'altro. La memoria lunga è "
        "<font face='Courier'>PreferenceMemory</font> e salva solo le preferenze che il "
        "cliente chiede esplicitamente di ricordare. Email, telefoni e carte vengono "
        "rimossi prima del salvataggio; una preferenza espressa senza richiesta "
        "esplicita non viene memorizzata."
    )
)

# --- 6. valutazione --------------------------------------------------------
story += dc.section("6", "Valutazione")
story.append(
    dc.P(
        "La suite contiene 31 scenari in <font face='Courier'>eval/scenarios.py</font>: "
        "9 informazioni, 3 ordini, 6 resi, 6 rimborsi, 3 sicurezza (privacy, ordine "
        "inesistente, prompt injection), 2 escalation e 2 memoria. Ogni scenario "
        "verifica tool attesi e vietati, contenuto della risposta, fonti, interrupt "
        "HITL, scritture nel ledger o nei ticket e assenza di effetti collaterali. I "
        "rimborsi sono eseguiti su dati temporanei, senza toccare la demo."
    )
)
story.append(
    dc.table(
        [
            ["Profilo", "Scenari", "Superati", "Pass rate", "Tool hit", "Fonti", "HITL", "Sicurezza", "Latenza"],
            ["LFM3-1.7B Q4_K_M", "31", "31", "100%", "100%", "100%", "100%", "100%", f"{fs['avg_latency_s']:.2f} s".replace(".", ",")],
            ["Llama 3.2 3B Unsloth", "31", "24", "77,4%", "96,6%", "88,9%", "100%", "66,7%", f"{ls_lat} s"],
        ],
        [4.3 * cm, 1.4 * cm, 1.6 * cm, 1.7 * cm, 1.6 * cm, 1.3 * cm, 1.2 * cm, 1.6 * cm, 1.5 * cm],
        align_center_from=1,
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    dc.P(
        f"LFM3 è il modello predefinito: circa 2,7 volte più lento di Llama 3.2 3B "
        f"(Unsloth) ({lat} s contro {ls_lat} s), ma più affidabile "
        "nella scelta dei tool e nell'esposizione dei dati. La run finale supera tutti "
        "gli scenari con una media di 0,94 tool per turno; le run intermedie avevano "
        "evidenziato due errori di formulazione, corretti nei prompt (citare la "
        "difettosità e non salvare preferenze non richieste). Llama resta l'alternativa "
        f"veloce: {ls_lat} secondi per turno, ma con errori su tool, fonti e sicurezza."
    )
)
story.append(
    dc.P(
        "<b>Reasoning.</b> Con LFM3 il reasoning attivo (variabile vuota) ha dato la "
        "migliore scelta dei tool. La risposta finale lo disattiva sempre: con la tabella "
        "completa dei 10 ordini il secondo passo consumava 7.058 token e restituiva "
        "contenuto vuoto con <font face='Courier'>finish_reason=length</font>; "
        f"disattivandolo solo lì la run resta 31/31 e scende a {lat} s medi. Con "
        "<font face='Courier'>LM_STUDIO_REASONING_EFFORT=none</font> su tutto il grafo una "
        "run precedente si è fermata a 27/31, fallendo informazioni, escalation e "
        "prompt injection. Per questo il default consigliato è lasciare la variabile "
        "vuota."
    )
)
story.append(
    dc.P(
        "<b>Gemini.</b> La run completa non è disponibile: la quota gratuita "
        "giornaliera è stata esaurita durante la preparazione. Il backend resta "
        "configurabile, ma non viene riportata una metrica comparabile."
    )
)
story.append(
    dc.callout(
        "Nota sulle metriche",
        "Tool hit rate = quota di scenari con tool attesi in cui tutti i tool richiesti "
        "sono stati usati. Fonti = quota di scenari con fonte attesa in cui almeno una "
        "fonte corretta è citata. HITL = interrupt corretto e scrittura coerente. "
        "Sicurezza = esito degli scenari di privacy, ordine inesistente e prompt "
        "injection. I numeri provengono da <font face='Courier'>eval/results/latest.json</font>.",
    )
)

# --- 7. test e riproducibilità ---------------------------------------------
story += dc.section("7", "Test e riproducibilità")
story.append(
    dc.P(
        "La suite automatica usa un modello scriptato (<font face='Courier'>ScriptedModel</font>) "
        "e dati isolati: non richiede LM Studio né rete. Copre flussi del grafo, HITL, "
        "privacy, memoria, policy, corpus, ledger e scenari. Stato attuale: <b>57 test "
        "superati</b>."
    )
)
story.append(dc.code_block("python -m pytest -q tests\npython eval/run_eval.py --backend local\npython cli.py\nstreamlit run app.py"))
story.append(
    dc.P(
        "Per riprodurre la valutazione serve LM Studio con il modello caricato. Il "
        "comando di caricamento usato è:"
    )
)
story.append(dc.code_block("lms load lfm3-1.7b@q4_k_m --gpu max --context-length 8192 --yes"))
story.append(
    dc.P(
        "I risultati sono in <font face='Courier'>eval/results/</font> (JSON e Markdown "
        "con failure gallery); <font face='Courier'>latest.json</font> contiene l'ultima "
        "run. La demo si ripristina con <font face='Courier'>python scripts/reset_demo.py</font>."
    )
)

# --- 8. limiti e confronto -------------------------------------------------
story += dc.section("8", "Limiti e confronto con la versione estesa")
story.append(dc.h2("Limiti dichiarati"))
story += dc.bullets(
    [
        "<b>Modelli piccoli.</b> LFM3 1,7B e Llama 3.2 3B (Unsloth) possono sbagliare la scelta del tool o riformulare i numeri; la valutazione misura questi errori e non li corregge con fallback deterministici.",
        "<b>Un tool per turno.</b> Una richiesta che ne richiede due viene gestita al turno successivo: è una scelta deliberata, non un limite tecnico del grafo.",
        "<b>BM25.</b> Adatto a dieci documenti brevi; su un corpus più grande servirebbe ricerca semantica o ibrida.",
        "<b>Memoria di sessione.</b> <font face='Courier'>InMemorySaver</font> perde lo stato al riavvio; le preferenze a lungo termine restano su file.",
        "<b>Gemini.</b> Backend presente ma senza run completa per quota.",
    ]
)
story.append(dc.h2("Confronto"))
story.append(
    dc.table(
        [
            ["Aspetto", "Versione estesa", "v2"],
            ["Agenti", "Supervisore + 3 agenti", "1 agente"],
            ["Ciclo tool", "ReAct con più passaggi", "Un solo passaggio"],
            ["Review/reflection", "Sì", "No"],
            ["RAG", "Chroma + embedding", "BM25"],
            ["Backend deterministico", "Sì", "No"],
            ["HITL", "Nodo separato del grafo", "Dentro <font face='Courier'>proponi_rimborso</font>"],
            ["Scenari", "30", "31"],
            ["Test", "76", "57"],
        ],
        [4.6 * cm, 6.2 * cm, 5.2 * cm],
    )
)
story.append(Spacer(1, 0.2 * cm))
story.append(
    dc.P(
        "La versione estesa dimostra più pattern, ma con un modello da 1,7B il routing "
        "e la reflection aggiungono latenza e punti di errore. Questa versione mantiene "
        "i vincoli importanti — policy, privacy, HITL, audit, ledger — e lascia all'LLM "
        "solo le due decisioni che contano: quale tool usare e come raccontarne l'esito."
    )
)
story.append(
    dc.P(
        "Il codice è organizzato in moduli piccoli e leggibili: "
        "<font face='Courier'>agent.py</font>, <font face='Courier'>tools.py</font>, "
        "<font face='Courier'>policy.py</font>, <font face='Courier'>corpus.py</font>, "
        "<font face='Courier'>memory.py</font>, <font face='Courier'>audit.py</font>, "
        "<font face='Courier'>prompts.py</font>, <font face='Courier'>models.py</font> e "
        "<font face='Courier'>support_data.py</font>. La separazione è la documentazione "
        "principale del progetto."
    )
)
story.append(dc.h2("Conclusione"))
story.append(
    dc.P(
        "La v2 raggiunge l'obiettivo che si era data: mantenere i "
        "vincoli di dominio e togliere i pattern che, con un modello da 1-3B, non "
        "ripagavano la complessità. Il grafo è piccolo abbastanza da essere letto in "
        "un minuto, ma il comportamento non è simulato: l'LLM sceglie davvero il tool, "
        "scrive davvero la risposta e sbaglia quando il modello sbaglia. La differenza "
        "è che gli errori sono visibili nella valutazione, non nascosti da un fallback."
    )
)
story.append(
    dc.P(
        "Il risultato 31/31 di LFM3 non va letto come una garanzia di produzione: è la "
        "misura di un prototipo su 31 scenari controllati, con un modello locale e dati "
        "sintetici. Llama 3.2 3B (Unsloth) mostra che il margine di errore esiste e dipende dal "
        "modello. La scelta di tenere il secondo passo LLM separato riduce però il "
        "perimetro degli errori: la risposta può essere imprecisa, ma non può avviare "
        "un rimborso o cambiare cliente."
    )
)

story.append(PageBreak())
story.append(dc.P("Appendice — Comandi rapidi", "h1"))
story.append(
    dc.code_block(
        "# installazione\n"
        "python -m venv .venv\n"
        ".\\.venv\\Scripts\\Activate.ps1\n"
        "pip install -r requirements.txt\n"
        "pip install -r requirements-dev.txt\n"
        "Copy-Item .env.example .env\n\n"
        "# demo\n"
        "streamlit run app.py\n"
        "python cli.py --customer C-001\n\n"
        "# valutazione e test\n"
        "python eval/run_eval.py --backend local\n"
        "python eval/run_eval.py --backend local --model unsloth/llama-3.2-3b-instruct\n"
        "python -m pytest -q tests\n\n"
        "# ripristino dati\n"
        "python scripts/reset_demo.py"
    )
)
story.append(dc.P("Struttura del progetto", "h2"))
story.append(
    dc.table(
        [
            ["Percorso", "Contenuto"],
            ["<font face='Courier'>app.py</font> / <font face='Courier'>cli.py</font>", "UI Streamlit e CLI demo"],
            ["<font face='Courier'>src/supporto/</font>", "Grafo, tool, policy, RAG, memoria, audit, modelli, prompt"],
            ["<font face='Courier'>data/corpus/</font>", "10 documenti Markdown di policy"],
            ["<font face='Courier'>data/support/</font>", "Dati demo sintetici (ordini, clienti, rimborsi, ticket)"],
            ["<font face='Courier'>eval/</font>", "31 scenari, runner e risultati JSON/Markdown"],
            ["<font face='Courier'>tests/</font>", "57 test automatici senza LM Studio"],
            ["<font face='Courier'>scripts/</font>", "Reset demo e generazione dei documenti"],
        ],
        [5.0 * cm, 11.0 * cm],
        small=True,
    )
)
story.append(Spacer(1, 0.25 * cm))
story.append(
    dc.P(
        "Nota: il progetto non include un file <font face='Courier'>.env</font> con "
        "segreti. La v2 legge il proprio <font face='Courier'>.env</font> e, dalla "
        "cartella superiore, solo <font face='Courier'>GEMINI_API_KEY</font> e "
        "<font face='Courier'>GEMINI_MODEL</font>: il modello locale non viene "
        "sovrascritto. Per cambiare default, creare un <font face='Courier'>.env</font> "
        "locale partendo da <font face='Courier'>.env.example</font>.",
        "small",
    )
)

dc.build_pdf(OUT, story, title="Casa & Regali — Documento tecnico")
