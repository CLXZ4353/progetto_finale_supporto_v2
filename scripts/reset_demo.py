# -*- coding: utf-8 -*-
"""Riporta i dati demo allo stato iniziale."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supporto.config import AUDIT_PATH, LOGS_DIR, SUPPORT_DIR  # noqa: E402
from supporto.support_data import write_support_data  # noqa: E402


def main() -> None:
    write_support_data(SUPPORT_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text("", encoding="utf-8")
    print("demo resettata: ordini, rimborsi, ticket, preferenze e audit.")


if __name__ == "__main__":
    main()
