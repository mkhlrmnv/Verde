# Applicant Profile Builder — Architecture

## Scope Summary
Build a Python + Reflex app that allows an applicant to upload CV and cover letters, parses documents into text, calls Google AI once to produce an initial structured applicant profile JSON, runs deterministic gap detection, requests targeted clarifications when preference gaps are found, merges clarifications into the profile, then visualizes/edits and saves the final JSON.

## Current End-to-End Pipeline
1. Upload CV + optional cover letters.
2. Extract and aggregate document text.
3. Generate initial profile with Google AI.
4. Detect missing preference gaps deterministically.
5. If gaps exist, show clarification page with targeted questions.
6. Merge clarification answers into profile (non-destructive, deduplicated).
7. Show final profile editor and export JSON.

## Clarification and Refinement Components
- `app/models/clarification.py`
	- `GapQuestion`, `GapDetectionResult`, and `ClarificationAnswerSet` contracts.
- `app/services/gap_detector.py`
	- Deterministic rule-based missing-field detection for:
		- `preferences.remote_hybrid_on_site`
		- `preferences.work_types`
		- optional `preferences.locations`, `preferences.industries`, `preferences.company_size`
- `app/services/profile_refiner.py`
	- Non-destructive merge of clarification answers into profile preferences.
	- Canonicalization and case-insensitive dedupe for stable output.

## State Machine
- `AppState.step` flow:
	- `upload` → `processing` → (`clarification` if gaps else `profile`) → `profile`
- Added state:
	- `gap_questions`, `clarification_answers`, `is_refining`, `has_gaps`
- Added events:
	- `set_clarification_text_answer`
	- `toggle_clarification_option`
	- `submit_clarifications_and_refine`
	- `skip_clarifications`

## Deterministic gap detection policy
- Gaps are detected only from normalized `ApplicantProfile.preferences` values.
- Detection is rule-based and deterministic; no model calls occur during this phase.
- Targeted questions are generated only for fields currently missing values.
- Required questions:
	- `preferences.remote_hybrid_on_site`
	- `preferences.work_types`
- Optional question candidates (asked only when empty):
	- `preferences.locations`
	- `preferences.industries`
	- `preferences.company_size`

## Clarification UX contract
- Clarification UI is rendered via `app/components/clarification_form.py` and shown when `AppState.step == "clarification"`.
- Questions are specific to missing fields and include either:
	- `multi_select` options for canonical categories, or
	- `text_list` free-form lists (comma/newline separated).
- Required questions are visually labeled and validated before refinement submit.
- Users may skip clarification and proceed directly to profile editing.

## Merge and idempotency rules
- Clarification answers are merged through `app/services/profile_refiner.py`.
- Merge is non-destructive:
	- Existing profile values are preserved.
	- New clarification values are appended after canonicalization.
- Canonicalization currently normalizes work mode and work type aliases.
- Case-insensitive de-duplication preserves first-seen ordering.
- Applying the same answer set repeatedly produces identical output (idempotent behavior).

## Routing and page integration
- Main flow is orchestrated at `/` in `app/pages/index.py` using `AppState.step`.
- Dedicated pages exist for direct navigation compatibility:
	- `/profile`
	- `/clarification`
- `app/state.py` controls transitions:
	- generation success with gaps → `clarification`
	- clarification submit/skip → `profile`

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
