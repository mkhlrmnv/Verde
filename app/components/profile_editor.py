from __future__ import annotations

import reflex as rx

from app.state import AppState


FIELD_TEXT_COLOR = "#374151"
FIELD_BG_COLOR = "#D0D0D0"
PREFERENCE_CHIP_TEXT_COLOR = "#1F2937"


def _chip_list(values: rx.Var, remove_handler, text_color: str = FIELD_TEXT_COLOR) -> rx.Component:
    return rx.hstack(
        rx.foreach(
            values,
            lambda item, idx: rx.badge(
                rx.hstack(
                    rx.text(item, size="1", color="#1923339E"),
                    rx.icon_button("x", size="1", variant="ghost", on_click=lambda i=idx: remove_handler(i)),
                    align="center",
                    spacing="1",
                ),
                variant="soft",
                color_scheme="indigo",
            ),
        ),
        spacing="2",
        wrap="wrap",
        width="100%"
    )


def _preference_group(
    title: str,
    values: rx.Var,
    update_handler,
    remove_handler,
    new_value: rx.Var,
    set_value,
    add_handler,
    key_handler,
) -> rx.Component:
    return rx.vstack(
        rx.text(title, size="2", weight="medium", color=FIELD_TEXT_COLOR),
        _chip_list(values, remove_handler, PREFERENCE_CHIP_TEXT_COLOR),
        rx.hstack(
            rx.input(
                value=new_value,
                on_change=set_value,
                on_key_down=key_handler,
                placeholder=f"Add {title.lower()}...",
                width="100%",
                color=FIELD_TEXT_COLOR,
                background_color=FIELD_BG_COLOR,
            ),
            rx.button("Add", on_click=add_handler),
            width="100%",
        ),
        rx.foreach(
            values,
            lambda item, idx: rx.input(
                value=item,
                on_change=lambda value, i=idx: update_handler(i, value),
                size="1",
                color=FIELD_TEXT_COLOR,
                background_color=FIELD_BG_COLOR,
            ),
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
    )


def _experience_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Experience", size="5"),
                rx.button("Add", on_click=AppState.add_empty_experience, size="2"),
                justify="between",
                width="100%",
            ),
            rx.foreach(
                AppState.experience,
                lambda item, idx: rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.input(
                                value=item["role"],
                                placeholder="Role / Title",
                                on_change=lambda value, i=idx: AppState.update_experience_role(i, value),
                                width="100%",
                                color=FIELD_TEXT_COLOR,
                                background_color=FIELD_BG_COLOR
                            ),
                            rx.input(
                                value=item["company"],
                                placeholder="Company",
                                on_change=lambda value, i=idx: AppState.update_experience_company(i, value),
                                width="100%",
                                color=FIELD_TEXT_COLOR,
                                background_color=FIELD_BG_COLOR
                            ),
                            rx.icon_button("x", on_click=lambda i=idx: AppState.remove_experience(i), variant="ghost"),
                            width="100%",
                        ),
                        rx.input(
                            value=item["duration"],
                            placeholder="Duration",
                            on_change=lambda value, i=idx: AppState.update_experience_duration(i, value),
                            width="100%",
                            color=FIELD_TEXT_COLOR,
                            background_color=FIELD_BG_COLOR
                        ),
                        rx.text_area(
                            value=item["description"],
                            placeholder="Description",
                            on_change=lambda value, i=idx: AppState.update_experience_description(i, value),
                            width="100%",
                            min_height="6rem",
                            color=FIELD_TEXT_COLOR,
                            background_color=FIELD_BG_COLOR
                        ),
                        spacing="2",
                        width="100%",
                        align_items="stretch",
                        
                    ),
                    width="100%",
                    variant="surface",
                    
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Quick Add", size="2", weight="medium", color=FIELD_TEXT_COLOR),
                    rx.input(
                        value=AppState.new_experience_role,
                        placeholder="Role",
                        on_change=AppState.set_new_experience_role,
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR
                    ),
                    rx.input(
                        value=AppState.new_experience_company,
                        placeholder="Company",
                        on_change=AppState.set_new_experience_company,
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR
                    ),
                    rx.input(
                        value=AppState.new_experience_duration,
                        placeholder="Duration",
                        on_change=AppState.set_new_experience_duration,
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR
                    ),
                    rx.text_area(
                        value=AppState.new_experience_description,
                        placeholder="Description",
                        on_change=AppState.set_new_experience_description,
                        min_height="4rem",
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR
                    ),
                    rx.button("Add Experience", on_click=AppState.add_experience),
                    spacing="2",
                    width="100%",
                    align_items="stretch",
                ),
                width="100%",
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )


def _projects_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Projects", size="5"),
                rx.button("Add", on_click=AppState.add_empty_project, size="2"),
                justify="between",
                width="100%",
            ),
            rx.foreach(
                AppState.projects,
                lambda item, idx: rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.input(
                                value=item["name"],
                                placeholder="Project Name",
                                on_change=lambda value, i=idx: AppState.update_project_name(i, value),
                                width="100%",
                                color=FIELD_TEXT_COLOR,
                                background_color=FIELD_BG_COLOR,
                            ),
                            rx.icon_button("x", on_click=lambda i=idx: AppState.remove_project(i), variant="ghost"),
                            width="100%",
                        ),
                        rx.text_area(
                            value=item["description"],
                            placeholder="Project description",
                            on_change=lambda value, i=idx: AppState.update_project_description(i, value),
                            width="100%",
                            min_height="5rem",
                            color=FIELD_TEXT_COLOR,
                            background_color=FIELD_BG_COLOR,
                        ),
                        spacing="2",
                        width="100%",
                        align_items="stretch",
                    ),
                    width="100%",
                    variant="surface",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Quick Add", size="2", weight="medium", color=FIELD_TEXT_COLOR),
                    rx.input(
                        value=AppState.new_project_name,
                        placeholder="Project name",
                        on_change=AppState.set_new_project_name,
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR,
                    ),
                    rx.text_area(
                        value=AppState.new_project_description,
                        placeholder="Project description",
                        on_change=AppState.set_new_project_description,
                        min_height="4rem",
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR,
                    ),
                    rx.button("Add Project", on_click=AppState.add_project),
                    spacing="2",
                    width="100%",
                    align_items="stretch",
                ),
                width="100%",
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )


