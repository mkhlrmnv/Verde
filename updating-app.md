# UI/UX Upgrade Plan — Applicant Profile Builder

Enough to proceed now:
- Split flow into separate pages (upload/processing vs applicant profile/stats).
- Improve visual layout (centered containers and cleaner section grouping).
- Use 2 dedicated upload inputs: one CV file input (max 1) and one cover-letter input (max 10).
- Trigger upload handling automatically after file selection (remove manual "Store uploads" step).
- Add "load existing saved profile" path to avoid unnecessary AI calls.

Still needs confirmation (non-blocking if defaults are used):
- Whether replacing an existing CV should overwrite previous CV immediately (answer: yes).
- Whether loading existing JSON should also populate upload history/warnings (answer: profile only).
- Whether saved JSON source remains only `output/applicant_profile.json` or supports multiple saved profiles later. (answer: Only one - latest one)

## TODO (file-by-file, implementation-focused)

### 1) Routing and page structure
- [ ] **File:** `app/app.py`
	- **Change:** Register 2 routes instead of a single page:
		- Upload/ingestion page (`/`)
		- Applicant profile + stats page (`/profile`)
	- **Logic to adjust:** Keep shared `AppState` so navigation does not lose in-memory state.
	- **Edge cases / breaking risks:** Direct visit to `/profile` without profile data should show empty-state guidance, not crash.

- [ ] **File:** `app/pages/index.py`
	- **Change:** Narrow this page to upload/ingestion responsibilities only (upload boxes, parse/generate actions, status callouts).
	- **Logic to adjust:** Remove profile editor rendering from this page and add nav CTA to `/profile`.
	- **Edge cases / breaking risks:** Buttons should remain disabled or guarded when prerequisite state is missing.

- [ ] **File:** `app/pages/profile.py` (new)
	- **Change:** Create profile/stats page with profile editor + quick applicant stats.
	- **Logic to adjust:** Display computed stats from current profile (e.g., counts for skills/projects/experience/languages).
	- **Edge cases / breaking risks:** Must render safely when profile is default/empty or loaded from disk.

- [ ] **File:** `app/pages/__init__.py`
	- **Change:** Export/import new page function(s) to keep page module structure clean.
	- **Edge cases / breaking risks:** Wrong import path can break app startup.

### 2) Upload UX redesign (two dedicated inputs + auto handling)
- [ ] **File:** `app/components/upload_panel.py`
	- **Change:** Replace single multi-upload widget with two clearly labeled cards/boxes:
		- CV upload: accepts `.pdf/.docx/.txt`, max 1 file.
		- Cover letters upload: accepts `.pdf/.docx/.txt`, max 10 files.
	- **Logic to adjust:** Wire each upload input to dedicated state handlers (`handle_cv_upload`, `handle_cover_letter_uploads`) and remove manual "Store uploads" button.
	- **Edge cases / breaking risks:**
		- Selecting >1 CV should show validation error and keep only first file or reject selection consistently.
		- Selecting >10 cover letters should not silently drop without warning.
		- Re-selecting files should replace prior selection deterministically.

- [ ] **File:** `app/state.py`
	- **Change:** Split uploaded file state into explicit buckets:
		- `uploaded_cv` (single file metadata)
		- `uploaded_cover_letters` (list, max 10)
	- **Logic to adjust:**
		- Add separate upload handlers for CV and cover letters.
		- Save files immediately when selected (auto-upload behavior).
		- Remove dependency on current `handle_upload` “manual store” step.
	- **Edge cases / breaking risks:**
		- Async double-trigger from repeated selection events.
		- Stale combined text after re-upload (must invalidate and force re-parse).
		- Shared warnings/errors must indicate CV vs cover-letter source.

### 3) Parse/generate flow changes for new upload model
- [ ] **File:** `app/state.py`
	- **Change:** Update `parse_uploaded_documents()` to consume explicit CV + cover-letter state instead of generic uploaded list.
	- **Logic to adjust:**
		- Require CV presence before parse (or define fallback explicitly).
		- Parse up to 10 cover letters and aggregate deterministically.
	- **Edge cases / breaking risks:**
		- CV extraction failure should block generation with clear message.
		- Partial cover-letter extraction failures should continue with warnings.

- [ ] **File:** `app/services/aggregate_input.py`
	- **Change:** Confirm/adjust truncation strategy to prioritize CV + most relevant cover letters under token limits.
	- **Logic to adjust:** Deterministic ordering so repeated runs with same files produce same prompt body.
	- **Edge cases / breaking risks:** Non-deterministic ordering can create confusing AI output differences.

