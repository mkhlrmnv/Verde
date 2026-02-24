from __future__ import annotations

import reflex as rx

from app.components.profile_editor import profile_editor
from app.components.top_nav import top_nav
from app.state import AppState


def _stat_card(label: str, value: rx.Var) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color="gray"),
            rx.heading(value, size="6"),
            align_items="start",
            spacing="1",
        ),
        width="100%",
    )


def profile() -> rx.Component:
    return rx.container(
        rx.vstack(
            top_nav(),
            rx.heading("Applicant Profile", size="8"),
            rx.cond(
                AppState.error_message != "",
                rx.callout(AppState.error_message, icon="triangle_alert", color_scheme="red"),
            ),
            rx.cond(
                AppState.success_message != "",
                rx.callout(AppState.success_message, icon="circle_check", color_scheme="green"),
            ),
            rx.cond(
                AppState.has_meaningful_profile,
                rx.hstack(
                    rx.box(profile_editor(), width="100%", flex="3"),
                    rx.vstack(
                        _stat_card("Skills", AppState.skills_count),
                        _stat_card("Projects", AppState.projects_count),
                        _stat_card("Experience", AppState.experience_count),
                        _stat_card("Languages", AppState.languages_count),
                        width="100%",
                        flex="1",
                        spacing="3",
                    ),
                    width="100%",
                    align="start",
                    spacing="4",
                ),
                rx.callout(
                    "No populated profile yet. Upload and generate from the Upload page, or load the saved profile JSON.",
                    icon="info",
                    color_scheme="blue",
                ),
            ),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        max_width="1100px",
        padding_y="5",
    )
