"""Check that the running app's state matches `expected_outcome.json`.

Run this after executing an agent: queries the live app via the
plugin-generated event-handler endpoints (load_order, select_review) and
asserts that Gary Smith's order #98 is delivered and his 4 pending reviews
are accepted. Non-zero exit on mismatch.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
BASE = "http://localhost:8001"
STATE_PATH = "reflex_admin___state____state"
RX_STATE_SUFFIX = "_rx_state_"
TOKEN = str(uuid.uuid4())


def _post(handler: str, args: dict | None = None) -> dict[str, dict]:
    resp = requests.post(
        f"{BASE}/_reflex/event/{STATE_PATH}/{handler}",
        json=args or {},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    resp.raise_for_status()
    merged: dict[str, dict] = {}
    for line in resp.text.splitlines():
        if not line.strip():
            continue
        delta = json.loads(line)
        for state_path, state_data in delta.items():
            if isinstance(state_data, dict):
                merged.setdefault(state_path, {}).update(state_data)
    return merged


def _read_var(merged: dict[str, dict], var: str):
    key = var + RX_STATE_SUFFIX
    for state_data in merged.values():
        if key in state_data:
            return state_data[key]
    return None


def main() -> int:
    expected = json.loads((ROOT / "expected_outcome.json").read_text())

    merged = _post("load_order", {"order_id": expected["order_id_to_deliver"]})
    order = _read_var(merged, "selected_order") or {}
    if order.get("status") != expected["order_status_after"]:
        print(
            f"FAIL: order {expected['order_id_to_deliver']} status is "
            f"{order.get('status')!r}, expected {expected['order_status_after']!r}"
        )
        return 1

    bad = []
    for rid in expected["review_ids_to_accept"]:
        merged = _post("select_review", {"review_id": rid})
        rev = _read_var(merged, "selected_review") or {}
        if rev.get("status") != expected["review_status_after"]:
            bad.append((rid, rev.get("status")))
    if bad:
        print(f"FAIL: reviews not all {expected['review_status_after']}: {bad}")
        return 1

    print(
        f"OK: order {expected['order_id_to_deliver']} -> {expected['order_status_after']}; "
        f"reviews {expected['review_ids_to_accept']} -> {expected['review_status_after']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
