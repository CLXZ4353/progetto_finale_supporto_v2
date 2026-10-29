# -*- coding: utf-8 -*-
"""Modello di chat: LM Studio locale o Gemini via API."""
from __future__ import annotations

import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .config import Settings, get_settings

# BF16 non usato; il Llama 3B meta-llama è sostituito da unsloth.
HIDDEN_MODEL_MARKERS = ("bf16", "meta-llama/llama-3.2-3b")


def is_model_visible(model_id: str) -> bool:
    """True se il modello può comparire nel selettore della UI."""
    return not any(marker in str(model_id).lower() for marker in HIDDEN_MODEL_MARKERS)


def is_lfm3(model_id: str) -> bool:
    """True per LFM3, l'unico modello con reasoning controllabile qui."""
    return "lfm3" in str(model_id).lower()


def dedupe_models(models: list[str], *, preferred: str | None = None) -> list[str]:
    """Un alias per modello; `preferred` sostituisce quello esposto."""
    options: dict[str, str] = {}
    for model in models:
        if is_model_visible(model):
            options.setdefault(str(model).split("@", 1)[0].lower(), str(model))
    if preferred and is_model_visible(preferred):
        family = str(preferred).split("@", 1)[0].lower()
        if family in options:
            options[family] = str(preferred)
        else:
            options = {family: str(preferred), **options}
    return list(options.values())


def final_reasoning_effort(settings: Settings) -> str | None:
    """Reasoning della risposta finale: spento solo con LFM3 locale."""
    if settings.model_backend == "local" and is_lfm3(settings.lm_studio_model):
        return "none"
    return None


def get_chat_model(settings: Settings | None = None, *, reasoning_effort: str | None = None):
    """Crea il modello; `reasoning_effort` vale solo per questa istanza."""
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

    effort = (
        settings.lm_studio_reasoning_effort
        if reasoning_effort is None
        else reasoning_effort
    )
    kwargs = {
        "model": settings.lm_studio_model,
        "api_key": "lm-studio",
        "base_url": settings.lm_studio_base_url,
        "temperature": 0,
        "timeout": 120,
        "max_retries": 1,
    }
    if effort:
        kwargs["extra_body"] = {"reasoning_effort": effort}
    return ChatOpenAI(**kwargs)


def list_local_models(settings: Settings | None = None, timeout: float = 2.0) -> list[str]:
    """Elenca i modelli LLM di LM Studio, con i caricati in cima."""
    settings = settings or get_settings()
    base = settings.lm_studio_base_url.rstrip("/")
    root = base[:-3] if base.endswith("/v1") else base
    for url, detailed in ((f"{root}/api/v0/models", True), (f"{base}/models", False)):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            items = response.json().get("data", [])
            if detailed:
                items = [
                    item
                    for item in items
                    if item.get("id") and str(item.get("type", "llm")).lower() == "llm"
                ]
                items.sort(
                    key=lambda item: (
                        str(item.get("state", "")) != "loaded",
                        str(item["id"]),
                    )
                )
            else:
                items = [item for item in items if item.get("id")]
                items.sort(key=lambda item: str(item["id"]))
            return [
                str(item["id"])
                for item in items
                if item.get("id") and is_model_visible(str(item["id"]))
            ]
        except Exception:  # noqa: BLE001 - il server locale può essere spento
            continue
    return []
