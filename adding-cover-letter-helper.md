# Cover Letter Helper — Builder Implementation TODO

## 1. State Management (Reflex rx.State)

### 1.1 Extend `Step` routing contract
- [ ] **File:** `app/state.py`
	- **Change:** Expand `Step` to include new phases for the helper flow.
	- **Logic/Function:**
		- Update `Step = Literal[...]` from current flow to include:
			- `"job_input"` (new page where user pastes job listing)
			- `"cover_helper_results"` (new page showing strengths/gaps/strategy)
		- Keep existing steps (`upload`, `processing`, `clarification`, `profile`) unchanged.
	- **Breaking changes / edge cases:**
		- Any `@rx.var` step checks or UI branches that assume only current values may silently fail.
		- Ensure default `step` remains stable (`"upload"`) to avoid changing initial app behavior.

### 1.2 Add new state variables (`vars`) for helper workflow
- [ ] **File:** `app/state.py`
	- **Change:** Add dedicated vars for job input, async state, and structured response storage.
	- **Logic/Function:** add exact fields under `AppState`:
		- `job_listing_text: str = ""`
		- `is_generating_cover_helper: bool = False`
		- `cover_helper_error: str = ""` (optional separate error channel; can reuse `error_message` if preferred)
		- `cover_helper_result: dict[str, Any] = {"strengths": [], "weaknesses_gaps": [], "cover_letter_strategy": []}`
		- `cover_helper_generated_at: str = ""` (optional display metadata)
	- **Breaking changes / edge cases:**
		- Keep dictionary shape stable so `rx.foreach` bindings do not break when response is empty.
		- Do not mix helper loading flag with existing `is_processing`; keep isolated to avoid disabling unrelated buttons.

### 1.3 Add computed vars for conditional rendering and button enablement
- [ ] **File:** `app/state.py`
	- **Change:** Add `@rx.var` helpers for UI control.
	- **Logic/Function:**
		- `is_job_input_step -> self.step == "job_input"`
		- `is_cover_helper_results_step -> self.step == "cover_helper_results"`
		- `has_job_listing_text -> bool(self.job_listing_text.strip())`
		- `has_cover_helper_result -> any([...])` checking each section length
	- **Breaking changes / edge cases:**
		- Avoid expensive computations in `@rx.var`; keep simple boolean checks.

### 1.4 Add input mutator and reset helpers
- [ ] **File:** `app/state.py`
	- **Change:** Add setters/resetters to keep state transitions deterministic.
	- **Logic/Function:**
		- `def set_job_listing_text(self, value: str) -> None`
		- `def clear_cover_helper_state(self) -> None` resetting text/result/errors/loading
		- In `reset_app()`, include reset of all new helper vars.
	- **Breaking changes / edge cases:**
		- `reset_app()` already has many responsibilities; ensure helper reset is not skipped when called from top nav.

### 1.5 Add navigation event from profile to new job input step
- [ ] **File:** `app/state.py`
	- **Change:** Add explicit event for the new “Move Forward” button.
	- **Logic/Function:**
		- `def move_to_job_listing_input(self) -> None`
			- Preconditions:
				- Validate `has_meaningful_profile`; if false, set error and keep `step="profile"`.
			- Transition:
				- Clear stale helper messages/results (not user text unless explicitly desired).
				- Set `step = "job_input"`.
	- **Breaking changes / edge cases:**
		- User may click repeatedly; event should be idempotent.
		- Preserve unsaved profile edits already present in `self.profile`.

