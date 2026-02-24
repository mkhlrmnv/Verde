from __future__ import annotations

import reflex as rx

from app.components.top_nav import top_nav
from app.components.upload_panel import upload_panel
from app.pages.loading import processing_view
from app.pages.profile import profile_content
from app.state import AppState


def index() -> rx.Component:
    return rx.box(
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
                    rx.cond(
                        AppState.is_upload_step,
                        upload_panel(),
                        rx.cond(
                            AppState.is_processing_step,
                            processing_view(),
                            profile_content(),
                        ),
                    ),
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
    )
