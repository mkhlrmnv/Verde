from __future__ import annotations

from pathlib import Path
import importlib
import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
import reflex as rx
from pydantic import ValidationError

from app.models.clarification import GapDetectionResult, GapQuestion
from app.models.cover_helper import CoverHelperAnalysis
from app.models.profile import ApplicantProfile
cover_helper_results_page = importlib.import_module("app.pages.cover_helper_results")
index_page = importlib.import_module("app.pages.index")
from app.services.cover_letter_helper import CoverHelperGenerationError, generate_cover_helper_analysis_once
from app.services.google_profile_builder import ProfileGenerationError, generate_profile_json_once
from app.state import MAX_COVER_LETTERS, MAX_TOTAL_UPLOADS, AppState
top_nav_component = importlib.import_module("app.components.top_nav")
upload_panel_component = importlib.import_module("app.components.upload_panel")
import app.state as state_module


class FakeUploadFile:
    def __init__(self, filename: str, data: bytes = b"file") -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


class _DumpOnly:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self._payload


def _state() -> AppState:
    return AppState(_reflex_internal_init=True)


async def _fake_async_run_in_thread(fn):
    return fn()


def _sample_profile() -> ApplicantProfile:
    return ApplicantProfile(
        summary="Backend engineer",
        skills=["Python", "FastAPI"],
        preferences={
            "locations": ["Berlin"],
            "work_types": ["full-time"],
            "remote_hybrid_on_site": ["remote"],
            "industries": ["FinTech"],
            "company_size": ["startup"],
        },
    )


@pytest.mark.asyncio
async def test_parse_and_generate_profile_reentry_guard_skips_when_processing() -> None:
    state = _state()
    state.is_processing = True
    state.step = "profile"
    state.error_message = "existing"

    await AppState.parse_and_generate_profile.fn(state)

    assert state.step == "profile"
    assert state.error_message == "existing"
    assert state.is_processing is True


@pytest.mark.asyncio
async def test_parse_and_generate_profile_requires_uploaded_cv() -> None:
    state = _state()

    await AppState.parse_and_generate_profile.fn(state)

    assert state.error_message == "Upload a CV before processing."
    assert state.step == "upload"
    assert state.is_processing is False


@pytest.mark.asyncio
async def test_parse_and_generate_profile_cv_extraction_failure_sets_upload_error() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "/tmp/cv.pdf"}

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file",
        side_effect=state_module.TextExtractionError("broken"),
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert "CV extraction failed" in state.error_message
    assert state.step == "upload"
    assert state.is_processing is False


@pytest.mark.asyncio
async def test_parse_and_generate_profile_cover_letter_extraction_warning_but_success() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "cv.pdf"}
    state.uploaded_cover_letters = [{"name": "cl1.pdf", "path": "cl1.pdf"}]

    def extract_side_effect(path: str) -> str:
        if path == "cl1.pdf":
            raise state_module.TextExtractionError("cannot parse")
        return "cv text"

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file", side_effect=extract_side_effect
    ), patch("app.state.generate_profile_json_once", return_value=_sample_profile()), patch(
        "app.state.detect_profile_gaps",
        return_value=GapDetectionResult(has_gaps=False, questions=[]),
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert state.step == "profile"
    assert state.is_processing is False
    assert state.extraction_warnings and "Cover letter extraction failed" in state.extraction_warnings[0]


@pytest.mark.asyncio
async def test_parse_and_generate_profile_empty_combined_text_rolls_back_state() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "cv.pdf"}

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file", return_value="   "
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert state.combined_text == ""
    assert state.error_message == "Unable to extract meaningful text from uploaded documents."
    assert state.step == "upload"
    assert state.is_processing is False