### 1.6 Add async orchestration event for analysis generation
- [ ] **File:** `app/state.py`
	- **Change:** Add a background event to call Google AI API and store structured output.
	- **Logic/Function:**
		- `@rx.event(background=True)`
		- `async def generate_cover_helper_analysis(self) -> None`
			- `async with self:` pre-checks:
				- block if `is_generating_cover_helper` is already `True`
				- validate `job_listing_text.strip()` is non-empty
				- validate profile via `ApplicantProfile.model_validate(self.profile)`
				- clear old helper error; set loading flag
			- run blocking service call through `run_in_thread(...)`
			- parse/validate response model
			- `async with self:` save normalized response into `cover_helper_result`, clear loading, set `step = "cover_helper_results"`
			- exception paths set clear user-facing error and always clear loading flag
	- **Breaking changes / edge cases:**
		- Race conditions from double-click submit while background event runs.
		- Ensure finalizer clears loading flag on all exception branches.

### 1.7 Add optional back-navigation events for smooth UX
- [ ] **File:** `app/state.py`
	- **Change:** Add optional events to re-edit input and rerun analysis.
	- **Logic/Function:**
		- `def back_to_profile_from_job_input(self) -> None`
		- `def back_to_job_input(self) -> None` (from results page)
	- **Breaking changes / edge cases:**
		- Preserve pasted listing when navigating back from results unless user explicitly clears.


## 2. API Integration Strategy

### 2.1 Introduce dedicated model contract for structured LLM output
- [ ] **File:** `app/models/cover_helper.py` (new)
	- **Change:** Add strict Pydantic models for response validation.
	- **Logic/Function:**
		- `StrengthItem`: `matched_skill`, `job_requirement`, `why_it_matches`, `evidence_from_profile`
		- `GapItem`: `missing_or_weak_skill`, `job_requirement`, `gap_impact`, `improvement_suggestion`
		- `StrategyItem`: `focus_skill`, `reason_to_highlight`, `example_snippet` (short snippet only)
		- `CoverHelperAnalysis`: 
			- `strengths: list[StrengthItem]`
			- `weaknesses_gaps: list[GapItem]`
			- `cover_letter_strategy: list[StrategyItem]`
			- optional `disclaimer: str`
		- `ConfigDict(extra="forbid")` on all models.
	- **Breaking changes / edge cases:**
		- Any extra JSON key from model should fail fast and surface a parsing error.
		- Keep field names aligned with UI keys exactly.

### 2.2 Add dedicated service for helper generation (separate from profile builder)
- [ ] **File:** `app/services/cover_letter_helper.py` (new)
	- **Change:** Implement isolated Google API orchestration logic.
	- **Logic/Function:**
		- Reuse env loading pattern from `app/services/google_profile_builder.py`.
		- Export:
			- `class CoverHelperGenerationError(Exception)`
			- `def generate_cover_helper_analysis_once(profile: ApplicantProfile, job_listing: str) -> CoverHelperAnalysis`
		- Keep function synchronous; call from state via `run_in_thread`.
	- **Breaking changes / edge cases:**
		- Do not mutate existing profile generation logic.
		- Missing API key should return explicit actionable error.

### 2.3 Use JSON-only prompting with hard anti-cover-letter constraints
- [ ] **File:** `app/services/cover_letter_helper.py`
	- **Change:** Build strict prompt payload that forces analysis-only output.
	- **Logic/Function (prompt structure):**
		- **System instruction block** must explicitly include:
			- “You are an analysis engine.”
			- “DO NOT write a full cover letter.”
			- “DO NOT output salutations, sign-off, or multi-paragraph narrative letter text.”
			- “Return valid JSON only; no markdown fences.”
		- **Input sections:**
			- `ApplicantProfile JSON:` serialized validated profile
			- `JobListing Text:` raw user listing
		- **Output schema contract in prompt:**
			- exact top-level keys: `strengths`, `weaknesses_gaps`, `cover_letter_strategy`
			- each `cover_letter_strategy.example_snippet` max 1–2 sentences
			- minimum and maximum items per list (recommended 3–7)
	- **Breaking changes / edge cases:**
		- If prompt is not strict enough, model may produce prose or fenced JSON.
		- Guard against prompt injection inside job listing by delimiting user text and reiterating rules after it.

