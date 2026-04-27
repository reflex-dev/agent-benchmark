from __future__ import annotations

import reflex as rx

from ..layout import page
from ..state import State


def _row(row) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.button(
                "View",
                on_click=State.select_review(row["id"]),
                size="1",
                variant="soft",
                id="view-review-" + row["id"].to_string(),
            )
        ),
        rx.table.cell(row["date"]),
        rx.table.cell(row["customer_name"]),
        rx.table.cell(row["rating"].to_string()),
        rx.table.cell(row["status"]),
        rx.table.cell(row["comment_preview"]),
    )


def _detail_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("Review #", State.selected_review["id"].to_string(), size="5"),
        rx.text("Customer: ", State.selected_review["customer_name"]),
        rx.text("Rating: ", State.selected_review["rating"].to_string()),
        rx.text("Status: ", State.selected_review["status"]),
        rx.text_area(
            value=State.selected_review["comment"],
            read_only=True,
            rows="6",
            width="100%",
        ),
        rx.hstack(
            rx.button("Accept", on_click=State.accept_review, id="review-accept"),
            rx.button(
                "Reject",
                on_click=State.reject_review,
                id="review-reject",
                color_scheme="red",
                variant="soft",
            ),
            margin_top="0.5rem",
        ),
        rx.cond(
            State.review_action_message != "",
            rx.box(
                State.review_action_message,
                id="review-action-message",
                padding="0.5rem 1rem",
                margin_top="0.5rem",
                background="#e6ffed",
                border="1px solid #34a853",
                border_radius="4px",
            ),
        ),
        align_items="flex-start",
        width="360px",
        padding="1rem",
        background="#fafafa",
        border="1px solid #ddd",
        border_radius="6px",
    )


def reviews_page() -> rx.Component:
    return page(
        rx.hstack(
            rx.text("Status filter:"),
            rx.select(
                ["pending", "accepted", "rejected"],
                value=State.reviews_status_filter,
                on_change=State.set_reviews_status_filter,
                id="reviews-filter",
            ),
            margin_bottom="1rem",
            align_items="center",
        ),
        rx.hstack(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(""),
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Customer"),
                        rx.table.column_header_cell("Rating"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Comment"),
                    )
                ),
                rx.table.body(rx.foreach(State.review_rows, _row)),
                flex="1",
            ),
            rx.cond(
                State.selected_review_id >= 0,
                _detail_panel(),
                rx.box(width="360px"),
            ),
            align_items="flex-start",
            width="100%",
            gap="1rem",
        ),
        title="Reviews",
    )
