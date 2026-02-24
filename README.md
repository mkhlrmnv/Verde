# Applicant Profile Builder

A Reflex app that uploads a CV and cover letters, extracts text, generates a structured applicant profile with Google AI in one shot, lets you edit it in a React-style editor, and saves JSON to disk.

Uses the `google-genai` SDK (`google.genai`) for Gemini API calls.

## Features
- Single-page step flow:
   - `upload` → `processing` → `profile`
- Sticky brand header with conditional `Start Over`
- Unified uploader with selected-file list
- First valid file is treated as CV, remaining files as cover letters (max 10)
- Parse and aggregate CV + cover letters
- One-shot profile generation with Google Gemini
- Load existing saved JSON to skip AI call when available
- React-style profile editing cards (summary, experience, projects, skills chips, preferences chips, languages)
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

Profile schema keys:
- `summary`: string
- `skills`: string[]
- `projects`: `{ name: string, description: string }[]`
- `experience`: `{ role: string, company: string, duration: string, description: string }[]`
- `preferences`: `{ locations, work_types, remote_hybrid_on_site, industries, company_size }`
- `languages`: `{ name: string, level: string }[]`

## Usage Flow
1. Open `/` and upload one or more files.
2. Click `Generate Profile`.
3. Wait in the processing step while extraction + generation runs.
4. Review/edit the profile in the profile step.
5. Click `Export JSON` to save updates.

## Notes
- Missing `GOOGLE_API_KEY` will surface a user-facing error when generating profile.
- Unsupported file types are skipped with warnings.
- Uploading files resets parsed artifacts and invalidates previous combined text.
- Legacy `output/applicant_profile.json` files with `projects`/`experience` as string arrays are auto-migrated on load.
