from __future__ import annotations

import reflex as rx

from app.state import AppState


def top_nav() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.box(
                    rx.text("A", color="white", weight="bold", size="5"),
                    background_color="indigo",
                    border_radius="10px",
                    width="2rem",
                    height="2rem",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.text("Applicant Profile Builder", weight="medium", size="4"),
                spacing="2",
                align="center",
            ),
            rx.cond(
                AppState.is_profile_step | AppState.is_clarification_step,
                rx.button(
                    "Start Over",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.reset_app,
                    size="2",
                ),
            ),
            justify="between",
            align="center",
            width="100%",
            height="4rem",
            max_width="72rem",
            margin_x="auto",
            padding_x="1rem",
        ),
        position="sticky",
        top="0",
        z_index="50",
        background_color="white",
        border_bottom="1px solid",
        border_color="gray.3",
        width="100%",
    )
