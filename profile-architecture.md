# Applicant Profile Builder — Implementation TODO

## Scope Summary
Build a Python + Reflex app that allows an applicant to upload CV and old cover letters, parses documents into text, calls Google AI once to produce a structured applicant profile JSON, visualizes/edit profile fields in UI, and saves the final JSON in the required schema.

## Is the current instruction enough context?
Mostly yes for an MVP architecture and implementation. It is sufficient to start coding with these assumptions:
- Supported upload formats initially: `.pdf`, `.docx`, `.txt`.
- One-shot LLM extraction call is run only after upload + parse step.
- Manual edits happen in the UI before save.
- JSON output must conform to target schema exactly.

Still missing (non-blocking for MVP, but should be clarified):
- Preferred storage location for saved JSON (`/data/profiles/*.json` vs overwrite single file).
- Authentication/multi-user support (likely out-of-scope for MVP).
- File size limits and privacy retention policy.

## Exact TODO (file-by-file)

### 1) Project setup and dependencies
- [ ] **File:** `pyproject.toml`
	- **Change:** Define project metadata and dependencies: `reflex`, `google-generativeai` (or current Google GenAI SDK), `pydantic`, `python-dotenv`, `pypdf`, `python-docx`.
	- **Edge cases / breaking risks:** SDK naming/version drift for Google AI package; lock to tested versions to avoid API breakage.

- [ ] **File:** `.env.example`
	- **Change:** Add `GOOGLE_API_KEY=`, `MODEL_NAME=` (default gemini model), optional `APP_ENV=`.
	- **Edge cases / breaking risks:** Missing API key should not crash app startup; surface user-facing error in UI.

- [ ] **File:** `.gitignore`
	- **Change:** Ensure `.env`, upload temp files, generated JSON output folder, and Reflex build artifacts are ignored.
	- **Edge cases / breaking risks:** Accidentally committing personal CV/letters or API keys.

### 2) Data contracts and validation
- [ ] **File:** `app/models/profile.py`
	- **Change:** Create Pydantic models for `LanguageEntry`, `Preferences`, `ApplicantProfile` with exact output schema:
		- `summary`, `skills`, `projects`, `experience`, `preferences`, `languages`.
	- **Edge cases / breaking risks:** LLM returns invalid shapes/types; strict validation errors must be handled and repaired/fallback.

- [ ] **File:** `app/models/parsing.py`
	- **Change:** Define parser result model (`source_files`, `combined_text`, `warnings`).
	- **Edge cases / breaking risks:** Empty extracted text from scanned PDFs; warnings must be propagated to UI.

### 3) Document ingestion and text extraction
- [ ] **File:** `app/services/file_storage.py`
	- **Change:** Implement upload persistence helpers (safe filename normalization, per-session temp folder creation, cleanup hooks).
	- **Edge cases / breaking risks:** Path traversal via crafted filename; enforce basename + allowed extensions.

- [ ] **File:** `app/services/text_extract.py`
	- **Change:** Implement extraction functions:
		- `extract_text_from_pdf(path)`
		- `extract_text_from_docx(path)`
		- `extract_text_from_txt(path)`
		- `extract_text_from_file(path)` dispatcher
	- **Edge cases / breaking risks:** Corrupted files, encrypted PDFs, zero-text pages, unsupported encodings.

- [ ] **File:** `app/services/aggregate_input.py`
	- **Change:** Merge extracted CV + cover letter text into one prompt-safe corpus with section labels and truncation strategy.
	- **Edge cases / breaking risks:** Token overflow for long history; implement deterministic truncation (keep latest letter + CV core sections).

### 4) Google AI one-shot profile generation
- [ ] **File:** `app/services/google_profile_builder.py`
	- **Change:**
		- Initialize Google AI client from env.
		- Implement `generate_profile_json_once(combined_text) -> ApplicantProfile`.
		- Use strict prompt instructing exact JSON schema and no extra keys.
		- Parse model response and validate with Pydantic.
	- **Edge cases / breaking risks:** Non-JSON response, partial JSON, hallucinated keys, rate-limit/network failure.

- [ ] **File:** `app/prompts/profile_prompt.txt`
	- **Change:** Store extraction prompt template with explicit schema and normalization rules (dedupe skills, concise summary, language levels as strings).
	- **Edge cases / breaking risks:** Prompt drift can break downstream parser if schema instructions are loosened.

