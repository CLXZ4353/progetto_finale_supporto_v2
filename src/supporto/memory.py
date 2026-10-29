# -*- coding: utf-8 -*-
"""Memoria a lungo termine delle preferenze.

La memoria a breve termine è il checkpointer di LangGraph (stato del thread).
Qui salviamo solo le preferenze che il cliente chiede esplicitamente di
ricordare: niente consenso separato, perché la richiesta stessa è il consenso.
I dati sensibili (email, telefoni, carte) vengono rimossi prima del salvataggio.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PREFERENCES_PATH

MAX_PREFERENCE_CHARS = 200
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def _sanitize(text: str) -> str:
    cleaned = " ".join(str(text).split()).strip()
    cleaned = _EMAIL_RE.sub("[email rimossa]", cleaned)
    cleaned = _PHONE_RE.sub("[telefono rimosso]", cleaned)
    cleaned = _CARD_RE.sub("[numero rimosso]", cleaned)
    return cleaned[:MAX_PREFERENCE_CHARS].rstrip()


class PreferenceMemory:
    """Preferenze per cliente su file JSON, con lock per un solo processo."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or PREFERENCES_PATH)
        self._lock = threading.RLock()
        self._items: dict[str, list[dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        for customer_id, items in data.items():
            if not isinstance(items, list):
                continue
            cleaned = []
            for item in items:
                text = str(item.get("text", "")).strip()
                if text:
                    cleaned.append(
                        {
                            "id": str(item.get("id") or uuid.uuid4().hex),
                            "text": text,
                            "created_at": str(item.get("created_at", "")),
                        }
                    )
            if cleaned:
                self._items[str(customer_id)] = cleaned

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self._items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.path)

    def get_preferences(self, customer_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._items.get(str(customer_id), [])]

    def get_profile(self, customer_id: str) -> str:
        return "; ".join(
            item["text"] for item in self.get_preferences(customer_id) if item.get("text")
        )

    def add(self, customer_id: str, text: str, *, source: str = "richiesta") -> dict[str, Any]:
        cleaned = _sanitize(text)
        if not cleaned or cleaned in {"[email rimossa]", "[telefono rimosso]", "[numero rimosso]"}:
            return {"salvata": False, "motivo": "nessun contenuto utile da ricordare"}
        with self._lock:
            items = self._items.setdefault(str(customer_id), [])
            existing = {item["text"].lower() for item in items}
            if cleaned.lower() in existing:
                return {"salvata": False, "motivo": "preferenza già presente", "testo": cleaned}
            record = {
                "id": uuid.uuid4().hex,
                "text": cleaned,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "source": source,
            }
            items.append(record)
            self._save()
        return {"salvata": True, **record}

    def clear(self, customer_id: str | None = None) -> None:
        with self._lock:
            if customer_id is None:
                self._items.clear()
            else:
                self._items.pop(str(customer_id), None)
            self._save()
