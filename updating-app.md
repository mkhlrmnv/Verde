# Reflex Update TODO — Match React Design in `src`

## Design Gap Summary
- React target is a single-screen step state (`upload` → `processing` → `profile`) with animated transitions, while Reflex is split across 3 routes and uses generic cards/navigation.
- React profile schema uses structured objects for `projects` and `experience`; current Reflex schema/editor treat both as simple string lists.
- React visual system depends on precise spacing, rounded containers, chip/tag editing, icon-led sections, sticky header, and a light-gray canvas that are not currently mirrored.

## File-by-File TODO

- [ ] **File:** `app/models/profile.py`  
	**Change:** Convert `ApplicantProfile.projects` and `ApplicantProfile.experience` from `list[str]` to object arrays matching React (`{name, description}` and `{role, company, duration, description}`), with dedicated nested models.  
	**Watch for:** Existing saved JSON in old shape will fail strict validation; add backward-compatible migration on load.

- [ ] **File:** `app/prompts/profile_prompt.txt`  
	**Change:** Update schema instructions so LLM returns object-based `projects`/`experience` with exact keys used by React.  
	**Watch for:** Model may still return legacy list format; downstream parser must normalize.

- [ ] **File:** `app/services/google_profile_builder.py`  
	**Change:** Add normalization/coercion layer before Pydantic validation to repair mixed/legacy model outputs into the new schema.  
	**Watch for:** Missing keys, wrong types, fenced JSON, extra keys, partial objects.

- [ ] **File:** `app/state.py`  
	**Change:** Replace route-driven UX with a `step` state (`upload|processing|profile`) and refactor all edit handlers for structured project/experience entries (add/update/remove by field).  
	**Watch for:** Double-submit while processing, stale file state after reset, index safety during list mutations.

- [ ] **File:** `app/pages/index.py`  
	**Change:** Rebuild as the single app shell (sticky header, conditional step content, inline error banner), matching React page flow and hierarchy.  
	**Watch for:** Preserve `check_saved_profile_exists` behavior without exposing non-React controls.

- [ ] **File:** `app/pages/loading.py`  
	**Change:** Decommission route usage; move rotating loading messages + spinner presentation into step-based processing UI (or keep only as reusable component).  
	**Watch for:** Avoid duplicate timers/effects if the processing component is re-mounted often.

- [ ] **File:** `app/pages/profile.py`  
	**Change:** Decommission route-centric profile/stat layout; move to React-style two-column profile editing section under `step='profile'`.  
	**Watch for:** Keep save/load messaging and actions working after layout relocation.

- [ ] **File:** `app/components/top_nav.py`  
	**Change:** Replace Upload/Profile navigation buttons with React-style brand header (logo tile + title + conditional `Start Over`).  
	**Watch for:** `Start Over` must atomically reset files, profile, warnings, messages, and step.

- [ ] **File:** `app/components/upload_panel.py`  
	**Change:** Redesign as single drag/drop uploader with selected-files list and React-equivalent CTA hierarchy/placement.  
	**Watch for:** Backend may still require CV vs cover-letter distinction; preserve logic while presenting unified UX.

- [ ] **File:** `app/components/profile_editor.py`  
	**Change:** Rebuild sections to match React cards: summary, experience cards, project cards, skills chips, preferences chips-by-category, language rows, export CTA.  
	**Watch for:** Enter-to-add chip behavior, delete affordances, controlled input bindings for nested fields.

- [ ] **File:** `app/app.py`  
	**Change:** Simplify routing to one primary page for UI parity; keep compatibility redirects only where needed.  
	**Watch for:** Existing bookmarks to `/loading` or `/profile` should redirect safely to `/`.

- [ ] **File:** `rxconfig.py`  
	**Change:** Add/adjust global theme settings (font family, neutral background, text tones) to mirror React baseline.  
	**Watch for:** Theme changes can unintentionally affect non-target components.

- [ ] **File:** `tests/test_profile_schema.py`  
	**Change:** Update schema tests for structured `projects`/`experience` objects and exact-key validation.  
	**Watch for:** Legacy fixtures and snapshots need migration.

- [ ] **File:** `tests/test_google_profile_builder.py`  
	**Change:** Add tests covering normalization from legacy/mixed model outputs to new strict schema.  
	**Watch for:** Keep tests fully mocked to avoid flaky network dependence.

- [ ] **File:** `README.md`  
	**Change:** Update docs to single-page step UX and new object schema for `projects`/`experience`.  
	**Watch for:** Add migration note for old `output/applicant_profile.json` format.

## Recommended Execution Order
1. Schema + prompt + generation normalization (`app/models/profile.py`, `app/prompts/profile_prompt.txt`, `app/services/google_profile_builder.py`).
2. State flow conversion to step-based UI (`app/state.py`).
3. UI parity rebuild (`app/pages/index.py`, `app/components/*`, deprecate route pages).
4. App wiring + theming (`app/app.py`, `rxconfig.py`).
5. Tests + docs (`tests/*`, `README.md`).
