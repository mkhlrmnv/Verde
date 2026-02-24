from __future__ import annotations

import reflex as rx

from app.pages import index, profile
from app.state import AppState

app = rx.App()
app.add_page(index, route="/", on_load=AppState.check_saved_profile_exists)
app.add_page(profile, route="/profile", on_load=AppState.check_saved_profile_exists)