@pytest.mark.asyncio
async def test_parse_and_generate_profile_success_routes_to_clarification_with_answers_seeded() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "cv.pdf"}

    questions = [
        GapQuestion(
            field_key="preferences.work_types",
            label="Preferred Work Types",
            prompt="Pick one",
            input_type="multi_select",
            required=True,
            options=["full-time"],
        ),
        GapQuestion(
            field_key="preferences.locations",
            label="Preferred Locations",
            prompt="List",
            input_type="text_list",
            required=False,
            options=[],
        ),
    ]

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file", return_value="cv text"
    ), patch("app.state.generate_profile_json_once", return_value=_sample_profile()), patch(
        "app.state.detect_profile_gaps",
        return_value=GapDetectionResult(has_gaps=True, questions=questions),
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert state.step == "clarification"
    assert state.has_gaps is True
    assert set(state.clarification_answers.keys()) == {"preferences.work_types", "preferences.locations"}
    assert state.clarification_answers["preferences.work_types"] == []


@pytest.mark.asyncio
async def test_parse_and_generate_profile_success_routes_to_profile_when_no_gaps() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "cv.pdf"}

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file", return_value="cv text"
    ), patch("app.state.generate_profile_json_once", return_value=_sample_profile()), patch(
        "app.state.detect_profile_gaps",
        return_value=GapDetectionResult(has_gaps=False, questions=[]),
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert state.step == "profile"
    assert state.has_gaps is False
    assert state.success_message == "Profile generated successfully."


@pytest.mark.asyncio
async def test_parse_and_generate_profile_handles_profile_generation_error() -> None:
    state = _state()
    state.uploaded_cv = {"name": "cv.pdf", "path": "cv.pdf"}

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.extract_text_from_file", return_value="cv text"
    ), patch(
        "app.state.generate_profile_json_once",
        side_effect=ProfileGenerationError("bad output"),
    ):
        await AppState.parse_and_generate_profile.fn(state)

    assert state.error_message == "bad output"
    assert state.step == "upload"
    assert state.is_processing is False


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_reentry_guard() -> None:
    state = _state()
    state.is_generating_cover_helper = True
    state.step = "job_input"
    state.job_listing_text = "listing"

    await AppState.generate_cover_helper_analysis.fn(state)

    assert state.is_generating_cover_helper is True
    assert state.step == "job_input"


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_requires_job_listing_text() -> None:
    state = _state()
    state.profile = _sample_profile().model_dump()
    state.job_listing_text = "   "

    await AppState.generate_cover_helper_analysis.fn(state)

    assert state.cover_helper_error == "Paste a job listing before running analysis."
    assert state.step == "job_input"


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_invalid_profile_routes_to_profile() -> None:
    state = _state()
    state.profile = {"invalid": True}
    state.job_listing_text = "listing"

    await AppState.generate_cover_helper_analysis.fn(state)

    assert "Profile is invalid and cannot be analyzed" in state.cover_helper_error
    assert state.step == "profile"


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_success_sets_results_and_timestamp() -> None:
    state = _state()
    state.profile = _sample_profile().model_dump()
    state.job_listing_text = "Job listing text"

    analysis = CoverHelperAnalysis.model_validate(
        {
            "strengths": [
                {
                    "matched_skill": "Python",
                    "job_requirement": "APIs",
                    "why_it_matches": "Built APIs",
                    "evidence_from_profile": "5 years",
                }
            ],
            "weaknesses_gaps": [
                {
                    "missing_or_weak_skill": "Kubernetes",
                    "job_requirement": "K8s",
                    "gap_impact": "Ramp up",
                    "improvement_suggestion": "Hands-on project",
                }
            ],
            "cover_letter_strategy": [
                {
                    "focus_skill": "Reliability",
                    "reason_to_highlight": "Key requirement",
                    "example_snippet": "I improved SLOs significantly.",
                }
            ],
        }
    )

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.generate_cover_helper_analysis_once", return_value=analysis
    ):
        await AppState.generate_cover_helper_analysis.fn(state)

    assert state.step == "cover_helper_results"
    assert state.cover_helper_result["strengths"][0]["matched_skill"] == "Python"
    assert state.cover_helper_generated_at
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", state.cover_helper_generated_at)
    assert state.is_generating_cover_helper is False


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_handles_cover_helper_generation_error() -> None:
    state = _state()
    state.profile = _sample_profile().model_dump()
    state.job_listing_text = "listing"

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.generate_cover_helper_analysis_once",
        side_effect=CoverHelperGenerationError("request failed"),
    ):
        await AppState.generate_cover_helper_analysis.fn(state)

    assert state.cover_helper_error == "request failed"
    assert state.step == "job_input"
    assert state.is_generating_cover_helper is False


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_handles_validation_error() -> None:
    state = _state()
    state.profile = _sample_profile().model_dump()
    state.job_listing_text = "listing"

    invalid_result = _DumpOnly(
        {
            "strengths": "invalid",
            "weaknesses_gaps": [],
            "cover_letter_strategy": [],
        }
    )

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.generate_cover_helper_analysis_once", return_value=invalid_result
    ):
        await AppState.generate_cover_helper_analysis.fn(state)

    assert state.step == "job_input"
    assert "Invalid analysis response" in state.cover_helper_error
    assert state.is_generating_cover_helper is False


