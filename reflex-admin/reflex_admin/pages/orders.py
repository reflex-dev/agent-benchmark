from __future__ import annotations

import reflex as rx

from ..layout import page
from ..state import State


def _tab_button(label: str, value: str, count) -> rx.Component:
    is_active = State.orders_tab == value
    return rx.button(
        label,
        " (",
        count.to_string(),
        ")",
        on_click=State.set_orders_tab(value),
        variant=rx.cond(is_active, "solid", "soft"),
        id="tab-" + value,
    )


def _row(row) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(row["reference"], href="/orders/" + row["id"].to_string()),
        ),
        rx.table.cell(row["date"]),
        rx.table.cell(row["customer_name"]),
        rx.table.cell("$", row["total"].to_string()),
        rx.table.cell(row["status"]),
    )


def orders_page() -> rx.Component:
    return page(
        rx.hstack(
            _tab_button("Ordered", "ordered", State.count_ordered),
            _tab_button("Delivered", "delivered", State.count_delivered),
            _tab_button("Cancelled", "cancelled", State.count_cancelled),
            margin_bottom="1rem",
        ),
        rx.input(
            placeholder="Search by customer or reference",
            on_change=State.set_orders_query,
            value=State.orders_query,
            id="orders-search",
            width="400px",
            margin_bottom="1rem",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Reference"),
                    rx.table.column_header_cell("Date"),
                    rx.table.column_header_cell("Customer"),
                    rx.table.column_header_cell("Total"),
                    rx.table.column_header_cell("Status"),
                )
            ),
            rx.table.body(rx.foreach(State.order_rows, _row)),
            width="100%",
        ),
        title="Orders",
    )


def order_detail_page() -> rx.Component:
    return page(
        rx.cond(
            State.selected_order_id >= 0,
            rx.vstack(
                rx.heading("Order ", State.selected_order["reference"], size="6"),
                rx.text("Order ID: ", rx.code(State.selected_order["id"].to_string())),
                rx.text("Customer: ", State.selected_order["customer_name"]),
                rx.text("Date: ", State.selected_order["date"]),
                rx.text("Total: $", State.selected_order["total"].to_string()),
                rx.text("Items: ", State.selected_order["items"].to_string()),
                rx.heading("Status", size="4", margin_top="1.5rem"),
                rx.select(
                    ["ordered", "delivered", "cancelled"],
                    value=State.order_status_draft,
                    on_change=State.set_order_status_draft,
                    id="order-status-select",
                ),
                rx.button(
                    "Save",
                    on_click=State.save_order_status,
                    id="order-save",
                    margin_top="0.5rem",
                ),
                rx.cond(
                    State.order_save_message != "",
                    rx.box(
                        State.order_save_message,
                        id="order-save-message",
                        padding="0.5rem 1rem",
                        margin_top="0.5rem",
                        background="#e6ffed",
                        border="1px solid #34a853",
                        border_radius="4px",
                    ),
                ),
                align_items="flex-start",
                width="100%",
            ),
            rx.text("Loading order..."),
        ),
        title="Order",
    )