### 5) Reflex state and business flow
- [ ] **File:** `app/state.py`
	- **Change:** Create `AppState` with fields:
		- uploaded files metadata
		- extraction warnings/errors
		- generated `ApplicantProfile` state
		- edit mode + save status
	- **Functions to implement:**
		- `handle_upload(files)`
		- `parse_uploaded_documents()`
		- `build_profile_once()`
		- profile update handlers (`update_summary`, `add_skill`, `remove_skill`, etc.)
		- `save_profile_json()`
	- **Edge cases / breaking risks:** Async state race (user clicks generate twice), stale state after re-upload, invalid manual edits.

### 6) Reflex UI (minimal, editable visual profile)
- [ ] **File:** `app/pages/index.py`
	- **Change:** Compose single-page flow:
		- Upload section (CV + multiple cover letters)
		- Parse + Generate profile button
		- Visual profile editor (summary textarea, editable lists for skills/projects/experience, preferences chips/inputs, languages table)
		- Save JSON action + success/error banners
	- **Edge cases / breaking risks:** Large list editing UX complexity; keep MVP controls simple and deterministic.

- [ ] **File:** `app/components/profile_editor.py`
	- **Change:** Encapsulate profile edit components to avoid bloated page file.
	- **Edge cases / breaking risks:** Field binding mismatches (editing wrong index in list updates).

- [ ] **File:** `app/components/upload_panel.py`
	- **Change:** Upload widget + selected files preview + validation feedback.
	- **Edge cases / breaking risks:** Unsupported file types should be blocked before processing.

### 7) JSON persistence and export
- [ ] **File:** `app/services/profile_store.py`
	- **Change:** Implement `save_profile(profile: ApplicantProfile, path: str)` and optional `load_profile(path)`.
	- **Output target:** `output/applicant_profile.json` (default MVP path).
	- **Edge cases / breaking risks:** Partial writes on interruption; write atomically via temp file + rename.

- [ ] **File:** `output/.gitkeep`
	- **Change:** Ensure output directory exists in repository structure without committing private profile data.
	- **Edge cases / breaking risks:** Missing folder causes save failures on first run.

### 8) App entrypoint and wiring
- [ ] **File:** `app/app.py`
	- **Change:** Register Reflex app and route(s), connect `AppState` and index page.
	- **Edge cases / breaking risks:** Misconfigured state import paths causing runtime startup errors.

- [ ] **File:** `rxconfig.py`
	- **Change:** Reflex config, app name, environment flags.
	- **Edge cases / breaking risks:** Wrong config can break `reflex run` boot.

### 9) Tests and quality gates
- [ ] **File:** `tests/test_profile_schema.py`
	- **Change:** Validate profile schema serialization exactly matches required keys.
	- **Edge cases / breaking risks:** Optional fields sneaking in and breaking consumer expectations.

- [ ] **File:** `tests/test_text_extract.py`
	- **Change:** Unit tests for file-type dispatch and graceful failure cases.
	- **Edge cases / breaking risks:** Platform-specific parsing behavior.

- [ ] **File:** `tests/test_google_profile_builder.py`
	- **Change:** Mock Google AI response; verify strict JSON parse + validation pipeline.
	- **Edge cases / breaking risks:** Flaky tests if real network is used; keep fully mocked.

### 10) Documentation and runbook
- [ ] **File:** `README.md`
	- **Change:** Document setup, env vars, supported file formats, run steps (`reflex run`), and where JSON output is saved.
	- **Edge cases / breaking risks:** Users running without API key or with unsupported files.

## Required output schema (must remain exact)
Final saved JSON should follow this structure:

{
	"summary": "...",
	"skills": [...],
	"projects": [...],
	"experience": [...],
	"preferences": {
		"locations": ["Finland", "Nordics"],
		"work_types": ["summer internship", "thesis", "part-time"],
		"remote_hybrid_on_site": ["on-site", "hybrid"],
		"industries": ["robotics", "automation", "ML"],
		"company_size": ["startup", "mid-size", "large corp"]
	},
	"languages": [
		{ "name": "English", "level": "C1" },
		{ "name": "Finnish", "level": "A2/B1" }
	]
}

## Suggested execution order
1. Setup dependencies + env + models.
2. Implement file parsing pipeline.
3. Implement Google AI one-shot JSON generation + validation.
4. Build Reflex UI upload + editor.
5. Implement save/export flow.
6. Add tests and README.
