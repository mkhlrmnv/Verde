from __future__ import annotations

import reflex as rx

from app.components.profile_editor import profile_editor


def profile_content() -> rx.Component:
    return rx.box(profile_editor(), width="100%", max_width="72rem", margin_x="auto", padding_x="1rem")


def profile() -> rx.Component:
    return rx.box(
        rx.script("window.location.replace('/');"),
        width="100%",
        min_height="1px",
    )
