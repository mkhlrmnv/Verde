from __future__ import annotations

import reflex as rx

from app.models.clarification import GapQuestionData
from app.state import AppState


def _render_multi_select_question(question: rx.Var[GapQuestionData]) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(question["label"], size="3", weight="medium"),
            rx.cond(question["required"], rx.badge("Required", color_scheme="red", variant="soft")),
            align="center",
            spacing="2",
            width="100%",
        ),
        rx.text(question["prompt"], size="2", color="#6b7280"),
        rx.hstack(
            rx.foreach(
                question["options"],
                lambda option: rx.button(
                    option,
                    variant=rx.cond(
                        AppState.clarification_answers[question["field_key"]].contains(option),
                        "solid",
                        "soft",
                    ),
                    color_scheme="indigo",
                    on_click=AppState.toggle_clarification_option(question["field_key"], option),
                    size="2",
                ),
            ),
            wrap="wrap",
            spacing="2",
            width="100%",
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
    )


def _render_text_list_question(question: rx.Var[GapQuestionData]) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(question["label"], size="3", weight="medium"),
            rx.cond(question["required"], rx.badge("Required", color_scheme="red", variant="soft")),
            align="center",
            spacing="2",
            width="100%",
        ),
        rx.text(question["prompt"], size="2", color="#6b7280"),
        rx.text_area(
            on_change=lambda value: AppState.set_clarification_text_answer(question["field_key"], value),
            placeholder="Enter values separated by commas or new lines",
            min_height="6rem",
            width="100%",
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
    )


def clarification_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Help us refine your profile", size="7"),
            rx.text(
                "We found a few missing preferences. Answer the questions below and we'll merge them into your profile.",
                color="#4b5563",
                size="3",
            ),
            rx.foreach(
                AppState.gap_questions,
                lambda question: rx.cond(
                    question["input_type"] == "multi_select",
                    _render_multi_select_question(question),
                    _render_text_list_question(question),
                ),
            ),
            rx.hstack(
                rx.button(
                    "Skip for now",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.skip_clarifications,
                    disabled=AppState.is_refining,
                ),
                rx.button(
                    "Refine profile",
                    on_click=AppState.submit_clarifications_and_refine,
                    loading=AppState.is_refining,
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
