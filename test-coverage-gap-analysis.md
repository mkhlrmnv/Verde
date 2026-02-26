## 1. Coverage Overview
Current suite is strong on deterministic pure functions and schema normalization (`cover_letter_helper` JSON parsing/guardrails, `google_profile_builder` normalization helpers, `gap_detector`, `profile_refiner`, schema persistence basics). Baseline stability is good (`31 passed`).

Major exposure is in orchestration/runtime behavior: most `AppState` async workflows, upload pipeline, loading/error transitions, and UI routing/conditional rendering are untested. There is also no measured line/branch report yet because `pytest-cov` is not currently available in the environment (coverage tooling blind spot).

**Well-tested today**
- Service-level normalization and deterministic merges.
- Basic profile schema compatibility and legacy migration on load.
- Limited profile→job-input state flow.

**High-risk, under-tested**
- Async state-machine transitions in `parse_and_generate_profile` and `generate_cover_helper_analysis`.
- Failure handling for external API calls (timeouts, empty responses, malformed JSON, unexpected exceptions).
- Upload parsing edge conditions (unsupported files, max file truncation, extraction failures).
- UI branch correctness for nested `rx.cond` trees and conditional button states.

## 2. State Management Gaps
### Uncovered `rx.State` async handlers (highest priority)
1. `AppState.parse_and_generate_profile`:
   - Guard path when `is_processing=True` (re-entrancy skip).
   - No CV path (`uploaded_cv` missing) and rollback behavior.
   - CV extraction failure (`TextExtractionError`) path.
   - Cover-letter partial extraction failures -> warnings accumulation while still succeeding.
   - Empty aggregated text path -> `step="upload"`, `is_processing=False`, error message set.
   - `ProfileGenerationError` and generic exception branches.
   - Success split path: `step="clarification"` vs `step="profile"` based on `has_gaps`.
   - `clarification_answers` key initialization from `gap_questions`.

2. `AppState.generate_cover_helper_analysis`:
   - Re-entrancy guard when already generating.
   - Empty job listing path.
   - Invalid profile (`ValidationError`) path.
   - Success path setting `cover_helper_result`, `cover_helper_generated_at`, `step="cover_helper_results"`.
   - `CoverHelperGenerationError`, `ValidationError`, and generic exception branches.
   - Ensure `is_generating_cover_helper` always resets to `False` after failure.

3. `AppState.handle_document_uploads`:
   - Empty file list error path.
   - All unsupported files path.
   - Mixed supported/unsupported files warning path.
   - Truncation path when files > `MAX_TOTAL_UPLOADS`.
   - Missing CV after filtering path.
   - Exception path from `save_upload_bytes`.

### Uncovered state variables / computed vars (`@rx.var`)
- Step booleans: `is_upload_step`, `is_processing_step`, `is_clarification_step`, `is_profile_step`, `is_job_input_step`, `is_cover_helper_processing_step`, `is_cover_helper_results_step`.
- File-related vars: `has_files`, `has_cv`, `cover_letter_count`, `selected_files`.
- Profile projection vars: `summary`, `skills`, `projects`, `experience`, `languages`, preference projections, and count vars.
- Helper vars: `has_job_listing_text`, `has_gap_questions`.

### Uncovered synchronous handlers with user-impact
- Clarification flows: `_normalize_clarification_values`, `set_clarification_text_answer`, `toggle_clarification_option`, `is_clarification_option_selected`, `clarification_answer_text`, `skip_clarifications`, `submit_clarifications_and_refine` required-field validation/error path.
- Save/load profile failure paths: `save_profile_json` and `load_saved_profile_json` exceptions and message flags.
- Editor mutators (skills/projects/experience/languages/preferences): add/update/remove boundary indices and Enter-key handlers.

## 3. Component & UI Gaps
### Critical conditional rendering not covered
- Root router in `pages/index.py`: deeply nested `rx.cond` decision tree across all steps (`upload -> processing -> clarification -> job_input -> cover_helper_processing -> cover_helper_results -> profile`).
- `components/upload_panel.py`:
  - `Selected Files` block visibility (`AppState.has_files`).
  - Saved-profile button enabled/disabled branch (`AppState.has_saved_profile`).
  - Warnings callout branch (`AppState.has_warnings`).
- `components/top_nav.py`: conditional `Start Over` button visibility across eligible steps.
- `pages/job_input.py`: helper error callout and analyze button disabled state (`has_job_listing_text == False`).
- `pages/cover_helper_results.py`:
  - Error callout branch (`cover_helper_error`).
  - Result-available branch (`has_cover_helper_result`) vs fallback empty-state card.
- `components/clarification_form.py`:
  - Multi-select vs text-list renderer branch by `input_type`.
  - Required badge rendering.
  - Selected-option visual state based on `clarification_answers` map.

### Suggested test type split
- Component-level smoke/render assertions for each major conditional branch.
- Integration-style state+component tests validating that state mutation drives expected rendered branch.

