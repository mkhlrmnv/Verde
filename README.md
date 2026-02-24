# Applicant Profile Builder

A minimal Reflex app that uploads a CV and cover letters, extracts text, generates a structured applicant profile with Google AI in one shot, lets you edit it, and saves JSON to disk.

Uses the `google-genai` SDK (`google.genai`) for Gemini API calls.

## Features
- Two-page flow:
   - `/` Upload + parsing + generation
   - `/profile` Profile editor + stats
- Dedicated upload inputs:
   - CV upload (max 1)
   - Cover letter upload (max 10)
- Auto-upload on file selection (no manual "Store uploads" step)
- Parse and aggregate CV + cover letters
- One-shot profile generation with Google Gemini
- Load existing saved JSON to skip AI call when available
- Visual profile editing in UI
- Atomic save to `output/applicant_profile.json`

## Setup
1. Create environment and install dependencies:
   - `python -m venv env`
   - `source env/bin/activate`
   - `pip install -e .[dev]`
2. Create `.env` from `.env.example` and set:
   - `GOOGLE_API_KEY`
   - Optional: `MODEL_NAME` (default `gemini-1.5-flash`)

## Run
- `reflex init`
- `reflex run`

## Output
Saved JSON path (MVP default):
- `output/applicant_profile.json`

## Usage Flow
1. Open `/` and upload a CV and optional cover letters.
2. Click `Parse documents` and then `Generate profile`.
3. Optionally click `Use existing saved profile` to load `output/applicant_profile.json` directly (skips AI generation).
4. Open `/profile` to review/edit profile fields and quick stats.
5. Save changes with `Save JSON`.

## Notes
- Missing `GOOGLE_API_KEY` will surface a user-facing error when generating profile.
- Unsupported file types are skipped with warnings.
- Re-uploading CV or cover letters replaces the previous selection for that bucket and invalidates parsed combined text.
