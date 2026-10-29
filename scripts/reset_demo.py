# -*- coding: utf-8 -*-
"""Riporta i dati demo allo stato iniziale."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supporto.config import AUDIT_PATH, LOGS_DIR, PREFERENCES_PATH, SUPPORT_DIR  # noqa: E402
from supporto.support_data import build_support_data  # noqa: E402


def main() -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = build_support_data()
    for name in ("products", "customers", "orders", "refunds", "tickets", "preferences"):
        path = SUPPORT_DIR / f"{name}.json"
        path.write_text(
            json.dumps(data[name], ensure_ascii=False, indent=2), encoding="utf-8"
        )
    PREFERENCES_PATH.write_text("{}", encoding="utf-8")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text("", encoding="utf-8")
    print("demo resettata: ordini, rimborsi, ticket, preferenze e audit.")


if __name__ == "__main__":
    main()