@pytest.mark.asyncio
async def test_generate_cover_helper_analysis_handles_unexpected_exception_and_resets_loading() -> None:
    state = _state()
    state.profile = _sample_profile().model_dump()
    state.job_listing_text = "listing"

    with patch("app.state.run_in_thread", side_effect=_fake_async_run_in_thread), patch(
        "app.state.generate_cover_helper_analysis_once",
        side_effect=RuntimeError("boom"),
    ):
        await AppState.generate_cover_helper_analysis.fn(state)

    assert state.step == "job_input"
    assert state.cover_helper_error.startswith("Failed to generate cover helper analysis:")
    assert state.is_generating_cover_helper is False


@pytest.mark.asyncio
async def test_handle_document_uploads_rejects_empty_input() -> None:
    state = _state()

    await state.handle_document_uploads([])

    assert state.error_message == "No files selected."


@pytest.mark.asyncio
async def test_handle_document_uploads_rejects_all_unsupported_files() -> None:
    state = _state()

    files = [FakeUploadFile("file.exe"), FakeUploadFile("notes.md")]
    await state.handle_document_uploads(files)

    assert state.error_message.startswith("No supported files uploaded")


@pytest.mark.asyncio
async def test_handle_document_uploads_warns_and_truncates_when_exceeding_max_uploads() -> None:
    state = _state()

    files = [FakeUploadFile(f"doc_{i}.pdf") for i in range(MAX_TOTAL_UPLOADS + 3)]

    with patch("app.state.save_upload_bytes", side_effect=lambda **kwargs: Path("/tmp") / kwargs["filename"]):
        await state.handle_document_uploads(files)

    assert state.error_message == ""
    assert state.uploaded_cv["name"] == "doc_0.pdf"
    assert len(state.uploaded_cover_letters) == MAX_COVER_LETTERS
    assert any("Only the first" in warning for warning in state.extraction_warnings)


@pytest.mark.asyncio
async def test_handle_document_uploads_warns_when_some_files_unsupported() -> None:
    state = _state()
    files = [FakeUploadFile("cv.pdf"), FakeUploadFile("bad.exe"), FakeUploadFile("cover.txt")]

    with patch("app.state.save_upload_bytes", side_effect=lambda **kwargs: Path("/tmp") / kwargs["filename"]):
        await state.handle_document_uploads(files)

    assert state.error_message == ""
    assert any("unsupported files were skipped" in warning for warning in state.extraction_warnings)
    assert state.uploaded_cv["name"] == "cv.pdf"
    assert len(state.uploaded_cover_letters) == 1


@pytest.mark.asyncio
async def test_handle_document_uploads_save_failure_sets_error_message() -> None:
    state = _state()
    files = [FakeUploadFile("cv.pdf")]

    with patch("app.state.save_upload_bytes", side_effect=RuntimeError("disk full")):
        await state.handle_document_uploads(files)

    assert state.error_message == "File upload failed: disk full"


def test_submit_clarifications_and_refine_blocks_when_required_answers_missing() -> None:
    state = _state()
    state.gap_questions = [
        {
            "field_key": "preferences.work_types",
            "label": "Work Types",
            "prompt": "p",
            "input_type": "multi_select",
            "required": True,
            "options": ["full-time"],
        }
    ]
    state.clarification_answers = {"preferences.work_types": []}

    state.submit_clarifications_and_refine()

    assert "Please answer required questions" in state.error_message
    assert state.is_refining is False


