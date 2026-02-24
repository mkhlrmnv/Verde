from __future__ import annotations

import reflex as rx

from app.state import AppState


ACCEPT_TYPES = {
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ".txt": ["text/plain"],
}


def upload_panel() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.heading("Build your applicant profile", size="9", text_align="center"),
                rx.text(
                    "Upload your CV and cover letters. We'll extract experience, skills, and preferences into a structured profile.",
                    size="4",
                    color="#4b5563",
                    text_align="center",
                    max_width="44rem",
                ),
                spacing="3",
                align_items="center",
                width="100%",
                margin_bottom="2rem",
            ),
            rx.upload(
                rx.vstack(
                    rx.heading("Click to upload or drag and drop", size="5"),
                    rx.text("PDF, DOCX, or TXT", size="2", color="#6b7280"),
                    spacing="2",
                    align_items="center",
                ),
                id="upload_documents",
                multiple=True,
                accept=ACCEPT_TYPES,
                on_drop=AppState.handle_document_uploads(rx.upload_files(upload_id="upload_documents")),
                width="100%",
                border="2px dashed",
                border_color="gray.5",
                border_radius="20px",
                padding="3rem",
                background_color="white",
                cursor="pointer",
            ),
            rx.cond(
                AppState.has_files,
                rx.vstack(
                    rx.text("Selected Files", weight="medium", size="2", color="#374151"),
                    rx.vstack(
                        rx.foreach(
                            AppState.selected_files,
                            lambda item: rx.hstack(
                                rx.badge(item["kind"], variant="soft", color_scheme="gray"),
                                rx.text(item["name"], size="2"),
                                justify="start",
                                align="center",
                                width="100%",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    margin_top="1.5rem",
                ),
            ),
            rx.hstack(
                rx.button(
                    "Generate Profile",
                    on_click=AppState.parse_and_generate_profile,
                    loading=AppState.is_processing,
                    disabled=AppState.has_cv == False,
                    size="3",
                ),
                rx.cond(
                    AppState.has_saved_profile,
                    rx.button("Use existing saved profile", on_click=AppState.load_saved_profile_json, size="3"),
                    rx.button("Use existing saved profile", disabled=True, size="3"),
                ),
                wrap="wrap",
                justify="end",
                width="100%",
                margin_top="1.5rem",
            ),
            rx.text(
                "The first valid file is treated as CV; additional files are treated as cover letters.",
                size="1",
                color="#6b7280",
            ),
            rx.cond(
                AppState.has_warnings,
                rx.callout(
                    rx.foreach(AppState.extraction_warnings, lambda warning: rx.text(warning)),
                    icon="triangle_alert",
                    color_scheme="amber",
                ),
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),
        width="100%",
        max_width="48rem",
        margin_x="auto",
        padding_x="1rem",
    )
