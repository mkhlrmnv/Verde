# Applicant Profile Builder Architecture

## Purpose

This document describes the implemented architecture of the Applicant Profile Builder application.

The app is a Reflex-based, state-driven workflow that:

1. Ingests CV and cover-letter files.
2. Extracts text and generates a structured applicant profile with Google Gemini.
3. Detects preference gaps and asks targeted clarification questions.
4. Merges clarification answers into profile data.
5. Supports profile editing and JSON export.
6. Runs a job-fit analysis helper against a pasted job listing.

## System Overview

- **UI framework:** Reflex
- **State orchestration:** `app/state.py` (`AppState`)
- **Domain validation:** Pydantic models in `app/models/`
- **AI integration:** `google-genai` via service layer in `app/services/`
- **Persistence:** local JSON file at `output/applicant_profile.json`
- **Tests:** `pytest` suite under `tests/`

## Runtime Flow (State Machine)

`AppState.step` is the source of truth for screen transitions:

`upload` → `processing` → (`clarification` if gaps, else `profile`) → `job_input` → `cover_helper_processing` → `cover_helper_results`

### Step details

- **upload**
  - User uploads files (`.pdf`, `.docx`, `.txt`).
  - First valid file is treated as CV; next valid files as cover letters.
- **processing**
  - App extracts text from uploaded files.
  - Combined text is aggregated and bounded in size.
  - Profile generation runs via Gemini.
  - Gap detection runs and decides whether clarification is needed.
- **clarification**
  - Targeted questions are rendered for missing preference fields.
  - Answers are validated and merged non-destructively.
- **profile**
  - User edits profile sections (summary, experience, projects, skills, preferences, languages).
  - Profile can be exported to JSON.
- **job_input**
  - User pastes a target job listing.
- **cover_helper_processing**
  - Helper analysis runs in background.
- **cover_helper_results**
  - App shows structured strengths, weaknesses/gaps, and strategy snippets.

## Layered Architecture

### 1) Presentation Layer

- `app/pages/index.py`
  - Primary state-driven page renderer.
- `app/pages/*.py`
  - View-specific content blocks (`clarification`, `job_input`, `cover_helper_results`, etc.).
- `app/components/*.py`
  - Reusable UI components (`upload_panel`, `profile_editor`, `clarification_form`, `top_nav`).

### 2) State & Orchestration Layer

- `app/state.py`
  - Owns UI state, transitions, and user-facing messages.
  - Coordinates background operations using `@rx.event(background=True)`.
  - Calls pure services for extraction, generation, detection, and merge.

### 3) Domain Model Layer

- `app/models/profile.py`
  - `ApplicantProfile` contract and legacy-shape normalization.
- `app/models/clarification.py`
  - Gap question and clarification answer contracts.
- `app/models/cover_helper.py`
  - Structured helper-analysis output contract.

### 4) Service Layer

- `app/services/file_storage.py`
  - Upload validation, filename normalization, temp file storage.
- `app/services/text_extract.py`
  - `.pdf`, `.docx`, `.txt` extraction.
- `app/services/aggregate_input.py`
  - Aggregates extracted text with max-size bound.
- `app/services/google_profile_builder.py`
  - Profile generation and strict response normalization/validation.
- `app/services/gap_detector.py`
  - Deterministic missing-preference detection.
- `app/services/profile_refiner.py`
  - Non-destructive merge of clarification answers.
- `app/services/cover_letter_helper.py`
  - Job-fit helper analysis with strict JSON and output guardrails.
- `app/services/profile_store.py`
  - Atomic save/load of profile JSON.

## Data Contracts

### Applicant profile

`ApplicantProfile` fields:

- `summary: str`
- `skills: list[str]`
- `projects: list[{name, description}]`
- `experience: list[{role, company, duration, description}]`
- `preferences: {locations, work_types, remote_hybrid_on_site, industries, company_size}`
- `languages: list[{name, level}]`

### Clarification model

Gap detector emits `GapQuestion` items with:

- `field_key`
- `label`
- `prompt`
- `input_type` (`multi_select` or `text_list`)
- `required`
- `options`

### Cover helper output

Helper returns strict JSON sections:

- `strengths`
- `weaknesses_gaps`
- `cover_letter_strategy`

## Reliability and Guardrails

- Input file type allowlist (`.pdf`, `.docx`, `.txt`).
- Upload caps (`1` CV + `10` cover letters).
- Deterministic, rule-based gap detection (no extra model calls).
- Clarification merge is non-destructive and deduplicated.
- Cover helper enforces analysis-only output and rejects letter-like responses.
- JSON persistence uses atomic replace to avoid partial writes.

## Environment and Configuration

- Required env var: `GOOGLE_API_KEY`
- Optional env vars:
  - `MODEL_NAME` (defaults to `gemini-1.5-flash`)
  - `UPLOAD_BASE_DIR` (custom temp upload location)

## Testing Strategy

`tests/` includes coverage for:

- Profile schema normalization and validation.
- Text extraction behavior.
- Gap detection and profile refinement logic.
- Cover helper parsing and guardrails.
- AppState flow checks for profile and helper transitions.

## Entry Points

- App bootstrap: `app/app.py`
- Main route: `/` (state-driven view orchestration)
- Compatibility routes: `/profile`, `/clarification`

## Non-Goals

- No remote database persistence (local JSON only).
- No full cover-letter generation in helper flow (analysis-only by design).
