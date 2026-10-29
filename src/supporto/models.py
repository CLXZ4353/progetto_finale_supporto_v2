# -*- coding: utf-8 -*-
"""Modello di chat: locale via LM Studio o Gemini via API.

Il resto del progetto usa solo `get_chat_model()`: cambiare backend non
richiede modifiche ai tool o al grafo.
"""
from __future__ import annotations

import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .config import Settings, get_settings

# Modelli esclusi dal selettore della UI: BF16 non usato; il Llama 3B
# meta-llama è sostituito da unsloth/llama-3.2-3b-instruct.
HIDDEN_MODEL_MARKERS = ("bf16", "meta-llama/llama-3.2-3b")


def is_model_visible(model_id: str) -> bool:
    """True se il modello può comparire nel selettore della UI."""
    return not any(marker in str(model_id).lower() for marker in HIDDEN_MODEL_MARKERS)


def is_lfm3(model_id: str) -> bool:
    """True se il modello è LFM3, l'unico con reasoning controllabile qui."""
    return "lfm3" in str(model_id).lower()


def _model_family(model_id: str) -> str:
    """Nome del modello senza alias di quantizzazione (es. `@q4_k_m`)."""
    return str(model_id).strip().split("@", 1)[0].lower()


def dedupe_models(models: list[str], *, preferred: str | None = None) -> list[str]:
    """Unisce gli alias dello stesso modello e mette `preferred` al suo posto.

    LM Studio può esporre lo stesso modello sia con l'alias di quantizzazione
    sia con il nome canonico: nel selettore deve comparire una volta sola.
    """
    options: list[str] = []
    for model in models:
        model = str(model)
        if not is_model_visible(model):
            continue
        family = _model_family(model)
        if any(_model_family(kept) == family for kept in options):
            continue
        options.append(model)
    if preferred and is_model_visible(preferred):
        family = _model_family(preferred)
        for index, model in enumerate(options):
            if _model_family(model) == family:
                options[index] = str(preferred)
                break
        else:
            options.insert(0, str(preferred))
    return options


def final_reasoning_effort(settings: Settings) -> str | None:
    """Reasoning da usare nella risposta finale; None lascia il default."""
    if settings.model_backend == "local" and is_lfm3(settings.lm_studio_model):
        return "none"
    return None


def get_chat_model(settings: Settings | None = None, *, reasoning_effort: str | None = None):
    """Crea il modello di chat.

    `reasoning_effort` permette di forzare il reasoning solo per una chiamata:
    la risposta finale LFM3 lo disattiva, la scelta dei tool usa il default.
    """
    settings = settings or get_settings()
    if settings.model_backend == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY non impostata. Inseriscila nel .env o usa MODEL_BACKEND=local."
            )
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.gemini_api_key,
            temperature=0,
            request_timeout=60,
            retries=0,
        )

    kwargs = {
        "model": settings.lm_studio_model,
        "api_key": "lm-studio",
        "base_url": settings.lm_studio_base_url,
        "temperature": 0,
        "timeout": 120,
        "max_retries": 1,
    }
    effort = (
        settings.lm_studio_reasoning_effort
        if reasoning_effort is None
        else reasoning_effort
    )
    if effort:
        kwargs["extra_body"] = {"reasoning_effort": effort}
    return ChatOpenAI(**kwargs)


def list_local_models(settings: Settings | None = None, timeout: float = 2.0) -> list[str]:
    """Elenca i modelli LLM di LM Studio, con i caricati in cima."""
    settings = settings or get_settings()
    base = settings.lm_studio_base_url.rstrip("/")
    root = base[:-3] if base.endswith("/v1") else base
    try:
        response = requests.get(f"{root}/api/v0/models", timeout=timeout)
        response.raise_for_status()
        items = response.json().get("data", [])
        llms = [
            item
            for item in items
            if item.get("id") and str(item.get("type", "llm")).lower() == "llm"
        ]
        llms.sort(key=lambda item: (str(item.get("state", "")) != "loaded", str(item["id"])))
        return [
            str(item["id"])
            for item in llms
            if is_model_visible(str(item["id"]))
        ]
    except Exception:  # noqa: BLE001 - il server locale può essere spento
        pass
    try:
        response = requests.get(f"{base}/models", timeout=timeout)
        response.raise_for_status()
        items = response.json().get("data", [])
        return sorted(
            str(item["id"])
            for item in items
            if item.get("id") and is_model_visible(str(item["id"]))
        )
    except Exception:  # noqa: BLE001
        return []
