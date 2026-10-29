# -*- coding: utf-8 -*-
"""Configurazione del progetto v2.

Legge il `.env` del progetto e, come fallback, quello della cartella
superiore (`llm_lab/.env`), così la chiave Gemini già presente non va
duplicata.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
# Dal `.env` superiore prendiamo solo le credenziali Gemini: non deve
# sovrascrivere modello, backend o altri parametri runtime della v2.
_parent_env = dotenv_values(ROOT.parent / ".env")
for _key in ("GEMINI_API_KEY", "GEMINI_MODEL"):
    _value = _parent_env.get(_key)
    if _value and not os.environ.get(_key):
        os.environ[_key] = _value

DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
SUPPORT_DIR = DATA_DIR / "support"
LOGS_DIR = ROOT / "logs"
EVAL_DIR = ROOT / "eval"
DOCS_DIR = ROOT / "docs"

ORDERS_PATH = SUPPORT_DIR / "orders.json"
CUSTOMERS_PATH = SUPPORT_DIR / "customers.json"
PRODUCTS_PATH = SUPPORT_DIR / "products.json"
REFUNDS_PATH = SUPPORT_DIR / "refunds.json"
TICKETS_PATH = SUPPORT_DIR / "tickets.json"
PREFERENCES_PATH = SUPPORT_DIR / "preferences.json"
AUDIT_PATH = LOGS_DIR / "audit.jsonl"


@dataclass(slots=True)
class Settings:
    """Parametri runtime. I percorsi restano costanti del modulo."""

    model_backend: str = "local"          # local | gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_model: str = "lfm3-1.7b@q4_k_m"
    # Solo per modelli che supportano il controllo del reasoning (es. LFM3):
    # "none" disattiva, vuoto lascia il default del modello.
    lm_studio_reasoning_effort: str = ""
    demo_today: date = field(default_factory=lambda: date(2026, 10, 23))
    top_k: int = 3
    chunk_size: int = 650
    chunk_overlap: int = 50

    @classmethod
    def from_env(cls) -> "Settings":
        raw_today = os.environ.get("DEMO_TODAY", "2026-10-23").strip()
        try:
            today = date.fromisoformat(raw_today)
        except ValueError:
            today = date(2026, 10, 23)
        return cls(
            model_backend=os.environ.get("MODEL_BACKEND", "local").strip().lower(),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            lm_studio_base_url=os.environ.get(
                "LM_STUDIO_BASE_URL", "http://localhost:1234/v1"
            ).strip(),
            lm_studio_model=os.environ.get(
                "LM_STUDIO_MODEL", "lfm3-1.7b@q4_k_m"
            ).strip(),
            lm_studio_reasoning_effort=os.environ.get(
                "LM_STUDIO_REASONING_EFFORT", ""
            ).strip(),
            demo_today=today,
            top_k=int(os.environ.get("TOP_K", "3")),
            chunk_size=int(os.environ.get("CHUNK_SIZE", "650")),
            chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", "50")),
        )

    @property
    def model_label(self) -> str:
        if self.model_backend == "gemini":
            return f"Gemini ({self.gemini_model})"
        return f"Locale ({self.lm_studio_model})"


def get_settings() -> Settings:
    """Rilegge l'ambiente a ogni chiamata: la UI può cambiare backend."""
    return Settings.from_env()
