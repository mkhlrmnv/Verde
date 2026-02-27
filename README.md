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

## Container (production-oriented)

This repository includes a multi-stage `Dockerfile` with:

- Python `3.12-slim` base images
- non-root runtime user
- reduced build context via `.dockerignore`
- container healthcheck
- runtime env-based configuration (no hardcoded secrets)

### Build image locally

```bash
docker build -t jae:local .
```

### Recommended run with Docker Compose

```bash
docker compose up --build
```

This uses `docker-compose.yml` and publishes both required ports (`3000` and `8000`).

### Run container locally

```bash
docker run --rm --env-file .env -p 3000:3000 -p 8000:8000 jae:local
```

This passes all variables from your local `.env` file to the container at runtime.
The `.env` file is not copied into the image.

Optional runtime variables:

- `PORT` (default `3000`)
- `BACKEND_PORT` (default `8000`)
- `GOOGLE_API_KEY` (required for model-backed features)
- `MODEL_NAME` (optional)
- `UPLOAD_BASE_DIR` (optional)

## CI image publishing to Docker Hub

Existing GitHub Actions workflow (`.github/workflows/pytest.yml`) now:

- runs on push to `main`
- supports manual trigger (`workflow_dispatch`)
- runs tests first (`pytest`)
- builds and pushes Docker image only after tests pass
- publishes tags:
   - `latest`
   - commit SHA (`${GITHUB_SHA}`)

Image naming format:

- `<dockerhub-namespace>/<repo-or-app>:<tag>`

Where image name defaults to GitHub repo name and can be overridden.

### Required GitHub configuration

Repository **Variables**:

- `DOCKERHUB_NAMESPACE` (optional, defaults to `DOCKERHUB_USERNAME`)
- `APP_IMAGE_NAME` (optional override)

Repository **Secrets**:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (Docker Hub access token)

After setup, every push to `main` runs tests and pushes the container image to Docker Hub.

### Pull and run the published image

```bash
docker pull mkhlrmnv/verde:latest
docker run --rm --env-file .env -p 3000:3000 -p 8000:8000 mkhlrmnv/verde:latest
```

Template:

```bash
docker pull <dockerhub-namespace>/<repo-or-app>:latest
docker run --rm --env-file .env -p 3000:3000 -p 8000:8000 <dockerhub-namespace>/<repo-or-app>:latest
```

## Notes and limits

- Missing `GOOGLE_API_KEY` surfaces an explicit user-facing error.
- Unsupported upload types are skipped with warnings.
- Maximum accepted valid uploads per run: `11` total (`1` CV + `10` cover letters).
- Combined extracted text is capped before model call to keep prompt size bounded.
