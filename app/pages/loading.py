from __future__ import annotations

import reflex as rx

PROCESSING_MESSAGES = [
    "Reading your documents...",
    "Extracting work experience...",
    "Identifying key skills...",
    "Structuring projects...",
    "Analyzing preferences...",
    "Finalizing profile...",
]

HELPER_PROCESSING_MESSAGES = [
    "Reading your target role requirements...",
    "Matching your profile strengths to the job...",
    "Identifying potential gaps and risks...",
    "Building focused recommendation snippets...",
    "Finalizing actionable guidance...",
]


def processing_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.spinner(size="3"),
            rx.heading("Processing your profile...", size="8"),
            rx.text("We're extracting your documents and generating your profile with AI.", size="4", color="#4b5563"),
            rx.vstack(
                rx.foreach(PROCESSING_MESSAGES, lambda item: rx.text("• " + item, size="2", color="#6b7280")),
                align_items="start",
                spacing="1",
            ),
            rx.text("Powered by Google AI", size="1", color="#9ca3af"),
            spacing="5",
            align_items="center",
            justify_content="center",
            min_height="60vh",
            text_align="center",
            width="100%",
        ),
        max_width="36rem",
        margin_x="auto",
        padding_x="1rem",
    )


def cover_helper_processing_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.spinner(size="3"),
            rx.heading("Analyzing job fit with AI...", size="8"),
            rx.text(
                "We're comparing your profile to the job listing and generating focused recommendations.",
                size="4",
                color="#4b5563",
            ),
            rx.vstack(
                rx.foreach(HELPER_PROCESSING_MESSAGES, lambda item: rx.text("• " + item, size="2", color="#6b7280")),
                align_items="start",
                spacing="1",
            ),
            rx.text("Powered by Google AI", size="1", color="#9ca3af"),
            spacing="5",
            align_items="center",
            justify_content="center",
            min_height="60vh",
            text_align="center",
            width="100%",
        ),
        max_width="36rem",
        margin_x="auto",
        padding_x="1rem",
    )


def loading() -> rx.Component:
    return rx.box(
        rx.script("window.location.replace('/');"),
        width="100%",
        min_height="1px",
    )
