"""Shared in-memory datastore loaded from seed.json.

The Reflex UI and the plugin-generated API endpoints read/write the same
dicts, so a state mutation through the API shows up in the UI on next
navigation and vice-versa.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

_HERE = Path(__file__).resolve()
# Prefer the benchmark root's seed.json (one source of truth across the repo);
# fall back to a local copy in the reflex-admin/ folder for standalone runs.
_CANDIDATES = [
    _HERE.parent.parent.parent / "seed.json",  # benchmark root
    _HERE.parent.parent / "seed.json",         # reflex-admin/
]
SEED_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

_lock = RLock()
with SEED_PATH.open() as _f:
    _db: dict[str, list[dict[str, Any]]] = json.load(_f)


def customers() -> list[dict[str, Any]]:
    return _db["customers"]


def orders() -> list[dict[str, Any]]:
    return _db["orders"]


def reviews() -> list[dict[str, Any]]:
    return _db["reviews"]


def products() -> list[dict[str, Any]]:
    return _db["products"]


def find_customer(customer_id: int) -> dict[str, Any] | None:
    for c in _db["customers"]:
        if c["id"] == customer_id:
            return c
    return None


def find_order(order_id: int) -> dict[str, Any] | None:
    for o in _db["orders"]:
        if o["id"] == order_id:
            return o
    return None


def find_review(review_id: int) -> dict[str, Any] | None:
    for r in _db["reviews"]:
        if r["id"] == review_id:
            return r
    return None


def update_order(order_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    with _lock:
        o = find_order(order_id)
        if o is None:
            return None
        o.update(patch)
        return o


def update_review(review_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    with _lock:
        r = find_review(review_id)
        if r is None:
            return None
        r.update(patch)
        return r


def customer_display_name(customer_id: int) -> str:
    c = find_customer(customer_id)
    if c is None:
        return f"#{customer_id}"
    return f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
