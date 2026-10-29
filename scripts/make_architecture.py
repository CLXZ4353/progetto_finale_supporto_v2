# -*- coding: utf-8 -*-
"""Genera il diagramma dell'architettura v2."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architettura.png"
OUT.parent.mkdir(exist_ok=True)

BROWN = "#6b4429"
GREEN = "#4f6b4d"
RED = "#8a4b3f"
INK = "#2f241c"
MUTED = "#5b4a3e"

fig, ax = plt.subplots(figsize=(12, 6.6))
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.6)
ax.axis("off")


def box(x, y, w, h, text, color="#f3e9df", edge=BROWN, fontsize=10, bold=False):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            linewidth=1.3,
            edgecolor=edge,
            facecolor=color,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        fontweight="bold" if bold else "normal",
        wrap=True,
    )


def arrow(x1, y1, x2, y2, color=BROWN, lw=1.3, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


# Flusso principale
box(0.2, 4.75, 1.7, 0.95, "Cliente\nStreamlit / CLI", "#e8f0e7", GREEN, bold=True)
box(2.35, 4.75, 1.9, 0.95, "agent\nl'LLM sceglie\nun tool", "#f3e9df", bold=True)
box(4.65, 4.75, 1.9, 0.95, "tools\n7 tool\npolicy-as-code", "#f7f1ea", bold=True)
box(6.95, 4.75, 1.9, 0.95, "respond\nl'LLM scrive\nsenza tool", "#eef1f6", "#4d5b73", bold=True)
box(9.25, 4.75, 2.05, 0.95, "finalize\nrisposta + fonti\n+ audit", "#e8f0e7", GREEN, bold=True)

arrow(1.9, 5.22, 2.3, 5.22)
arrow(4.25, 5.22, 4.6, 5.22)
arrow(6.55, 5.22, 6.9, 5.22)
arrow(8.85, 5.22, 9.2, 5.22)

# Percorso senza tool
arrow(4.25, 5.45, 9.2, 5.75, color="#8a7a66", lw=1.1, rad=-0.12)
ax.text(6.7, 6.02, "nessun tool: risposta diretta", ha="center", fontsize=9, color=MUTED, style="italic")

# Sorgenti dei tool
box(2.35, 3.15, 1.9, 0.7, "policy.py\nregole e soglie", "#f7f1ea", fontsize=9)
box(4.65, 3.15, 1.9, 0.7, "JSON demo DB\nordini e clienti", "#f7f1ea", fontsize=9)
box(6.95, 3.15, 1.9, 0.7, "corpus + BM25\n10 documenti", "#f7f1ea", fontsize=9)
box(9.25, 3.15, 2.05, 0.7, "memoria\npreferenze", "#f7f1ea", fontsize=9)

for x in (3.3, 5.6, 7.9):
    arrow(x, 4.72, x, 3.88, color="#8a7a66", lw=1.0)
arrow(9.8, 3.88, 9.8, 4.72, color="#8a7a66", lw=1.0)

# HITL e ledger: il percorso parte dal tool e aggira la riga delle sorgenti
box(7.15, 1.75, 2.1, 0.75, "HITL rimborso\ninterrupt / resume", "#f6e7e4", RED, fontsize=9, bold=True)
box(9.5, 1.75, 2.1, 0.8, "Ledger idempotente\n+ audit JSONL", "#e8f0e7", GREEN, fontsize=9, bold=True)
ax.plot([6.3, 6.3, 8.2], [4.72, 4.05, 4.05], color=RED, lw=1.3, solid_capstyle="round")
arrow(8.2, 4.05, 8.2, 2.53, color=RED, lw=1.3)
arrow(9.28, 2.12, 9.47, 2.12, color=RED, lw=1.3)
arrow(10.55, 2.56, 10.55, 4.72, color=GREEN, lw=1.1, rad=0.0)

# Nota
box(
    0.2,
    0.35,
    11.1,
    0.75,
    "L'LLM sceglie il tool e scrive la risposta; il codice impone policy, privacy, HITL e ledger. "
    "Nessun fallback deterministico.",
    "#f3efe9",
    "#8a7a66",
    fontsize=9.5,
)

ax.text(0.2, 6.38, "Casa & Regali — architettura v2", fontsize=15, fontweight="bold", color="#3b2b20")
ax.text(
    0.2,
    6.1,
    "Un solo agente, un solo passaggio di tool, un secondo passo LLM per la risposta.",
    fontsize=9.5,
    color=MUTED,
)

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Scritto {OUT}")
