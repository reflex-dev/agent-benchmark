from __future__ import annotations

import reflex as rx

from ..layout import page
from ..state import State


def _row(row) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(row["last_name"], href="/customers/" + row["id"].to_string()),
        ),
        rx.table.cell(row["first_name"]),
        rx.table.cell(row["email"]),
        rx.table.cell(
            row["nb_orders"].to_string(),
            custom_attrs={"data-testid": "nb-orders"},
        ),
        rx.table.cell("$", row["total_spent"].to_string()),
    )


def customers_page() -> rx.Component:
    return page(
        rx.input(
            placeholder="Search last name",
            on_change=State.set_customers_query,
            value=State.customers_query,
            id="customers-search",
            width="300px",
            margin_bottom="1rem",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Last name"),
                    rx.table.column_header_cell("First name"),
                    rx.table.column_header_cell("Email"),
                    rx.table.column_header_cell("Orders"),
                    rx.table.column_header_cell("Total spent"),
                )
            ),
            rx.table.body(rx.foreach(State.customer_rows, _row)),
            width="100%",
        ),
        title="Customers",
    )


def _customer_order_row(o) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(o["reference"], href="/orders/" + o["id"].to_string())
        ),
        rx.table.cell(o["date"]),
        rx.table.cell("$", o["total"].to_string()),
        rx.table.cell(o["status"]),
    )


def customer_detail_page() -> rx.Component:
    return page(
        rx.cond(
            State.selected_customer_id >= 0,
            rx.vstack(
                rx.heading(
                    State.selected_customer["first_name"],
                    " ",
                    State.selected_customer["last_name"],
                    size="6",
                ),
                rx.text("Customer ID: ", rx.code(State.selected_customer["id"].to_string())),
                rx.text("Email: ", State.selected_customer["email"]),
                rx.text("Orders: ", State.selected_customer["nb_orders"].to_string()),
                rx.text("Total spent: $", State.selected_customer["total_spent"].to_string()),
                rx.heading("Orders", size="4", margin_top="1.5rem"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Reference"),
                            rx.table.column_header_cell("Date"),
                            rx.table.column_header_cell("Total"),
                            rx.table.column_header_cell("Status"),
                        )
                    ),
                    rx.table.body(rx.foreach(State.selected_customer_orders, _customer_order_row)),
                    width="100%",
                ),
                align_items="stretch",
                width="100%",
            ),
            rx.text("Loading customer..."),
        ),
        title="Customer",
    )
