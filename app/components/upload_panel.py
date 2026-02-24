from __future__ import annotations

import reflex as rx

from app.state import AppState


ACCEPT_TYPES = {
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ".txt": ["text/plain"],
}


def upload_panel() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Upload documents", size="5"),
            rx.text("Upload one CV and up to 10 cover letters (.pdf, .docx, .txt). Files are stored right after selection."),
            rx.hstack(
                rx.card(
                    rx.vstack(
                        rx.heading("CV", size="4"),
                        rx.text("Max 1 file"),
                        rx.upload(
                            rx.vstack(
                                rx.button("Select CV", type="button"),
                                rx.text("or drag and drop"),
                            ),
                            id="upload_cv",
                            multiple=True,
                            accept=ACCEPT_TYPES,
                            on_drop=AppState.handle_cv_upload(rx.upload_files(upload_id="upload_cv")),
                        ),
                        rx.cond(AppState.has_cv, rx.text("Selected CV: " + AppState.uploaded_cv["name"], size="2")),
                        spacing="2",
                        align_items="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.vstack(
                        rx.heading("Cover letters", size="4"),
                        rx.text("Max 10 files"),
                        rx.upload(
                            rx.vstack(
                                rx.button("Select cover letters", type="button"),
                                rx.text("or drag and drop"),
                            ),
                            id="upload_cover_letters",
                            multiple=True,
                            accept=ACCEPT_TYPES,
                            on_drop=AppState.handle_cover_letter_uploads(
                                rx.upload_files(upload_id="upload_cover_letters")
                            ),
                        ),
                        rx.cond(
                            AppState.cover_letter_count > 0,
                            rx.vstack(
                                rx.text("Selected cover letters:", size="2"),
                                rx.foreach(
                                    AppState.uploaded_cover_letters,
                                    lambda item: rx.text("• " + item["name"], size="2"),
                                ),
                                spacing="1",
                                align_items="start",
                            ),
                        ),
                        spacing="2",
                        align_items="start",
                        width="100%",
                    ),
                    width="100%",
                ),
                width="100%",
                align="start",
                spacing="3",
            ),
            rx.hstack(
                rx.button("Parse & Generate Profile", on_click=AppState.parse_and_generate_profile, loading=AppState.is_processing),
                rx.cond(
                    AppState.has_saved_profile,
                    rx.button("Use existing saved profile", on_click=AppState.load_saved_profile_json),
                    rx.button("Use existing saved profile", disabled=True),
                ),
                wrap="wrap",
            ),
            rx.cond(
                AppState.has_warnings,
                rx.callout(
                    rx.foreach(AppState.extraction_warnings, lambda warning: rx.text(warning)),
                    icon="triangle_alert",
                    color_scheme="amber",
                ),
            ),
            spacing="4",
            align_items="start",
        ),
        width="100%",
    )
