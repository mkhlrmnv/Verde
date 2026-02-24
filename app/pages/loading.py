from __future__ import annotations

import reflex as rx

from app.state import AppState


def loading() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Processing your profile...", size="8"),
            rx.spinner(size="3"),
            rx.text("We're extracting your documents and generating your profile with AI.", size="5"),
            rx.text("This may take a few moments. Please stay on this page.", size="4"),
            rx.cond(
                AppState.success_message != "",
                rx.vstack(
                    rx.callout(AppState.success_message, icon="circle_check", color_scheme="green"),
                    rx.script("setTimeout(() => window.location = '/profile', 2000)"),
                    spacing="2",
                ),
            ),
            rx.cond(
                AppState.error_message != "",
                rx.vstack(
                    rx.callout(AppState.error_message, icon="triangle_alert", color_scheme="red"),
                    rx.link(rx.button("Go back to upload", variant="solid"), href="/"),
                    spacing="2",
                ),
            ),
            spacing="6",
            align_items="center",
            justify_content="center",
            min_height="100vh",
            text_align="center",
            width="100%",
        ),
        max_width="600px",
        padding_y="5",
    )
