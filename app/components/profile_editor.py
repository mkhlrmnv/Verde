from __future__ import annotations

import reflex as rx

from app.state import AppState


def _editable_list(
    title: str,
    values: rx.Var,
    update_handler,
    remove_handler,
    new_value: rx.Var,
    set_new_value,
    add_handler,
) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading(title, size="4"),
            rx.foreach(
                values,
                lambda item, idx: rx.hstack(
                    rx.input(value=item, on_change=lambda value, i=idx: update_handler(i, value), width="100%"),
                    rx.icon_button("x", on_click=lambda i=idx: remove_handler(i), size="1"),
                    width="100%",
                ),
            ),
            rx.hstack(
                rx.input(value=new_value, on_change=set_new_value, placeholder=f"Add {title.lower()} item", width="100%"),
                rx.button("Add", on_click=add_handler),
                width="100%",
            ),
            spacing="2",
            align_items="stretch",
        ),
        width="100%",
    )


def _preferences_editor() -> rx.Component:
    return rx.vstack(
        _editable_list(
            "Preferred locations",
            AppState.preference_locations,
            AppState.update_pref_location,
            AppState.remove_pref_location,
            AppState.new_pref_location,
            AppState.set_new_pref_location,
            AppState.add_pref_location,
        ),
        _editable_list(
            "Preferred work types",
            AppState.preference_work_types,
            AppState.update_pref_work_type,
            AppState.remove_pref_work_type,
            AppState.new_pref_work_type,
            AppState.set_new_pref_work_type,
            AppState.add_pref_work_type,
        ),
        _editable_list(
            "Preferred mode",
            AppState.preference_modes,
            AppState.update_pref_mode,
            AppState.remove_pref_mode,
            AppState.new_pref_mode,
            AppState.set_new_pref_mode,
            AppState.add_pref_mode,
        ),
        _editable_list(
            "Preferred industries",
            AppState.preference_industries,
            AppState.update_pref_industry,
            AppState.remove_pref_industry,
            AppState.new_pref_industry,
            AppState.set_new_pref_industry,
            AppState.add_pref_industry,
        ),
        _editable_list(
            "Preferred company size",
            AppState.preference_company_sizes,
            AppState.update_pref_company_size,
            AppState.remove_pref_company_size,
            AppState.new_pref_company_size,
            AppState.set_new_pref_company_size,
            AppState.add_pref_company_size,
        ),
        width="100%",
    )


def _languages_editor() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Languages", size="4"),
            rx.foreach(
                AppState.languages,
                lambda item, idx: rx.hstack(
                    rx.input(
                        value=item["name"],
                        placeholder="Language",
                        on_change=lambda value, i=idx: AppState.update_language_name(i, value),
                    ),
                    rx.input(
                        value=item["level"],
                        placeholder="Level",
                        on_change=lambda value, i=idx: AppState.update_language_level(i, value),
                    ),
                    rx.icon_button("x", on_click=lambda i=idx: AppState.remove_language(i), size="1"),
                    width="100%",
                ),
            ),
            rx.hstack(
                rx.input(
                    value=AppState.new_language_name,
                    placeholder="Language",
                    on_change=AppState.set_new_language_name,
                    width="100%",
                ),
                rx.input(
                    value=AppState.new_language_level,
                    placeholder="Level",
                    on_change=AppState.set_new_language_level,
                    width="100%",
                ),
                rx.button("Add", on_click=AppState.add_language),
                width="100%",
            ),
            spacing="2",
            align_items="stretch",
        ),
        width="100%",
    )


def profile_editor() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Profile editor", size="5"),
            rx.text_area(
                value=AppState.summary,
                on_change=AppState.update_summary,
                min_height="140px",
                width="100%",
            ),
            _editable_list(
                "Skills",
                AppState.skills,
                AppState.update_skill,
                AppState.remove_skill,
                AppState.new_skill,
                AppState.set_new_skill,
                AppState.add_skill,
            ),
            _editable_list(
                "Projects",
                AppState.projects,
                AppState.update_project,
                AppState.remove_project,
                AppState.new_project,
                AppState.set_new_project,
                AppState.add_project,
            ),
            _editable_list(
                "Experience",
                AppState.experience,
                AppState.update_experience,
                AppState.remove_experience,
                AppState.new_experience,
                AppState.set_new_experience,
                AppState.add_experience,
            ),
            _preferences_editor(),
            _languages_editor(),
            rx.button("Save JSON", on_click=AppState.save_profile_json, loading=AppState.is_saving),
            spacing="4",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )
