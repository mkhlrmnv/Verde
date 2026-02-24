from __future__ import annotations

import reflex as rx


def top_nav() -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.link(rx.button("Upload", variant="soft"), href="/"),
            rx.link(rx.button("Profile", variant="soft"), href="/profile"),
            spacing="2",
            justify="center",
            width="100%",
        ),
        width="100%",
    )
