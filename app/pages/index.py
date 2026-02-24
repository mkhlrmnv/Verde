from __future__ import annotations

import reflex as rx

from app.components.top_nav import top_nav
from app.components.upload_panel import upload_panel
from app.state import AppState


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            top_nav(),
            rx.heading("Applicant Profile Builder", size="8"),
            upload_panel(),
            rx.cond(
                AppState.error_message != "",
                rx.callout(AppState.error_message, icon="triangle_alert", color_scheme="red"),
            ),
            rx.cond(
                AppState.success_message != "",
                rx.callout(AppState.success_message, icon="circle_check", color_scheme="green"),
            ),
            rx.hstack(
                rx.link(rx.button("Go to profile", variant="solid"), href="/profile"),
                justify="center",
                width="100%",
            ),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        max_width="980px",
        padding_y="5",
    )