def test_submit_clarifications_and_refine_validation_error_path() -> None:
    state = _state()
    state.profile = {"unexpected": "field"}
    state.gap_questions = []
    state.clarification_answers = {}

    state.submit_clarifications_and_refine()

    assert "Refinement failed due to invalid profile data" in state.error_message
    assert state.is_refining is False


def test_toggle_clarification_option_is_case_insensitive() -> None:
    state = _state()
    state.clarification_answers = {"preferences.work_types": ["Remote"]}

    state.toggle_clarification_option("preferences.work_types", "remote")

    assert state.clarification_answers["preferences.work_types"] == []


def test_set_clarification_text_answer_normalizes_and_dedupes_values() -> None:
    state = _state()

    state.set_clarification_text_answer("preferences.locations", "Berlin, berlin\nParis,  Paris")

    assert state.clarification_answers["preferences.locations"] == ["Berlin", "Paris"]


def _rendered_string(component) -> str:
    return str(component.render())


def _index_state_for_step(step: str) -> SimpleNamespace:
    return SimpleNamespace(
        error_message="",
        success_message="",
        is_upload_step=step == "upload",
        is_processing_step=step == "processing",
        is_clarification_step=step == "clarification",
        is_job_input_step=step == "job_input",
        is_cover_helper_processing_step=step == "cover_helper_processing",
        is_cover_helper_results_step=step == "cover_helper_results",
    )