def _skills_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Skills", size="5"),
            _chip_list(AppState.skills, AppState.remove_skill),
            rx.hstack(
                rx.input(
                    value=AppState.new_skill,
                    on_change=AppState.set_new_skill,
                    on_key_down=AppState.add_skill_on_key,
                    placeholder="Add a skill and press Enter...",
                    width="100%",
                    color=FIELD_TEXT_COLOR,
                    background_color=FIELD_BG_COLOR,
                ),
                rx.button("Add", on_click=AppState.add_skill),
                width="100%",
            ),
            spacing="2",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )


def _preferences_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Preferences", size="5"),
            _preference_group(
                "Locations",
                AppState.preference_locations,
                AppState.update_pref_location,
                AppState.remove_pref_location,
                AppState.new_pref_location,
                AppState.set_new_pref_location,
                AppState.add_pref_location,
                AppState.add_pref_location_on_key,
            ),
            _preference_group(
                "Work Types",
                AppState.preference_work_types,
                AppState.update_pref_work_type,
                AppState.remove_pref_work_type,
                AppState.new_pref_work_type,
                AppState.set_new_pref_work_type,
                AppState.add_pref_work_type,
                AppState.add_pref_work_type_on_key,
            ),
            _preference_group(
                "Environment",
                AppState.preference_modes,
                AppState.update_pref_mode,
                AppState.remove_pref_mode,
                AppState.new_pref_mode,
                AppState.set_new_pref_mode,
                AppState.add_pref_mode,
                AppState.add_pref_mode_on_key,
            ),
            _preference_group(
                "Industries",
                AppState.preference_industries,
                AppState.update_pref_industry,
                AppState.remove_pref_industry,
                AppState.new_pref_industry,
                AppState.set_new_pref_industry,
                AppState.add_pref_industry,
                AppState.add_pref_industry_on_key,
            ),
            _preference_group(
                "Company Size",
                AppState.preference_company_sizes,
                AppState.update_pref_company_size,
                AppState.remove_pref_company_size,
                AppState.new_pref_company_size,
                AppState.set_new_pref_company_size,
                AppState.add_pref_company_size,
                AppState.add_pref_company_size_on_key,
            ),
            spacing="4",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )


def _languages_section() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Languages", size="5"),
                rx.button("Add", on_click=AppState.add_language, size="2"),
                justify="between",
                width="100%",
            ),
            rx.foreach(
                AppState.languages,
                lambda item, idx: rx.hstack(
                    rx.input(
                        value=item["name"],
                        placeholder="Language",
                        on_change=lambda value, i=idx: AppState.update_language_name(i, value),
                        width="100%",
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR,
                    ),
                    rx.input(
                        value=item["level"],
                        placeholder="Level",
                        on_change=lambda value, i=idx: AppState.update_language_level(i, value),
                        width="10rem",
                        color=FIELD_TEXT_COLOR,
                        background_color=FIELD_BG_COLOR,
                    ),
                    rx.icon_button("x", on_click=lambda i=idx: AppState.remove_language(i), variant="ghost"),
                    width="100%",
                ),
            ),
            rx.hstack(
                rx.input(
                    value=AppState.new_language_name,
                    placeholder="Language",
                    on_change=AppState.set_new_language_name,
                    width="100%",
                    color=FIELD_TEXT_COLOR,
                    background_color=FIELD_BG_COLOR,
                ),
                rx.input(
                    value=AppState.new_language_level,
                    placeholder="Level",
                    on_change=AppState.set_new_language_level,
                    width="10rem",
                    color=FIELD_TEXT_COLOR,
                    background_color=FIELD_BG_COLOR,
                ),
                rx.button("Add", on_click=AppState.add_language),
                width="100%",
            ),
            spacing="2",
            align_items="stretch",
            width="100%",
        ),
        width="100%",
    )


def profile_editor() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.heading("Applicant Profile", size="8"),
                rx.text("Review and edit your extracted information.", color="#4b5563"),
                spacing="1",
                align_items="start",
            ),
            rx.button("Export JSON", on_click=AppState.save_profile_json, loading=AppState.is_saving),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.hstack(
            rx.vstack(
                rx.card(
                    rx.vstack(
                        rx.heading("Professional Summary", size="5"),
                        rx.text_area(
                            value=AppState.summary,
                            on_change=AppState.update_summary,
                            min_height="8rem",
                            width="100%",
                            color=FIELD_TEXT_COLOR,
                            background_color=FIELD_BG_COLOR,
                        ),
                        spacing="2",
                        align_items="stretch",
                        width="100%",
                    ),
                    width="100%",
                ),
                _experience_section(),
                _projects_section(),
                spacing="4",
                width="100%",
                flex="2",
                align_items="stretch",
            ),
            rx.vstack(
                _skills_section(),
                _preferences_section(),
                _languages_section(),
                spacing="4",
                width="100%",
                flex="1",
                align_items="stretch",
            ),
            width="100%",
            align="start",
            spacing="4",
            flex_direction=["column", "column", "row"],
        ),
        width="100%",
        spacing="4",
        align_items="stretch",
    )
