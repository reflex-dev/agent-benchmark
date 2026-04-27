"""Reflex state — event handlers drive the UI and mutate the shared datastore.

Every event handler defined here is also exposed as an HTTP endpoint by
`rxe.EventHandlerAPIPlugin` (configured in `rxconfig.py`) at
`POST /_reflex/event/<state_path>/<handler>`. Computed vars stream back in
the response deltas, so reads happen by triggering a setter handler and
parsing the resulting computed-var delta.

Computed vars read from a module-level dict (`data._db`). Reflex's
ComputedVar dependency tracking can't see mutations to that dict, so every
mutating handler bumps `data_rev`, and every computed var touches `data_rev`
to register it as a dependency. Without this, Accept-review clicks appear to
succeed but the list never refreshes.
"""

from __future__ import annotations

from typing import Any

import reflex as rx

from . import data


class State(rx.State):
    # Monotonic counter bumped on every data mutation. Computed vars read it
    # so Reflex invalidates them when the underlying dict changes.
    data_rev: int = 0

    def _touch(self):
        self.data_rev = self.data_rev + 1

    # ---- Customers page ----
    customers_query: str = ""

    @rx.var
    def customer_rows(self) -> list[dict[str, Any]]:
        _ = self.data_rev
        q = self.customers_query.lower().strip()
        rows = list(data.customers())
        if q:
            rows = [
                c for c in rows
                if q in (c.get("last_name") or "").lower()
                or q in (c.get("first_name") or "").lower()
            ]
        rows = sorted(rows, key=lambda c: c.get("nb_orders") or 0, reverse=True)
        return [
            {
                "id": c["id"],
                "first_name": c.get("first_name") or "",
                "last_name": c.get("last_name") or "",
                "email": c.get("email") or "",
                "nb_orders": c.get("nb_orders") or 0,
                "total_spent": c.get("total_spent") or 0,
            }
            for c in rows[:100]
        ]

    def set_customers_query(self, q: str):
        self.customers_query = q

    # ---- Orders page ----
    orders_tab: str = "ordered"
    orders_query: str = ""

    @rx.var
    def order_rows(self) -> list[dict[str, Any]]:
        _ = self.data_rev
        q = self.orders_query.lower().strip()
        rows = [o for o in data.orders() if o["status"] == self.orders_tab]
        if q:
            keep = []
            for o in rows:
                name = data.customer_display_name(o["customer_id"]).lower()
                ref = (o.get("reference") or "").lower()
                if q in name or q in ref:
                    keep.append(o)
            rows = keep
        rows = sorted(rows, key=lambda o: o.get("date") or "", reverse=True)
        return [
            {
                "id": o["id"],
                "reference": o.get("reference") or "",
                "date": (o.get("date") or "")[:10],
                "customer_id": o["customer_id"],
                "customer_name": data.customer_display_name(o["customer_id"]),
                "total": o.get("total") or 0,
                "status": o.get("status") or "",
            }
            for o in rows[:200]
        ]

    @rx.var
    def count_ordered(self) -> int:
        _ = self.data_rev
        return sum(1 for o in data.orders() if o["status"] == "ordered")

    @rx.var
    def count_delivered(self) -> int:
        _ = self.data_rev
        return sum(1 for o in data.orders() if o["status"] == "delivered")

    @rx.var
    def count_cancelled(self) -> int:
        _ = self.data_rev
        return sum(1 for o in data.orders() if o["status"] == "cancelled")

    def set_orders_tab(self, tab: str):
        self.orders_tab = tab

    def set_orders_query(self, q: str):
        self.orders_query = q

    # ---- Order detail ----
    selected_order_id: int = -1
    order_status_draft: str = ""
    order_save_message: str = ""

    @rx.var
    def selected_order(self) -> dict[str, Any]:
        _ = self.data_rev
        o = data.find_order(self.selected_order_id)
        if o is None:
            return {}
        return {
            "id": o["id"],
            "reference": o.get("reference") or "",
            "date": o.get("date") or "",
            "customer_id": o["customer_id"],
            "customer_name": data.customer_display_name(o["customer_id"]),
            "total": o.get("total") or 0,
            "status": o.get("status") or "",
            "items": len(o.get("basket") or []),
        }

    def load_order(self, order_id: int):
        self.selected_order_id = int(order_id)
        o = data.find_order(self.selected_order_id)
        self.order_status_draft = (o or {}).get("status") or ""
        self.order_save_message = ""

    def load_order_from_route(self):
        # on_load handlers can't take dynamic args directly; read from
        # self.router.page.params, which Reflex populates from the URL.
        raw = self.router.page.params.get("order_id", "")
        try:
            oid = int(raw)
        except (TypeError, ValueError):
            return
        self.load_order(oid)

    def set_order_status_draft(self, status: str):
        self.order_status_draft = status

    def save_order_status(self):
        if self.selected_order_id < 0 or not self.order_status_draft:
            return
        data.update_order(self.selected_order_id, {"status": self.order_status_draft})
        self._touch()
        self.order_save_message = "Order updated"

    # ---- Reviews page ----
    reviews_status_filter: str = "pending"
    selected_review_id: int = -1
    review_action_message: str = ""

    @rx.var
    def review_rows(self) -> list[dict[str, Any]]:
        _ = self.data_rev
        rows = list(data.reviews())
        if self.reviews_status_filter:
            rows = [r for r in rows if r["status"] == self.reviews_status_filter]
        rows = sorted(rows, key=lambda r: r.get("date") or "", reverse=True)
        return [
            {
                "id": r["id"],
                "date": (r.get("date") or "")[:10],
                "customer_id": r["customer_id"],
                "customer_name": data.customer_display_name(r["customer_id"]),
                "product_id": r["product_id"],
                "rating": r.get("rating") or 0,
                "status": r.get("status") or "",
                "comment_preview": (r.get("comment") or "")[:80],
            }
            for r in rows[:300]
        ]

    @rx.var
    def selected_review(self) -> dict[str, Any]:
        _ = self.data_rev
        r = data.find_review(self.selected_review_id)
        if r is None:
            return {}
        return {
            "id": r["id"],
            "date": r.get("date") or "",
            "customer_id": r["customer_id"],
            "customer_name": data.customer_display_name(r["customer_id"]),
            "product_id": r["product_id"],
            "rating": r.get("rating") or 0,
            "status": r.get("status") or "",
            "comment": r.get("comment") or "",
        }

    def set_reviews_status_filter(self, status: str):
        self.reviews_status_filter = status
        self.selected_review_id = -1
        self.review_action_message = ""

    def select_review(self, review_id: int):
        self.selected_review_id = int(review_id)
        self.review_action_message = ""

    def accept_review(self):
        if self.selected_review_id < 0:
            return
        data.update_review(self.selected_review_id, {"status": "accepted"})
        self._touch()
        self.review_action_message = "Review accepted"
        self.selected_review_id = -1

    def reject_review(self):
        if self.selected_review_id < 0:
            return
        data.update_review(self.selected_review_id, {"status": "rejected"})
        self._touch()
        self.review_action_message = "Review rejected"
        self.selected_review_id = -1

    # ---- Customer detail ----
    selected_customer_id: int = -1

    @rx.var
    def selected_customer(self) -> dict[str, Any]:
        _ = self.data_rev
        c = data.find_customer(self.selected_customer_id)
        if c is None:
            return {}
        return {
            "id": c["id"],
            "first_name": c.get("first_name") or "",
            "last_name": c.get("last_name") or "",
            "email": c.get("email") or "",
            "nb_orders": c.get("nb_orders") or 0,
            "total_spent": c.get("total_spent") or 0,
        }

    @rx.var
    def selected_customer_orders(self) -> list[dict[str, Any]]:
        _ = self.data_rev
        if self.selected_customer_id < 0:
            return []
        rows = [o for o in data.orders() if o["customer_id"] == self.selected_customer_id]
        rows = sorted(rows, key=lambda o: o.get("date") or "", reverse=True)
        return [
            {
                "id": o["id"],
                "reference": o.get("reference") or "",
                "date": (o.get("date") or "")[:10],
                "total": o.get("total") or 0,
                "status": o.get("status") or "",
            }
            for o in rows
        ]

    def load_customer(self, customer_id: int):
        self.selected_customer_id = int(customer_id)

    def load_customer_from_route(self):
        raw = self.router.page.params.get("customer_id", "")
        try:
            cid = int(raw)
        except (TypeError, ValueError):
            return
        self.load_customer(cid)