### 2.4 Use structured output mode when available + strict post-validation fallback
- [ ] **File:** `app/services/cover_letter_helper.py`
	- **Change:** Prefer API-level structured response configuration; validate with Pydantic regardless.
	- **Logic/Function:**
		- Attempt `response_mime_type="application/json"` (or equivalent in installed SDK version).
		- Extract text, parse JSON, validate via `CoverHelperAnalysis.model_validate(...)`.
		- If invalid JSON: attempt safe extraction (`_extract_json_block` pattern) once, then fail.
	- **Breaking changes / edge cases:**
		- SDK option names differ by version; handle gracefully without silently downgrading quality.

### 2.5 Add hard post-processing guard to block accidental full cover letter output
- [ ] **File:** `app/services/cover_letter_helper.py`
	- **Change:** Add explicit safeguard before returning final model.
	- **Logic/Function:**
		- Heuristic checks across all textual fields:
			- reject if text contains letter-like patterns (`"Dear Hiring"`, `"Sincerely"`, long paragraph over threshold)
			- reject if any `example_snippet` exceeds max length policy
		- On violation: raise `CoverHelperGenerationError("Model returned disallowed full-letter style output")`.
	- **Breaking changes / edge cases:**
		- Heuristic must be conservative to avoid false positives on valid snippets.

### 2.6 Add tests for service and schema behavior
- [ ] **File:** `tests/test_cover_letter_helper.py` (new)
	- **Change:** Unit tests for parsing/validation and anti-letter guard.
	- **Logic/Function:**
		- valid structured JSON parses
		- markdown-fenced JSON recovery path works
		- prose-only response raises `CoverHelperGenerationError`
		- full-letter-like snippet is rejected
	- **Breaking changes / edge cases:**
		- Keep tests mocked; no live API calls.


## 3. UI Component Breakdown

### 3.1 Profile page update: add “Move Forward” trigger
- [ ] **File:** `app/components/profile_editor.py`
	- **Change:** Add a new primary/secondary button in header actions near `Export JSON`.
	- **Logic/Function:**
		- Add button label: `Move Forward` (or `Analyze Against Job Listing`)
		- `on_click=AppState.move_to_job_listing_input`
		- optional `disabled=~AppState.has_meaningful_profile`
	- **Breaking changes / edge cases:**
		- Keep existing visual balance in top action row.
		- Avoid removing `Export JSON` or changing existing profile editor controls.

### 3.2 Create new Job Listing input page content
- [ ] **File:** `app/pages/job_input.py` (new)
	- **Change:** Add page content wrapper matching existing layout style.
	- **Logic/Function:**
		- Header + helper text (“Paste the job listing you want to target”).
		- `rx.text_area` bound to `AppState.job_listing_text` + `on_change=AppState.set_job_listing_text`
		- CTA row:
			- `Analyze Fit & Strategy` button triggers `AppState.generate_cover_helper_analysis`
			- back button to profile (`AppState.back_to_profile_from_job_input`)
		- loading state: button `loading=AppState.is_generating_cover_helper`
	- **Breaking changes / edge cases:**
		- Text area must support long input without truncation.
		- Disable submit when no listing provided to prevent avoidable API calls.

### 3.3 Create results page with structured cards
- [ ] **File:** `app/pages/cover_helper_results.py` (new)
	- **Change:** Render structured analysis sections with Reflex primitives.
	- **Logic/Function:**
		- Use `rx.cond` for empty/loading/error states.
		- Use `rx.card` per section:
			- **Strengths**: `rx.foreach(AppState.cover_helper_result["strengths"], ...)`
			- **Weaknesses/Gaps**: `rx.foreach(AppState.cover_helper_result["weaknesses_gaps"], ...)`
			- **Cover Letter Strategy**: `rx.foreach(AppState.cover_helper_result["cover_letter_strategy"], ...)`
		- Include action buttons:
			- `Back to Job Listing` (`AppState.back_to_job_input`)
			- optional `Generate Again` (`AppState.generate_cover_helper_analysis`)
	- **Breaking changes / edge cases:**
		- Guard key access in dict-based state to avoid runtime errors when fields are empty/missing.

### 3.4 Wire the new steps into main page state renderer
- [ ] **File:** `app/pages/index.py`
	- **Change:** Extend nested step conditionals.
	- **Logic/Function:**
		- Insert new branch order after profile generation flow:
			- `is_upload_step -> upload_panel()`
			- `is_processing_step -> processing_view()`
			- `is_clarification_step -> clarification_content()`
			- `is_job_input_step -> job_input_content()`
			- `is_cover_helper_results_step -> cover_helper_results_content()`
			- fallback `profile_content()`
	- **Breaking changes / edge cases:**
		- Branch ordering matters; avoid unreachable states.

### 3.5 Optional route registration for direct route support
- [ ] **File:** `app/app.py`
	- **Change:** Optionally add dedicated routes if app architecture needs URL-level navigation.
	- **Logic/Function:**
		- Add pages only if you also implement route guards similar to existing `/profile` redirect pattern.
		- If staying fully state-driven in `/`, skip route additions for minimal change.
	- **Breaking changes / edge cases:**
		- Direct refresh on route can break flow if state is not initialized.

### 3.6 Keep top navigation behavior coherent
- [ ] **File:** `app/components/top_nav.py`
	- **Change:** Ensure `Start Over` is visible in new helper steps as appropriate.
	- **Logic/Function:**
		- Extend condition from current profile/clarification-only visibility to include job input and results steps.
	- **Breaking changes / edge cases:**
		- Reset must clear helper state too (covered in state reset TODO).


## 4. Execution Checklist

- [ ] Create `app/models/cover_helper.py` with strict `CoverHelperAnalysis` schema and nested item models.
- [ ] Create `app/services/cover_letter_helper.py` with `generate_cover_helper_analysis_once(...)` and dedicated error class.
- [ ] Implement prompt builder in service with hard rule: **DO NOT write a full cover letter** and JSON-only output.
- [ ] Add post-generation guardrail to reject letter-style outputs and oversized snippets.
- [ ] Add new state vars in `app/state.py`: `job_listing_text`, `is_generating_cover_helper`, `cover_helper_result`, `cover_helper_error`, metadata fields.
- [ ] Add `@rx.var` helpers: `is_job_input_step`, `is_cover_helper_results_step`, `has_job_listing_text`, `has_cover_helper_result`.
- [ ] Add state events: `set_job_listing_text`, `move_to_job_listing_input`, `back_to_profile_from_job_input`, `back_to_job_input`, `clear_cover_helper_state`.
- [ ] Add async background event `generate_cover_helper_analysis` using `run_in_thread` + validation + robust error handling.
- [ ] Update `reset_app()` to clear all helper vars and avoid stale result leaks.
- [ ] Update profile UI in `app/components/profile_editor.py` to include `Move Forward` button.
- [ ] Create `app/pages/job_input.py` with textarea + submit/back actions.
- [ ] Create `app/pages/cover_helper_results.py` rendering section cards with `rx.foreach` + `rx.cond`.
- [ ] Wire new state branches into `app/pages/index.py` in deterministic order.
- [ ] Update `app/components/top_nav.py` visibility logic for `Start Over` across new steps.
- [ ] Decide route strategy in `app/app.py` (state-only flow vs explicit routes) and implement consistently.
- [ ] Add tests in `tests/test_cover_letter_helper.py` for parsing, schema enforcement, and anti-full-letter guard.
- [ ] Add/extend state flow tests (new file recommended: `tests/test_cover_helper_state_flow.py`) for profile → job input → results transitions.
- [ ] Verify no regressions in existing profile generation tests and clarification flow tests.
- [ ] Run full test suite and fix only issues introduced by this feature.
- [ ] Update `README.md` with a concise section describing the new helper flow and non-generation-of-full-letter guarantee.

'runSubagent':builder
