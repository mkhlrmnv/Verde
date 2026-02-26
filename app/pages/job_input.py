from __future__ import annotations

import reflex as rx

from app.state import AppState


def job_input_content() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Target a Job Listing", size="7"),
            rx.text("Paste the job listing you want to target.", size="3", color="#4b5563"),
            rx.text_area(
                value=AppState.job_listing_text,
                on_change=AppState.set_job_listing_text,
                placeholder="Paste the full job listing here...",
                min_height="20rem",
                width="100%",
                resize="vertical",
            ),
            rx.cond(
                AppState.cover_helper_error != "",
                rx.callout(AppState.cover_helper_error, icon="triangle_alert", color_scheme="red"),
            ),
            rx.hstack(
                rx.button(
                    "Back to Profile",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.back_to_profile_from_job_input,
                ),
                rx.button(
                    "Analyze Fit & Strategy",
                    on_click=AppState.generate_cover_helper_analysis,
                    loading=AppState.is_generating_cover_helper,
                    disabled=AppState.has_job_listing_text == False,
                ),
                justify="end",
                width="100%",
                wrap="wrap",
            ),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
    )
