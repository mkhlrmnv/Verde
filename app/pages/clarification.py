from __future__ import annotations

import reflex as rx

from app.components.clarification_form import clarification_form
from app.components.top_nav import top_nav
from app.state import AppState


def clarification_content() -> rx.Component:
    return rx.box(
        clarification_form(),
        width="100%",
        max_width="56rem",
        margin_x="auto",
        padding_x="1rem",
    )


def clarification() -> rx.Component:
    return rx.cond(
        AppState.is_clarification_step,
        rx.box(
            rx.vstack(
                top_nav(),
                rx.box(
                    rx.vstack(
                        rx.cond(
                            AppState.error_message != "",
                            rx.callout(AppState.error_message, icon="triangle_alert", color_scheme="red"),
                        ),
                        rx.cond(
                            AppState.success_message != "",
                            rx.callout(AppState.success_message, icon="circle_check", color_scheme="green"),
                        ),
                        clarification_content(),
                        spacing="4",
                        width="100%",
                        align_items="stretch",
                    ),
                    width="100%",
                    max_width="72rem",
                    margin_x="auto",
                    padding_top="2rem",
                    padding_x="1rem",
                ),
                width="100%",
                align_items="stretch",
                spacing="0",
            ),
            width="100%",
            min_height="100vh",
            background_color="#f5f5f5",
            color="#111827",
        ),
        rx.box(
            rx.script("window.location.replace('/');"),
            width="100%",
            min_height="1px",
        ),
    )
