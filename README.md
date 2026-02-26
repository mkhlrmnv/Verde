# Verde - AI Powered Job Applications

Reflex app for turning a CV + cover letters into an editable applicant profile, then running a job-fit helper analysis.

The app uses Google Gemini via `google-genai` and keeps all profile persistence local as JSON.

## Architecture

For a full architecture walkthrough, see [ARCHITECTURE.md](ARCHITECTURE.md).

## What it does

- Upload documents (`.pdf`, `.docx`, `.txt`)
- Treat first valid file as CV and remaining valid files as cover letters (up to 10)
- Extract and aggregate text from all valid files
- Generate a structured `ApplicantProfile` with one model call
- Detect missing preference gaps and request targeted clarification answers
- Merge clarification answers non-destructively into profile preferences
- Let you edit summary, experience, projects, skills, preferences, and languages
- Analyze profile fit against a pasted job listing (strengths, gaps, strategy snippets)
- Save profile atomically to `output/applicant_profile.json`

## Tech stack

- Python `3.12+`
- Reflex `0.8.x`
- Pydantic `2.x`
- Google GenAI SDK (`google-genai`)
- `pypdf` and `python-docx` for document extraction
- `pytest` for tests

## Setup

1. Create and activate a virtual environment:
   - `python3.12 -m venv env`
   - `source env/bin/activate`

2. Install dependencies:
   - `pip install -e .[dev]`

3. Create a `.env` file in the project root with:
   - `GOOGLE_API_KEY=your_key_here`
   - Optional: `MODEL_NAME=gemini-1.5-flash`
   - Optional: `UPLOAD_BASE_DIR=/custom/upload/temp/dir`

## Run locally

- `reflex run`

Then open the local Reflex URL shown in terminal.

## App flow

Main UX is state-driven in one screen (`/`), with compatibility routes for `/profile` and `/clarification`.

Step order:

`upload` → `processing` → (`clarification` when gaps exist) → `profile` → `job_input` → `cover_helper_processing` → `cover_helper_results`

## Profile schema

Saved JSON uses this shape:

- `summary: str`
- `skills: list[str]`
- `projects: list[{name: str, description: str}]`
- `experience: list[{role: str, company: str, duration: str, description: str}]`
- `preferences: {locations, work_types, remote_hybrid_on_site, industries, company_size}`
- `languages: list[{name: str, level: str}]`

Legacy saved files where `projects` or `experience` are string lists are accepted and normalized on load.

## Cover helper behavior

The helper is analysis-only (not full letter generation). It returns JSON with:

- `strengths`
- `weaknesses_gaps`
- `cover_letter_strategy`

Guardrails reject full-letter style output (e.g., salutations/sign-offs or oversized narrative snippets).

## Tests

Run all tests:

- `pytest`

CI also runs `pytest` on pushes to `main` via GitHub Actions.

## Notes and limits

- Missing `GOOGLE_API_KEY` surfaces an explicit user-facing error.
- Unsupported upload types are skipped with warnings.
- Maximum accepted valid uploads per run: `11` total (`1` CV + `10` cover letters).
- Combined extracted text is capped before model call to keep prompt size bounded.