def test_index_renders_upload_panel_when_upload_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("upload"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "UPLOAD_PANEL" in rendered


def test_index_renders_processing_view_when_processing_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("processing"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "PROCESSING_VIEW" in rendered


def test_index_renders_clarification_when_clarification_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("clarification"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "CLARIFICATION_VIEW" in rendered


def test_index_renders_job_input_when_job_input_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("job_input"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "JOB_INPUT_VIEW" in rendered


def test_index_renders_cover_helper_processing_when_cover_helper_processing_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("cover_helper_processing"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "COVER_HELPER_PROCESSING_VIEW" in rendered


def test_index_renders_cover_helper_results_when_results_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_page, "AppState", _index_state_for_step("cover_helper_results"))
    monkeypatch.setattr(index_page, "upload_panel", lambda: rx.text("UPLOAD_PANEL"))
    monkeypatch.setattr(index_page, "processing_view", lambda: rx.text("PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "clarification_content", lambda: rx.text("CLARIFICATION_VIEW"))
    monkeypatch.setattr(index_page, "job_input_content", lambda: rx.text("JOB_INPUT_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_processing_view", lambda: rx.text("COVER_HELPER_PROCESSING_VIEW"))
    monkeypatch.setattr(index_page, "cover_helper_results_content", lambda: rx.text("COVER_HELPER_RESULTS_VIEW"))
    monkeypatch.setattr(index_page, "profile_content", lambda: rx.text("PROFILE_VIEW"))

    rendered = _rendered_string(index_page.index())

    assert "COVER_HELPER_RESULTS_VIEW" in rendered


def test_upload_panel_saved_profile_button_enabled_only_when_profile_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enabled_state = SimpleNamespace(
        handle_document_uploads=AppState.handle_document_uploads,
        parse_and_generate_profile=AppState.parse_and_generate_profile,
        load_saved_profile_json=AppState.load_saved_profile_json,
        has_files=True,
        selected_files=[{"kind": "CV", "name": "cv.pdf"}],
        has_saved_profile=True,
        is_processing=False,
        has_cv=True,
        has_warnings=False,
        extraction_warnings=[],
    )
    monkeypatch.setattr(upload_panel_component.rx, "cond", lambda cond, t, f=None: t if cond else f)
    monkeypatch.setattr(upload_panel_component.rx, "foreach", lambda *_args, **_kwargs: rx.text("FILES"))
    monkeypatch.setattr(upload_panel_component, "AppState", enabled_state)
    enabled_render = _rendered_string(upload_panel_component.upload_panel())

    disabled_state = SimpleNamespace(**{**enabled_state.__dict__, "has_saved_profile": False})
    monkeypatch.setattr(upload_panel_component, "AppState", disabled_state)
    disabled_render = _rendered_string(upload_panel_component.upload_panel())

    assert "Use existing saved profile" in enabled_render
    assert "disabled:true" not in enabled_render
    assert "Use existing saved profile" in disabled_render
    assert "disabled:true" in disabled_render


def test_cover_helper_results_shows_empty_state_when_no_results_and_no_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SimpleNamespace(
        cover_helper_error="",
        has_cover_helper_result=False,
        cover_helper_result={"strengths": [], "weaknesses_gaps": [], "cover_letter_strategy": []},
        is_generating_cover_helper=False,
        has_job_listing_text=True,
        back_to_job_input=AppState.back_to_job_input,
        generate_cover_helper_analysis=AppState.generate_cover_helper_analysis,
    )
    monkeypatch.setattr(cover_helper_results_page, "AppState", state)
    monkeypatch.setattr(cover_helper_results_page, "_strengths_section", lambda: rx.text("STRENGTHS"))
    monkeypatch.setattr(cover_helper_results_page, "_gaps_section", lambda: rx.text("GAPS"))
    monkeypatch.setattr(cover_helper_results_page, "_strategy_section", lambda: rx.text("STRATEGY"))

    rendered = _rendered_string(cover_helper_results_page.cover_helper_results_content())

    assert "No analysis available yet. Return to Job Listing and run analysis." in rendered


def test_top_nav_start_over_visibility_by_step(monkeypatch: pytest.MonkeyPatch) -> None:
    visible = _state()
    visible.step = "profile"
    hidden = _state()
    hidden.step = "upload"

    visible_condition = (
        visible.is_profile_step
        or visible.is_clarification_step
        or visible.is_job_input_step
        or visible.is_cover_helper_results_step
    )
    hidden_condition = (
        hidden.is_profile_step
        or hidden.is_clarification_step
        or hidden.is_job_input_step
        or hidden.is_cover_helper_results_step
    )

    assert visible_condition is True
    assert hidden_condition is False


def test_state_computed_vars_for_selected_files_counts_and_step_flags() -> None:
    state = _state()
    state.step = "job_input"
    state.uploaded_cv = {"name": "cv.pdf", "path": "/tmp/cv.pdf"}
    state.uploaded_cover_letters = [{"name": "c1.pdf", "path": "/tmp/c1.pdf"}, {"name": "c2.pdf", "path": "/tmp/c2.pdf"}]

    assert state.has_files is True
    assert state.has_cv is True
    assert state.cover_letter_count == 2
    assert state.selected_files == [
        {"kind": "CV", "name": "cv.pdf"},
        {"kind": "Cover Letter", "name": "c1.pdf"},
        {"kind": "Cover Letter", "name": "c2.pdf"},
    ]
    assert state.is_upload_step is False
    assert state.is_processing_step is False
    assert state.is_clarification_step is False
    assert state.is_profile_step is False
    assert state.is_job_input_step is True
    assert state.is_cover_helper_processing_step is False
    assert state.is_cover_helper_results_step is False


def test_generate_profile_json_once_missing_google_api_key_raises() -> None:
    with patch("app.services.google_profile_builder.load_dotenv", return_value=True), patch.dict(
        "os.environ", {"GOOGLE_API_KEY": "", "MODEL_NAME": "gemini-1.5-flash"}, clear=False
    ):
        with pytest.raises(ProfileGenerationError, match="GOOGLE_API_KEY is missing"):
            generate_profile_json_once("candidate corpus")


def test_generate_profile_json_once_timeout_from_google_client_raises_profile_generation_error() -> None:
    class FakeModels:
        def generate_content(self, model: str, contents: str):
            raise TimeoutError("timed out")

    fake_client = SimpleNamespace(models=FakeModels())

    with patch("app.services.google_profile_builder.load_dotenv", return_value=True), patch(
        "app.services.google_profile_builder._create_model", return_value=(fake_client, "gemini")
    ):
        with pytest.raises(ProfileGenerationError, match="Google model request failed"):
            generate_profile_json_once("candidate corpus")


def test_generate_profile_json_once_empty_response_text_raises() -> None:
    class FakeModels:
        def generate_content(self, model: str, contents: str):
            return SimpleNamespace(text="")

    fake_client = SimpleNamespace(models=FakeModels())

    with patch("app.services.google_profile_builder.load_dotenv", return_value=True), patch(
        "app.services.google_profile_builder._create_model", return_value=(fake_client, "gemini")
    ):
        with pytest.raises(ProfileGenerationError, match="empty response"):
            generate_profile_json_once("candidate corpus")


def test_generate_profile_json_once_invalid_json_raises() -> None:
    class FakeModels:
        def generate_content(self, model: str, contents: str):
            return SimpleNamespace(text="{not-valid-json}")

    fake_client = SimpleNamespace(models=FakeModels())

    with patch("app.services.google_profile_builder.load_dotenv", return_value=True), patch(
        "app.services.google_profile_builder._create_model", return_value=(fake_client, "gemini")
    ):
        with pytest.raises(ProfileGenerationError, match="Invalid model JSON output"):
            generate_profile_json_once("candidate corpus")


def test_generate_cover_helper_analysis_once_empty_listing_raises() -> None:
    with pytest.raises(CoverHelperGenerationError, match="Job listing text is empty"):
        generate_cover_helper_analysis_once(profile=_sample_profile(), job_listing="   ")


def test_generate_cover_helper_analysis_once_request_failure_raises_cover_helper_generation_error() -> None:
    with patch("app.services.cover_letter_helper.load_dotenv", return_value=True), patch(
        "app.services.cover_letter_helper._create_model", return_value=(SimpleNamespace(), "gemini")
    ), patch(
        "app.services.cover_letter_helper._request_content",
        side_effect=CoverHelperGenerationError("Google model request failed: timeout"),
    ):
        with pytest.raises(CoverHelperGenerationError, match="Google model request failed"):
            generate_cover_helper_analysis_once(profile=_sample_profile(), job_listing="listing")


def test_generate_cover_helper_analysis_once_empty_response_text_raises() -> None:
    with patch("app.services.cover_letter_helper.load_dotenv", return_value=True), patch(
        "app.services.cover_letter_helper._create_model", return_value=(SimpleNamespace(), "gemini")
    ), patch(
        "app.services.cover_letter_helper._request_content", return_value=SimpleNamespace(text="")
    ):
        with pytest.raises(CoverHelperGenerationError, match="empty response"):
            generate_cover_helper_analysis_once(profile=_sample_profile(), job_listing="listing")


def test_generate_cover_helper_analysis_once_validation_failure_raises() -> None:
    with patch("app.services.cover_letter_helper.load_dotenv", return_value=True), patch(
        "app.services.cover_letter_helper._create_model", return_value=(SimpleNamespace(), "gemini")
    ), patch(
        "app.services.cover_letter_helper._request_content", return_value=SimpleNamespace(text="{}")
    ), patch(
        "app.services.cover_letter_helper._safe_parse_analysis",
        side_effect=CoverHelperGenerationError("Invalid helper JSON output: invalid schema"),
    ):
        with pytest.raises(CoverHelperGenerationError, match="Invalid helper JSON output"):
            generate_cover_helper_analysis_once(profile=_sample_profile(), job_listing="listing")


def test_generate_cover_helper_analysis_once_guardrails_reject_overlong_or_multi_sentence_snippet() -> None:
    payload = {
        "strengths": [
            {
                "matched_skill": "Python",
                "job_requirement": "APIs",
                "why_it_matches": "Built APIs",
                "evidence_from_profile": "5 years",
            }
        ],
        "weaknesses_gaps": [
            {
                "missing_or_weak_skill": "Kubernetes",
                "job_requirement": "K8s",
                "gap_impact": "Ramp-up",
                "improvement_suggestion": "Hands-on lab",
            }
        ],
        "cover_letter_strategy": [
            {
                "focus_skill": "Impact",
                "reason_to_highlight": "Relevant",
                "example_snippet": "I led migration. I improved reliability. I drove platform adoption.",
            }
        ],
    }

    with patch("app.services.cover_letter_helper.load_dotenv", return_value=True), patch(
        "app.services.cover_letter_helper._create_model", return_value=(SimpleNamespace(), "gemini")
    ), patch(
        "app.services.cover_letter_helper._request_content",
        return_value=SimpleNamespace(text=str(payload).replace("'", '"')),
    ):
        with pytest.raises(CoverHelperGenerationError, match="disallowed full-letter style output"):
            generate_cover_helper_analysis_once(profile=_sample_profile(), job_listing="listing")