## 4. Edge Cases & API Mocks
### Google AI / external-service failure scenarios to add
1. Timeout/network failure during profile generation.
2. Timeout/network failure during cover-helper generation.
3. API returns response object with empty `text`.
4. API returns malformed JSON (non-parseable).
5. API returns fenced markdown + invalid inner JSON.
6. API returns JSON shape that fails Pydantic validation.
7. API returns letter-style snippet violating guardrails.
8. Missing `GOOGLE_API_KEY` env var.
9. `google.genai` import failure (dependency missing).

### Required `unittest.mock` patch targets
- Profile builder service-level tests:
  - `patch("app.services.google_profile_builder._create_model")`
  - `patch("app.services.google_profile_builder._load_prompt")` (optional deterministic prompt)
- Cover helper service-level tests:
  - `patch("app.services.cover_letter_helper._create_model")`
  - `patch("app.services.cover_letter_helper._request_content")`
- AppState orchestration tests (patch at import site in `app.state`):
  - `patch("app.state.run_in_thread", side_effect=fake_async_run_in_thread)`
  - `patch("app.state.extract_text_from_file")`
  - `patch("app.state.generate_profile_json_once")`
  - `patch("app.state.detect_profile_gaps")`
  - `patch("app.state.generate_cover_helper_analysis_once")`
  - `patch("app.state.save_upload_bytes")`

### Mock implementation notes
- Use `AsyncMock` for async helpers and state events.
- For `run_in_thread`, provide async side effect that executes the callable: `async def fake_async_run_in_thread(fn): return fn()`.
- Use lightweight response stubs with `.text` attribute for model replies.

## 5. Execution Checklist
### P0 — Async orchestration and failure containment
- [ ] test_parse_and_generate_profile_reentry_guard_skips_when_processing()
- [ ] test_parse_and_generate_profile_requires_uploaded_cv()
- [ ] test_parse_and_generate_profile_cv_extraction_failure_sets_upload_error()
- [ ] test_parse_and_generate_profile_cover_letter_extraction_warning_but_success()
- [ ] test_parse_and_generate_profile_empty_combined_text_rolls_back_state()
- [ ] test_parse_and_generate_profile_success_routes_to_clarification_with_answers_seeded()
- [ ] test_parse_and_generate_profile_success_routes_to_profile_when_no_gaps()
- [ ] test_parse_and_generate_profile_handles_profile_generation_error()
- [ ] test_generate_cover_helper_analysis_reentry_guard()
- [ ] test_generate_cover_helper_analysis_requires_job_listing_text()
- [ ] test_generate_cover_helper_analysis_invalid_profile_routes_to_profile()
- [ ] test_generate_cover_helper_analysis_success_sets_results_and_timestamp()
- [ ] test_generate_cover_helper_analysis_handles_cover_helper_generation_error()
- [ ] test_generate_cover_helper_analysis_handles_validation_error()
- [ ] test_generate_cover_helper_analysis_handles_unexpected_exception_and_resets_loading()

### P1 — Upload pipeline and clarification flow correctness
- [ ] test_handle_document_uploads_rejects_empty_input()
- [ ] test_handle_document_uploads_rejects_all_unsupported_files()
- [ ] test_handle_document_uploads_warns_and_truncates_when_exceeding_max_uploads()
- [ ] test_handle_document_uploads_warns_when_some_files_unsupported()
- [ ] test_handle_document_uploads_save_failure_sets_error_message()
- [ ] test_submit_clarifications_and_refine_blocks_when_required_answers_missing()
- [ ] test_submit_clarifications_and_refine_validation_error_path()
- [ ] test_toggle_clarification_option_is_case_insensitive()
- [ ] test_set_clarification_text_answer_normalizes_and_dedupes_values()

### P2 — UI branch coverage and state projections
- [ ] test_index_renders_upload_panel_when_upload_step()
- [ ] test_index_renders_processing_view_when_processing_step()
- [ ] test_index_renders_clarification_when_clarification_step()
- [ ] test_index_renders_job_input_when_job_input_step()
- [ ] test_index_renders_cover_helper_processing_when_cover_helper_processing_step()
- [ ] test_index_renders_cover_helper_results_when_results_step()
- [ ] test_upload_panel_saved_profile_button_enabled_only_when_profile_exists()
- [ ] test_cover_helper_results_shows_empty_state_when_no_results_and_no_error()
- [ ] test_top_nav_start_over_visibility_by_step()
- [ ] test_state_computed_vars_for_selected_files_counts_and_step_flags()

### P3 — Service hardening and dependency fault injection
- [ ] test_generate_profile_json_once_missing_google_api_key_raises()
- [ ] test_generate_profile_json_once_timeout_from_google_client_raises_profile_generation_error()
- [ ] test_generate_profile_json_once_empty_response_text_raises()
- [ ] test_generate_profile_json_once_invalid_json_raises()
- [ ] test_generate_cover_helper_analysis_once_empty_listing_raises()
- [ ] test_generate_cover_helper_analysis_once_request_failure_raises_cover_helper_generation_error()
- [ ] test_generate_cover_helper_analysis_once_empty_response_text_raises()
- [ ] test_generate_cover_helper_analysis_once_validation_failure_raises()
- [ ] test_generate_cover_helper_analysis_once_guardrails_reject_overlong_or_multi_sentence_snippet()

#agent:builder