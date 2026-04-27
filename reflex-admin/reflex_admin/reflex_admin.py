"""Reflex app entrypoint.

`rxe.EventHandlerAPIPlugin` (see `rxconfig.py`) auto-generates an HTTP
endpoint for every event handler on `State`. There are no API-specific
handlers — the same `State` methods that drive the UI back the API.
"""

from __future__ import annotations

import reflex as rx
import reflex_enterprise as rxe

from .pages import (
    customer_detail_page,
    customers_page,
    order_detail_page,
    orders_page,
    reviews_page,
)
from .state import State


def index() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Posters Galore Administration", size="7"),
            rx.text("Pick a section:"),
            rx.hstack(
                rx.link(rx.button("Customers"), href="/customers"),
                rx.link(rx.button("Orders"), href="/orders"),
                rx.link(rx.button("Reviews"), href="/reviews"),
            ),
        ),
        height="100vh",
    )


app = rxe.App()

app.add_page(index, route="/", title="Posters Galore")
app.add_page(customers_page, route="/customers", title="Customers")
app.add_page(
    customer_detail_page,
    route="/customers/[customer_id]",
    title="Customer",
    on_load=State.load_customer_from_route,
)
app.add_page(orders_page, route="/orders", title="Orders")
app.add_page(
    order_detail_page,
    route="/orders/[order_id]",
    title="Order",
    on_load=State.load_order_from_route,
)
app.add_page(reviews_page, route="/reviews", title="Reviews")
