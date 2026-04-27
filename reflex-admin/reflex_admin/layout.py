from __future__ import annotations

import reflex as rx


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.heading("Posters Galore", size="5", margin_bottom="1rem"),
        rx.link("Customers", href="/customers", padding="0.5rem 0", id="nav-customers"),
        rx.link("Orders", href="/orders", padding="0.5rem 0", id="nav-orders"),
        rx.link("Reviews", href="/reviews", padding="0.5rem 0", id="nav-reviews"),
        padding="1.5rem",
        width="200px",
        height="100vh",
        background="#f5f5f5",
        border_right="1px solid #ddd",
        align_items="stretch",
    )


def page(*children: rx.Component, title: str = "") -> rx.Component:
    body = rx.vstack(
        rx.heading(title, size="7", margin_bottom="1rem"),
        *children,
        padding="2rem",
        width="100%",
        align_items="stretch",
    )
    return rx.hstack(sidebar(), body, align_items="stretch", width="100%")
