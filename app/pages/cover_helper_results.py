from __future__ import annotations

import reflex as rx

from app.state import AppState


def _strengths_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Strengths", size="5"),
            rx.foreach(
                AppState.cover_helper_result["strengths"],
                lambda item: rx.card(
                    rx.vstack(
                        rx.text(item["matched_skill"], weight="medium"),
                        rx.text(item["job_requirement"], size="2", color="#4b5563"),
                        rx.text(item["why_it_matches"], size="2"),
                        rx.text(item["evidence_from_profile"], size="2", color="#374151"),
                        spacing="2",
                        align_items="start",
                    ),
                    width="100%",
                    variant="surface",
                ),
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
    )


def _gaps_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Weaknesses & Gaps", size="5"),
            rx.foreach(
                AppState.cover_helper_result["weaknesses_gaps"],
                lambda item: rx.card(
                    rx.vstack(
                        rx.text(item["missing_or_weak_skill"], weight="medium"),
                        rx.text(item["job_requirement"], size="2", color="#4b5563"),
                        rx.text(item["gap_impact"], size="2"),
                        rx.text(item["improvement_suggestion"], size="2", color="#374151"),
                        spacing="2",
                        align_items="start",
                    ),
                    width="100%",
                    variant="surface",
                ),
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
    )


def _strategy_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Cover Letter Strategy", size="5"),
            rx.foreach(
                AppState.cover_helper_result["cover_letter_strategy"],
                lambda item: rx.card(
                    rx.vstack(
                        rx.text(item["focus_skill"], weight="medium"),
                        rx.text(item["reason_to_highlight"], size="2", color="#4b5563"),
                        rx.text(item["example_snippet"], size="2"),
                        spacing="2",
                        align_items="start",
                    ),
                    width="100%",
                    variant="surface",
                ),
            ),
            spacing="3",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
    )


def cover_helper_results_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.heading("Job Fit Analysis", size="7"),
                rx.text("Review strengths, gaps, and strategy before drafting your letter.", size="3", color="#4b5563"),
                spacing="1",
                align_items="start",
            ),
            rx.hstack(
                rx.button("Back to Job Listing", variant="ghost", on_click=AppState.back_to_job_input),
                rx.button(
                    "Generate Again",
                    on_click=AppState.generate_cover_helper_analysis,
                    loading=AppState.is_generating_cover_helper,
                    disabled=AppState.has_job_listing_text == False,
                ),
                spacing="2",
            ),
            justify="between",
            align="center",
            width="100%",
            wrap="wrap",
        ),
        rx.cond(
            AppState.cover_helper_error != "",
            rx.callout(AppState.cover_helper_error, icon="triangle_alert", color_scheme="red"),
            rx.cond(
                AppState.has_cover_helper_result,
                rx.vstack(_strengths_section(), _gaps_section(), _strategy_section(), spacing="4", width="100%"),
                rx.card(
                    rx.text("No analysis available yet. Return to Job Listing and run analysis."),
                    width="100%",
                ),
            ),
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )
