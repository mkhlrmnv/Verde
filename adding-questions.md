# User Portfolio Refinement — Technical Pipeline TODO

## 0) Current State Snapshot (from codebase analysis)
- Flow is state-driven in `AppState.step`: `upload -> processing -> profile` in `app/state.py`, rendered in `app/pages/index.py`.
- AI generation currently happens once in `AppState.parse_and_generate_profile()` via `generate_profile_json_once()`.
- Result is stored in `AppState.profile` and immediately shown in editor (`app/components/profile_editor.py`).
- No intermediate clarification/gap phase exists.
- Existing schema already contains preference bucket `remote_hybrid_on_site`, but there is no missing-field detection logic.

---

## 1) Target Feature Pipeline (End-to-End)
1. User uploads CV + optional cover letters (existing).
2. System extracts/aggregates text and generates initial profile via Google API (existing).
3. **Gap Detection** runs on generated profile + source corpus.
4. If gaps exist, state transitions to **Clarification Page**.
5. User answers targeted questions (e.g., preferred work mode).
6. **Refinement Merge** applies answers into profile state.
7. Final refined profile is shown in existing editor and saved/exported normally.

---

## 2) Detailed TODO (File-by-file)

### A. Domain/Data Contracts

- [ ] **File:** `app/models/profile.py`
	- **Change:** Keep existing schema, but add optional model-level helper(s) or companion typed structures for refinement metadata if needed (do not pollute saved output schema).
	- **Logic to add:** Internal typing support for clarification answers mapped to profile fields (especially `preferences.remote_hybrid_on_site`, `preferences.work_types`, `preferences.locations`).
	- **Edge/breaking risks:**
		- Saved JSON schema must remain exactly unchanged.
		- Avoid adding persisted keys like `clarifications` into `ApplicantProfile` model dump.

- [ ] **New file:** `app/models/clarification.py`
	- **Change:** Create focused models for:
		- `GapQuestion` (id, label, target_field, input_type, options, required)
		- `GapDetectionResult` (questions + reason/context)
		- `ClarificationAnswerSet` (question_id -> answer payload)
	- **Logic to add:** Centralized, typed contract between gap detector, UI, and merge layer.
	- **Edge/breaking risks:**
		- Question IDs must be stable; changing IDs breaks answer mapping.
		- Support both single-select and free-text answer shapes safely.

### B. Gap Detection Service

- [ ] **New file:** `app/services/gap_detector.py`
	- **Change:** Add deterministic `detect_profile_gaps(profile, combined_text) -> GapDetectionResult`.
	- **Logic to add:**
		- Rule-based checks for missing/empty high-value fields:
			- `preferences.remote_hybrid_on_site`
			- `preferences.work_types`
			- optionally `preferences.locations`, `industries`, `company_size` when fully empty.
		- Optional text-aware checks: if corpus lacks explicit evidence for preference categories, ask clarification.
		- Priority ordering of questions so UI remains predictable.
	- **Edge/breaking risks:**
		- Over-questioning users when profile actually contains values in synonyms/casing variants.
		- Need normalization (`remote`, `Remote`, `work from home`) before deciding “missing”.

- [ ] **File:** `app/services/google_profile_builder.py`
	- **Change:** Keep generation responsibility isolated; do not mix gap detection into model call.
	- **Logic to add:** none mandatory, but optionally expose normalized evidence hooks used by detector.
	- **Edge/breaking risks:**
		- Avoid coupling LLM prompt logic with clarification logic; keeps testability high.

### C. Clarification Merge Service (Fine-Tuning)

- [ ] **New file:** `app/services/profile_refiner.py`
	- **Change:** Add `merge_clarifications_into_profile(profile, answers) -> ApplicantProfile`.
	- **Logic to add:**
		- Map question IDs to profile target fields.
		- Merge strategy:
			- For list fields, append normalized unique values.
			- For empty fields, set directly.
			- For pre-populated fields, avoid destructive overwrite unless explicitly intended.
		- De-duplication and canonicalization (e.g., `Remote`/`remote`).
	- **Edge/breaking risks:**
		- Duplicate accumulation on repeated submissions.
		- User answers accidentally replacing valid extracted preferences.

### D. State Machine + Business Logic

- [ ] **File:** `app/state.py`
	- **Change:** Extend step state and refinement state.
	- **Logic to add:**
		- Update `Step` literal to include `clarification`.
		- New state fields:
			- `gap_questions: list[dict]` (or typed serialized form)
			- `clarification_answers: dict[str, Any]`
			- `is_refining: bool`
			- `has_gaps: bool`
		- New computed vars:
			- `is_clarification_step`
			- `has_gap_questions`
		- In `parse_and_generate_profile()`:
			1) generate profile (existing),
			2) run gap detector,
			3) if gaps -> `step = "clarification"`, else `step = "profile"`.
		- New events:
			- `set_clarification_answer(question_id, value)`
			- `submit_clarifications_and_refine()`
			- `skip_clarifications()` (optional fallback)
			- `back_to_upload_from_clarification()` (optional UX)
		- `submit_clarifications_and_refine()` should call merge service and then route to profile step.
		- Reset logic (`reset_app`) must clear clarification state.
	- **Edge/breaking risks:**
		- Background event race conditions (double-click submit).
		- Existing top-nav `Start Over` must clear new refinement fields too.
		- Compatibility with `load_saved_profile_json()` should bypass clarification unless explicitly re-run.