### 4) Existing JSON reuse (avoid repeated AI calls)
- [ ] **File:** `app/state.py`
	- **Change:** Add state and action for existing output detection/loading:
		- `has_saved_profile`
		- `load_saved_profile_json()`
	- **Logic to adjust:**
		- On page load or via explicit action, check whether `output/applicant_profile.json` exists.
		- Load into `profile` using validated model path.
		- Set success/error messages clearly so user knows AI call was skipped.
	- **Edge cases / breaking risks:**
		- Corrupted JSON must show recoverable error and not poison in-memory state.
		- Loading saved profile should not accidentally clear uploaded files unless intentional.

- [ ] **File:** `app/components/upload_panel.py`
	- **Change:** Add "Use existing saved profile" action when file exists.
	- **Logic to adjust:** Show this action near generate controls to make the cost-saving path obvious.
	- **Edge cases / breaking risks:** Must be disabled/hidden when no saved JSON is present.

- [ ] **File:** `app/services/profile_store.py`
	- **Change:** Keep current `load_profile` and add helper(s) if needed (e.g., `saved_profile_exists(path)`).
	- **Logic to adjust:** Centralize path existence + load validation logic here rather than duplicating in state.
	- **Edge cases / breaking risks:** Path mismatches between save and load create false negatives in UI.

### 5) Visual polish and layout centering
- [ ] **File:** `app/pages/index.py`
	- **Change:** Center main content and constrain width consistently (`container` + centered `vstack` usage).
	- **Logic to adjust:** Keep vertical rhythm and spacing consistent across sections (upload/status/actions).
	- **Edge cases / breaking risks:** Over-constraining width can make long warnings wrap poorly.

- [ ] **File:** `app/pages/profile.py` (new)
	- **Change:** Use balanced two-section layout:
		- profile editor
		- compact stats summary card(s)
	- **Logic to adjust:** Stats should be derived from state vars, not duplicated mutable state.
	- **Edge cases / breaking risks:** Derived stats can error if profile keys are missing from invalid payloads.

- [ ] **File:** `app/components/profile_editor.py`
	- **Change:** Keep editor as reusable component on profile page only; ensure full-width fields inside centered container.
	- **Logic to adjust:** No behavioral changes beyond placement/layout unless needed for route split.
	- **Edge cases / breaking risks:** None major if handlers remain unchanged.

### 6) Navigation component for page switching
- [ ] **File:** `app/components/top_nav.py` (new)
	- **Change:** Add a minimal top navigation with links/buttons for `Upload` and `Profile` pages.
	- **Logic to adjust:** Provide stable navigation state (active page hint optional, but keep MVP simple).
	- **Edge cases / breaking risks:** Broken route links can strand users away from upload flow.

- [ ] **File:** `app/components/__init__.py`
	- **Change:** Export new nav component if this package pattern is used.
	- **Edge cases / breaking risks:** Import cycles if component imports pages directly.

### 7) Tests to protect new UX logic
- [ ] **File:** `tests/test_text_extract.py`
	- **Change:** Add coverage for CV-only and cover-letter list parse paths through updated state logic (via service-level tests where possible).
	- **Edge cases / breaking risks:** Keep tests deterministic and filesystem-local.

- [ ] **File:** `tests/test_profile_schema.py`
	- **Change:** Keep strict schema checks unchanged; add a test proving loaded JSON validates identically to generated JSON.
	- **Edge cases / breaking risks:** Corrupt fixture should assert validation error path.

- [ ] **File:** `tests/test_google_profile_builder.py`
	- **Change:** Add test ensuring load-existing-profile path bypasses generation call logic (no AI invocation).
	- **Edge cases / breaking risks:** Avoid coupling this test to network or environment keys.

### 8) Documentation updates
- [ ] **File:** `README.md`
	- **Change:** Document new two-page flow, auto-upload behavior, CV vs cover-letter limits, and “load existing saved JSON” option.
	- **Edge cases / breaking risks:** Keep instructions aligned with real routes and button labels to avoid onboarding confusion.

## Suggested execution order
1. Add new route/page skeleton (`/` and `/profile`) and nav.
2. Refactor state for separate CV/cover-letter uploads + auto upload handlers.
3. Update upload component to two boxes and remove manual store step.
4. Adjust parse/generate logic to new state structure.
5. Add saved-profile detection/load path and wire UI action.
6. Polish centering/layout on both pages.
7. Add/adjust tests for upload constraints and load-without-AI flow.
8. Update README.
