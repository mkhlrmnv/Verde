from __future__ import annotations

from app.state import AppState


def test_move_to_job_listing_input_requires_meaningful_profile() -> None:
    state = AppState()
    state.step = "profile"
    state.profile = {
        "summary": "",
        "skills": [],
        "projects": [],
        "experience": [],
        "preferences": {
            "locations": [],
            "work_types": [],
            "remote_hybrid_on_site": [],
            "industries": [],
            "company_size": [],
        },
        "languages": [],
    }

    state.move_to_job_listing_input()

    assert state.step == "profile"
    assert "Generate or complete your profile" in state.error_message


def test_move_to_job_listing_input_is_idempotent_and_clears_stale_results() -> None:
    state = AppState()
    state.step = "profile"
    state.profile["summary"] = "Experienced engineer"
    state.cover_helper_error = "old error"
    state.cover_helper_generated_at = "2026-01-01T00:00:00"
    state.cover_helper_result = {
        "strengths": [{"matched_skill": "Python"}],
        "weaknesses_gaps": [{"missing_or_weak_skill": "Go"}],
        "cover_letter_strategy": [{"focus_skill": "Testing"}],
    }

    state.move_to_job_listing_input()
    state.move_to_job_listing_input()

    assert state.step == "job_input"
    assert state.cover_helper_error == ""
    assert state.cover_helper_generated_at == ""
    assert state.cover_helper_result["strengths"] == []


def test_back_navigation_preserves_job_listing_text() -> None:
    state = AppState()
    state.step = "job_input"
    state.job_listing_text = "Senior Backend Engineer"

    state.back_to_profile_from_job_input()
    state.back_to_job_input()

    assert state.step == "job_input"
    assert state.job_listing_text == "Senior Backend Engineer"


def test_clear_cover_helper_state_and_reset_app_clear_helper_fields() -> None:
    state = AppState()
    state.step = "cover_helper_results"
    state.job_listing_text = "Listing"
    state.cover_helper_error = "error"
    state.cover_helper_generated_at = "2026-01-01T00:00:00"
    state.cover_helper_result = {
        "strengths": [{"matched_skill": "Python"}],
        "weaknesses_gaps": [],
        "cover_letter_strategy": [],
    }

    state.clear_cover_helper_state()
    assert state.job_listing_text == ""
    assert state.has_cover_helper_result is False

    state.job_listing_text = "Another listing"
    state.cover_helper_result = {
        "strengths": [{"matched_skill": "Python"}],
        "weaknesses_gaps": [],
        "cover_letter_strategy": [],
    }
    state.reset_app()

    assert state.step == "upload"
    assert state.job_listing_text == ""
    assert state.has_cover_helper_result is False