### E. UI — Clarification Page

- [ ] **New file:** `app/components/clarification_form.py`
	- **Change:** Build dedicated component for question rendering.
	- **Logic to add:**
		- Render each `GapQuestion` with proper input control by `input_type`:
			- single select chips/radio (e.g., remote/hybrid/on-site)
			- multi-select (if needed)
			- free text input
		- Primary CTA: `Apply Answers & Continue`
		- Secondary CTA: `Skip for now` (optional)
		- Validation: required questions must be answered.
	- **Edge/breaking risks:**
		- Incorrect binding per question index/id can store answers under wrong key.
		- Invalid empty submissions should show clear message via `AppState.error_message`.

- [ ] **New file:** `app/pages/clarification.py`
	- **Change:** Add page-level wrapper (similar to `profile_content`) for clarification UI.
	- **Logic to add:** Compose heading, short explanation, form component, and status messages.
	- **Edge/breaking risks:**
		- Keep visual system consistent with existing neutral palette/components.

- [ ] **File:** `app/pages/index.py`
	- **Change:** Insert clarification branch into current conditional rendering pipeline.
	- **Logic to add:**
		- `upload` -> `upload_panel()`
		- `processing` -> `processing_view()`
		- `clarification` -> `clarification_content()`
		- `profile` -> `profile_content()`
	- **Edge/breaking risks:**
		- Conditional nesting readability/maintainability; keep branch order explicit.

- [ ] **File:** `app/components/top_nav.py`
	- **Change:** Adjust `Start Over` visibility to include clarification step (not profile-only).
	- **Logic to add:** show reset control when state is `clarification` or `profile`.
	- **Edge/breaking risks:**
		- Users getting stranded without reset if generation fails into clarification.

### F. App Wiring

- [ ] **File:** `app/app.py`
	- **Change:** Register clarification route/component only if route-based access is desired; otherwise keep index-only render path.
	- **Logic to add:** optional `app.add_page(clarification, route="/clarification")` with redirect compatibility.
	- **Edge/breaking risks:**
		- Current architecture is single-screen stateful; adding extra route can introduce state mismatch if hard-refreshed.

- [ ] **File:** `app/pages/__init__.py`
	- **Change:** export new clarification page helper(s) for clean imports.
	- **Edge/breaking risks:** import cycles if page imports state-heavy modules incorrectly.

### G. Tests (must be added for new behavior)

- [ ] **New file:** `tests/test_gap_detector.py`
	- **Change:** Unit tests for missing-field detection and no-gap scenarios.
	- **Cases:**
		- Empty `remote_hybrid_on_site` produces question.
		- Existing value suppresses question.
		- Synonym normalization prevents false positives.
	- **Edge/breaking risks:** brittle tests if question ordering is not deterministic.

- [ ] **New file:** `tests/test_profile_refiner.py`
	- **Change:** Validate answer merge semantics.
	- **Cases:**
		- Adds remote preference when missing.
		- Does not duplicate identical values.
		- Non-destructive merge with existing preferences.
	- **Edge/breaking risks:** accidental overwrite behavior.

- [ ] **File:** `tests/test_profile_schema.py`
	- **Change:** Confirm final saved schema keys are unchanged after refinement flow.
	- **Edge/breaking risks:** leakage of clarification metadata into persisted profile JSON.

- [ ] **File:** `tests/test_google_profile_builder.py`
	- **Change:** Keep generation tests separate; add regression test proving load/generation still works when clarification is introduced at state level.
	- **Edge/breaking risks:** coupling AI generation test to UI state transitions.

- [ ] **(Optional) New file:** `tests/test_state_refinement_flow.py`
	- **Change:** State-level flow test:
		- generation -> gaps -> clarification step -> refine -> profile step.
	- **Edge/breaking risks:** event-loop/background event complexity in unit tests.

### H. Documentation/Runbook

- [ ] **File:** `README.md`
	- **Change:** Update app flow docs to include clarification step and explain why additional questions appear.
	- **Edge/breaking risks:** stale docs causing confusion for expected UX.

- [ ] **File:** `profile-architecture.md`
	- **Change:** Add architecture section for “Gap Detection + Clarification + Refinement Merge”.
	- **Edge/breaking risks:** architecture drift between implementation and documentation.

---

## 3) Suggested Implementation Sequence
1. Add `clarification` models + `gap_detector` + `profile_refiner` services.
2. Extend `AppState` with clarification step and submit/merge events.
3. Build clarification UI component/page and wire into `index.py` branching.
4. Update top-nav reset behavior and any routing exports.
5. Add unit tests for detector/refiner/state flow.
6. Update README + architecture docs.

---

## 4) Non-negotiable Guardrails
- Final persisted JSON must remain `ApplicantProfile` shape exactly.
- Clarification logic must be deterministic and testable (no hidden LLM dependency for gap detection).
- Refinement merge must be non-destructive by default and idempotent for repeated submits.
- UI must ask only targeted missing-field questions, not full profile re-entry.
