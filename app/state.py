from __future__ import annotations

from pathlib import Path
from datetime import datetime
import traceback
from typing import Any, Literal
import uuid

import reflex as rx
from pydantic import ValidationError
from reflex.utils.misc import run_in_thread

from app.models.clarification import ClarificationAnswerSet, GapQuestionData
from app.models.cover_helper import CoverHelperAnalysis
from app.models.profile import ApplicantProfile
from app.services.aggregate_input import aggregate_profile_input
from app.services.cover_letter_helper import (
    CoverHelperGenerationError,
    generate_cover_helper_analysis_once,
)
from app.services.file_storage import is_supported_extension, save_upload_bytes
from app.services.gap_detector import detect_profile_gaps
from app.services.google_profile_builder import ProfileGenerationError, generate_profile_json_once
from app.services.profile_refiner import merge_clarifications_into_profile
from app.services.profile_store import load_profile, save_profile, saved_profile_exists
from app.services.text_extract import TextExtractionError, extract_text_from_file


MAX_COVER_LETTERS = 10
MAX_TOTAL_UPLOADS = MAX_COVER_LETTERS + 1
Step = Literal[
    "upload",
    "processing",
    "clarification",
    "profile",
    "job_input",
    "cover_helper_processing",
    "cover_helper_results",
]


class AppState(rx.State):
    session_id: str = uuid.uuid4().hex
    step: Step = "upload"

    uploaded_cv: dict[str, str] = {}
    uploaded_cover_letters: list[dict[str, str]] = []

    combined_text: str = ""
    extraction_warnings: list[str] = []
    error_message: str = ""
    success_message: str = ""

    is_processing: bool = False
    is_saving: bool = False
    is_refining: bool = False
    has_saved_profile: bool = False
    has_gaps: bool = False

    profile: dict[str, Any] = ApplicantProfile().model_dump()
    gap_questions: list[GapQuestionData] = []
    clarification_answers: dict[str, list[str]] = {}

    job_listing_text: str = ""
    is_generating_cover_helper: bool = False
    cover_helper_error: str = ""
    cover_helper_result: dict[str, list[dict[str, str]]] = {
        "strengths": [],
        "weaknesses_gaps": [],
        "cover_letter_strategy": [],
    }
    cover_helper_generated_at: str = ""

    new_skill: str = ""
    new_project_name: str = ""
    new_project_description: str = ""
    new_experience_role: str = ""
    new_experience_company: str = ""
    new_experience_duration: str = ""
    new_experience_description: str = ""
    new_language_name: str = ""
    new_language_level: str = ""
    new_pref_location: str = ""
    new_pref_work_type: str = ""
    new_pref_mode: str = ""
    new_pref_industry: str = ""
    new_pref_company_size: str = ""

    @rx.var
    def has_files(self) -> bool:
        return bool(self.uploaded_cv) or len(self.uploaded_cover_letters) > 0

    @rx.var
    def has_cv(self) -> bool:
        return bool(self.uploaded_cv)

    @rx.var
    def cover_letter_count(self) -> int:
        return len(self.uploaded_cover_letters)

    @rx.var
    def selected_files(self) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        if self.uploaded_cv:
            files.append({"kind": "CV", "name": self.uploaded_cv.get("name", "")})
        for item in self.uploaded_cover_letters:
            files.append({"kind": "Cover Letter", "name": item.get("name", "")})
        return files

    @rx.var
    def has_profile(self) -> bool:
        return bool(self.profile)

    @rx.var
    def has_meaningful_profile(self) -> bool:
        return any(
            [
                str(self.profile.get("summary", "")).strip(),
                len(self.profile.get("skills", [])) > 0,
                len(self.profile.get("projects", [])) > 0,
                len(self.profile.get("experience", [])) > 0,
                len(self.profile.get("languages", [])) > 0,
            ]
        )

    @rx.var
    def has_warnings(self) -> bool:
        return len(self.extraction_warnings) > 0

    @rx.var
    def is_upload_step(self) -> bool:
        return self.step == "upload"

    @rx.var
    def is_processing_step(self) -> bool:
        return self.step == "processing"

    @rx.var
    def is_profile_step(self) -> bool:
        return self.step == "profile"

    @rx.var
    def is_clarification_step(self) -> bool:
        return self.step == "clarification"

    @rx.var
    def is_job_input_step(self) -> bool:
        return self.step == "job_input"

    @rx.var
    def is_cover_helper_results_step(self) -> bool:
        return self.step == "cover_helper_results"

    @rx.var
    def is_cover_helper_processing_step(self) -> bool:
        return self.step == "cover_helper_processing"

    @rx.var
    def has_job_listing_text(self) -> bool:
        return bool(self.job_listing_text.strip())

    @rx.var
    def has_cover_helper_result(self) -> bool:
        strengths = self.cover_helper_result.get("strengths", [])
        weaknesses = self.cover_helper_result.get("weaknesses_gaps", [])
        strategy = self.cover_helper_result.get("cover_letter_strategy", [])
        return any([len(strengths) > 0, len(weaknesses) > 0, len(strategy) > 0])

    @rx.var
    def has_gap_questions(self) -> bool:
        return len(self.gap_questions) > 0

    @rx.var
    def summary(self) -> str:
        return str(self.profile.get("summary", ""))

    @rx.var
    def skills(self) -> list[str]:
        return list(self.profile.get("skills", []))

    @rx.var
    def projects(self) -> list[dict[str, str]]:
        return list(self.profile.get("projects", []))

    @rx.var
    def experience(self) -> list[dict[str, str]]:
        return list(self.profile.get("experience", []))

    @rx.var
    def languages(self) -> list[dict[str, str]]:
        return list(self.profile.get("languages", []))

    @rx.var
    def preference_locations(self) -> list[str]:
        return list(self.profile.get("preferences", {}).get("locations", []))

    @rx.var
    def preference_work_types(self) -> list[str]:
        return list(self.profile.get("preferences", {}).get("work_types", []))

    @rx.var
    def preference_modes(self) -> list[str]:
        return list(self.profile.get("preferences", {}).get("remote_hybrid_on_site", []))

    @rx.var
    def preference_industries(self) -> list[str]:
        return list(self.profile.get("preferences", {}).get("industries", []))

    @rx.var
    def preference_company_sizes(self) -> list[str]:
        return list(self.profile.get("preferences", {}).get("company_size", []))

    @rx.var
    def skills_count(self) -> int:
        return len(self.skills)

    @rx.var
    def projects_count(self) -> int:
        return len(self.projects)

    @rx.var
    def experience_count(self) -> int:
        return len(self.experience)

    @rx.var
    def languages_count(self) -> int:
        return len(self.languages)

    def _clear_messages(self) -> None:
        self.error_message = ""
        self.success_message = ""

    def _debug(self, message: str) -> None:
        print(f"[AppState][session={self.session_id}] {message}")

    def _set_profile(self, profile: dict[str, Any]) -> None:
        validated = ApplicantProfile.model_validate(profile)
        self.profile = validated.model_dump()

    def _reset_parsed_artifacts(self) -> None:
        self.combined_text = ""
        self.extraction_warnings = []

    def _reset_draft_inputs(self) -> None:
        self.new_skill = ""
        self.new_project_name = ""
        self.new_project_description = ""
        self.new_experience_role = ""
        self.new_experience_company = ""
        self.new_experience_duration = ""
        self.new_experience_description = ""
        self.new_language_name = ""
        self.new_language_level = ""
        self.new_pref_location = ""
        self.new_pref_work_type = ""
        self.new_pref_mode = ""
        self.new_pref_industry = ""
        self.new_pref_company_size = ""

    def _reset_refinement_state(self) -> None:
        self.is_refining = False
        self.has_gaps = False
        self.gap_questions = []
        self.clarification_answers = {}

    def _reset_cover_helper_result_state(self) -> None:
        self.is_generating_cover_helper = False
        self.cover_helper_error = ""
        self.cover_helper_generated_at = ""
        self.cover_helper_result = {
            "strengths": [],
            "weaknesses_gaps": [],
            "cover_letter_strategy": [],
        }

    def clear_cover_helper_state(self) -> None:
        self.job_listing_text = ""
        self._reset_cover_helper_result_state()

    def check_saved_profile_exists(self) -> None:
        output_path = Path("output") / "applicant_profile.json"
        self.has_saved_profile = saved_profile_exists(str(output_path))

    def reset_app(self) -> None:
        self.session_id = uuid.uuid4().hex
        self.step = "upload"
        self.uploaded_cv = {}
        self.uploaded_cover_letters = []
        self._reset_parsed_artifacts()
        self._clear_messages()
        self._reset_draft_inputs()
        self.is_processing = False
        self.is_saving = False
        self._reset_refinement_state()
        self.clear_cover_helper_state()
        self.profile = ApplicantProfile().model_dump()

    def set_job_listing_text(self, value: str) -> None:
        self.job_listing_text = value

    def move_to_job_listing_input(self) -> None:
        self._clear_messages()
        if not self.has_meaningful_profile:
            self.error_message = "Generate or complete your profile before analyzing against a job listing."
            self.step = "profile"
            return

        self._reset_cover_helper_result_state()
        self.step = "job_input"

    def back_to_profile_from_job_input(self) -> None:
        self._clear_messages()
        self.step = "profile"

    def back_to_job_input(self) -> None:
        self._clear_messages()
        self.step = "job_input"

    @rx.event(background=True)
    async def generate_cover_helper_analysis(self) -> None:
        async with self:
            if self.is_generating_cover_helper:
                return

            self._clear_messages()
            self.cover_helper_error = ""

            if not self.job_listing_text.strip():
                self.cover_helper_error = "Paste a job listing before running analysis."
                self.step = "job_input"
                return

            try:
                profile_model = ApplicantProfile.model_validate(self.profile)
            except ValidationError as exc:
                self.cover_helper_error = f"Profile is invalid and cannot be analyzed: {exc}"
                self.step = "profile"
                return

            listing = self.job_listing_text
            self.is_generating_cover_helper = True
            self.step = "cover_helper_processing"

        try:
            analysis = await run_in_thread(
                lambda: generate_cover_helper_analysis_once(profile=profile_model, job_listing=listing)
            )

            normalized = CoverHelperAnalysis.model_validate(analysis.model_dump())

            async with self:
                self.cover_helper_result = {
                    "strengths": [item.model_dump() for item in normalized.strengths],
                    "weaknesses_gaps": [item.model_dump() for item in normalized.weaknesses_gaps],
                    "cover_letter_strategy": [item.model_dump() for item in normalized.cover_letter_strategy],
                }
                self.cover_helper_generated_at = datetime.now().isoformat(timespec="seconds")
                self.cover_helper_error = ""
                self.step = "cover_helper_results"
                self.is_generating_cover_helper = False
        except CoverHelperGenerationError as exc:
            async with self:
                self.cover_helper_error = str(exc)
                self.step = "job_input"
                self.is_generating_cover_helper = False
        except ValidationError as exc:
            async with self:
                self.cover_helper_error = f"Invalid analysis response: {exc}"
                self.step = "job_input"
                self.is_generating_cover_helper = False
        except Exception as exc:
            async with self:
                self.cover_helper_error = f"Failed to generate cover helper analysis: {exc}"
                self.step = "job_input"
                self.is_generating_cover_helper = False
            self._debug(f"Cover helper generation exception: {exc}")
            self._debug(traceback.format_exc())

    async def handle_document_uploads(self, files: list[rx.UploadFile]) -> None:
        self._debug("handle_document_uploads called")
        try:
            self._clear_messages()
            self._reset_parsed_artifacts()

            if not files:
                self.error_message = "No files selected."
                return

            valid_uploads = [f for f in files if is_supported_extension(f.filename or "")]
            if not valid_uploads:
                self.error_message = "No supported files uploaded. Allowed formats: .pdf, .docx, .txt"
                return

            if len(valid_uploads) > MAX_TOTAL_UPLOADS:
                valid_uploads = valid_uploads[:MAX_TOTAL_UPLOADS]
                self.extraction_warnings.append(
                    f"Only the first {MAX_TOTAL_UPLOADS} supported files were kept (1 CV + {MAX_COVER_LETTERS} cover letters)."
                )

            if len(valid_uploads) < len(files):
                self.extraction_warnings.append("Some unsupported files were skipped.")

            stored_cv: dict[str, str] = {}
            stored_letters: list[dict[str, str]] = []

            for idx, upload in enumerate(valid_uploads):
                filename = upload.filename or ("uploaded_cv.txt" if idx == 0 else "cover_letter.txt")
                data = await upload.read()
                path = save_upload_bytes(file_bytes=data, filename=filename, session_id=self.session_id)

                if idx == 0:
                    stored_cv = {"name": filename, "path": str(path)}
                else:
                    stored_letters.append({"name": filename, "path": str(path)})

            if not stored_cv:
                self.error_message = "Upload at least one valid CV file."
                return

            self.uploaded_cv = stored_cv
            self.uploaded_cover_letters = stored_letters
            self.success_message = (
                f"Stored {1 + len(stored_letters)} file(s): 1 CV and {len(stored_letters)} cover letter(s)."
            )
        except Exception as exc:
            self.error_message = f"File upload failed: {exc}"
            self._debug(f"File upload exception: {exc}")
            self._debug(traceback.format_exc())

    @rx.event(background=True)
    async def parse_and_generate_profile(self) -> None:
        async with self:
            self._debug("parse_and_generate_profile called")
            if self.is_processing:
                return

            self._clear_messages()
            self.is_processing = True
            self.step = "processing"
            self.extraction_warnings = []

            if not self.uploaded_cv:
                self.error_message = "Upload a CV before processing."
                self.step = "upload"
                self.is_processing = False
                return

            cv_name = self.uploaded_cv["name"]
            cv_path = self.uploaded_cv["path"]
            cover_file_infos = list(self.uploaded_cover_letters[:MAX_COVER_LETTERS])

        try:
            try:
                cv_text = await run_in_thread(lambda: extract_text_from_file(cv_path))
            except TextExtractionError as exc:
                async with self:
                    self.error_message = f"CV extraction failed: {cv_name}: {exc}"
                    self.step = "upload"
                    self.is_processing = False
                return

            cover_letters: list[str] = []
            warnings: list[str] = []
            for file_info in cover_file_infos:
                file_name = file_info["name"]
                file_path = file_info["path"]
                try:
                    text = await run_in_thread(lambda path=file_path: extract_text_from_file(path))
                    cover_letters.append(text)
                except TextExtractionError as exc:
                    warnings.append(f"Cover letter extraction failed for {file_name}: {exc}")

            combined_text = aggregate_profile_input(cv_text=cv_text, cover_letters=cover_letters)

            if not combined_text.strip():
                async with self:
                    self.combined_text = ""
                    self.extraction_warnings = warnings
                    self.error_message = "Unable to extract meaningful text from uploaded documents."
                    self.step = "upload"
                    self.is_processing = False
                return

            generated = await run_in_thread(lambda: generate_profile_json_once(combined_text))
            gap_detection = await run_in_thread(lambda: detect_profile_gaps(generated, combined_text))
            clarification_answers = {question.field_key: [] for question in gap_detection.questions}

            async with self:
                self.combined_text = combined_text
                self.extraction_warnings = warnings
                self.profile = generated.model_dump()
                self.has_gaps = gap_detection.has_gaps
                self.gap_questions = [
                    {
                        "field_key": question.field_key,
                        "label": question.label,
                        "prompt": question.prompt,
                        "input_type": question.input_type,
                        "required": question.required,
                        "options": list(question.options),
                    }
                    for question in gap_detection.questions
                ]
                self.clarification_answers = clarification_answers
                self.success_message = (
                    "Profile generated. Please answer a few clarification questions."
                    if gap_detection.has_gaps
                    else "Profile generated successfully."
                )
                self.step = "clarification" if gap_detection.has_gaps else "profile"
                self.is_processing = False

        except ProfileGenerationError as exc:
            async with self:
                self.error_message = str(exc)
                self.step = "upload"
                self.is_processing = False
            self._debug(f"Profile generation error: {exc}")
        except Exception as exc:
            async with self:
                self.error_message = f"Unexpected processing failure: {exc}"
                self.step = "upload"
                self.is_processing = False
            self._debug(f"Unexpected processing exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self._debug("parse_and_generate_profile finished")

    def save_profile_json(self) -> None:
        self._debug("save_profile_json called")
        self._clear_messages()
        self.is_saving = True
        try:
            output_path = Path("output") / "applicant_profile.json"
            profile_model = ApplicantProfile.model_validate(self.profile)
            save_profile(profile=profile_model, path=str(output_path))
            self.has_saved_profile = True
            self.success_message = f"Saved profile to {output_path}."
        except ValidationError as exc:
            self.error_message = f"Profile is invalid and cannot be saved: {exc}"
        except Exception as exc:
            self.error_message = f"Failed to save profile: {exc}"
            self._debug(f"Save exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self.is_saving = False

    def load_saved_profile_json(self) -> None:
        self._debug("load_saved_profile_json called")
        self._clear_messages()
        output_path = Path("output") / "applicant_profile.json"
        try:
            if not saved_profile_exists(str(output_path)):
                self.has_saved_profile = False
                self.error_message = "No saved profile found at output/applicant_profile.json"
                return

            loaded = load_profile(str(output_path))
            self.profile = loaded.model_dump()
            self.has_saved_profile = True
            self._reset_refinement_state()
            self.step = "profile"
            self.success_message = "Loaded saved profile from output/applicant_profile.json (AI generation skipped)."
        except Exception as exc:
            self.error_message = f"Failed to load saved profile JSON: {exc}"
            self._debug(self.error_message)
            self._debug(traceback.format_exc())

    def go_to_upload(self) -> None:
        self.step = "upload"

    def _normalize_clarification_values(self, value: str) -> list[str]:
        split_values = value.replace("\n", ",").split(",")
        items: list[str] = []
        seen: set[str] = set()
        for item in split_values:
            cleaned = item.strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            items.append(cleaned)
        return items

    def set_clarification_text_answer(self, field_key: str, value: str) -> None:
        updated = dict(self.clarification_answers)
        updated[field_key] = self._normalize_clarification_values(value)
        self.clarification_answers = updated

    def toggle_clarification_option(self, field_key: str, option: str) -> None:
        updated = dict(self.clarification_answers)
        selected = list(updated.get(field_key, []))
        option_key = option.casefold()

        existing_keys = [item.casefold() for item in selected]
        if option_key in existing_keys:
            selected = [item for item in selected if item.casefold() != option_key]
        else:
            selected.append(option)

        updated[field_key] = selected
        self.clarification_answers = updated

    def is_clarification_option_selected(self, field_key: str, option: str) -> bool:
        selected = self.clarification_answers.get(field_key, [])
        selected_keys = {item.casefold() for item in selected}
        return option.casefold() in selected_keys

    def clarification_answer_text(self, field_key: str) -> str:
        values = self.clarification_answers.get(field_key, [])
        return ", ".join(values)

    def skip_clarifications(self) -> None:
        self._clear_messages()
        self._reset_refinement_state()
        self.step = "profile"
        self.success_message = "Clarification skipped. You can continue editing the profile."

    def submit_clarifications_and_refine(self) -> None:
        self._clear_messages()

        required_missing = [
            question["label"]
            for question in self.gap_questions
            if question.get("required", False) and len(self.clarification_answers.get(question["field_key"], [])) == 0
        ]
        if required_missing:
            self.error_message = f"Please answer required questions: {', '.join(required_missing)}"
            return

        self.is_refining = True
        try:
            profile_model = ApplicantProfile.model_validate(self.profile)
            answer_model = ClarificationAnswerSet.model_validate({"answers": self.clarification_answers})
            refined_profile = merge_clarifications_into_profile(profile_model, answer_model)

            self.profile = refined_profile.model_dump()
            self._reset_refinement_state()
            self.step = "profile"
            self.success_message = "Profile refined successfully with your clarifications."
        except ValidationError as exc:
            self.error_message = f"Refinement failed due to invalid profile data: {exc}"
        except Exception as exc:
            self.error_message = f"Failed to refine profile: {exc}"
            self._debug(f"Refinement exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self.is_refining = False

    def parse_uploaded_documents(self) -> None:
        """Deprecated no-op retained for compatibility with existing tests."""
        return None

    def update_summary(self, value: str) -> None:
        self.profile["summary"] = value

    def set_new_skill(self, value: str) -> None:
        self.new_skill = value

    def add_skill_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_skill()

    def update_skill(self, index: int, value: str) -> None:
        skills = list(self.profile.get("skills", []))
        if 0 <= index < len(skills):
            skills[index] = value
            self.profile["skills"] = skills

    def add_skill(self) -> None:
        value = self.new_skill.strip()
        if not value:
            return
        skills = list(self.profile.get("skills", []))
        skills.append(value)
        self.profile["skills"] = skills
        self.new_skill = ""

    def remove_skill(self, index: int) -> None:
        skills = list(self.profile.get("skills", []))
        if 0 <= index < len(skills):
            skills.pop(index)
            self.profile["skills"] = skills

    def set_new_project_name(self, value: str) -> None:
        self.new_project_name = value

    def set_new_project_description(self, value: str) -> None:
        self.new_project_description = value

    def add_empty_project(self) -> None:
        projects = list(self.profile.get("projects", []))
        projects.insert(0, {"name": "", "description": ""})
        self.profile["projects"] = projects

    def add_project(self) -> None:
        name = self.new_project_name.strip()
        description = self.new_project_description.strip()
        if not name and not description:
            return
        projects = list(self.profile.get("projects", []))
        projects.append({"name": name, "description": description})
        self.profile["projects"] = projects
        self.new_project_name = ""
        self.new_project_description = ""

    def update_project_name(self, index: int, value: str) -> None:
        projects = list(self.profile.get("projects", []))
        if 0 <= index < len(projects):
            projects[index]["name"] = value
            self.profile["projects"] = projects

    def update_project_description(self, index: int, value: str) -> None:
        projects = list(self.profile.get("projects", []))
        if 0 <= index < len(projects):
            projects[index]["description"] = value
            self.profile["projects"] = projects

    def remove_project(self, index: int) -> None:
        projects = list(self.profile.get("projects", []))
        if 0 <= index < len(projects):
            projects.pop(index)
            self.profile["projects"] = projects

    def set_new_experience_role(self, value: str) -> None:
        self.new_experience_role = value

    def set_new_experience_company(self, value: str) -> None:
        self.new_experience_company = value

    def set_new_experience_duration(self, value: str) -> None:
        self.new_experience_duration = value

    def set_new_experience_description(self, value: str) -> None:
        self.new_experience_description = value

    def add_empty_experience(self) -> None:
        experience = list(self.profile.get("experience", []))
        experience.insert(0, {"role": "", "company": "", "duration": "", "description": ""})
        self.profile["experience"] = experience

    def add_experience(self) -> None:
        role = self.new_experience_role.strip()
        company = self.new_experience_company.strip()
        duration = self.new_experience_duration.strip()
        description = self.new_experience_description.strip()
        if not role and not company and not duration and not description:
            return
        experience = list(self.profile.get("experience", []))
        experience.append(
            {
                "role": role,
                "company": company,
                "duration": duration,
                "description": description,
            }
        )
        self.profile["experience"] = experience
        self.new_experience_role = ""
        self.new_experience_company = ""
        self.new_experience_duration = ""
        self.new_experience_description = ""

    def update_experience_role(self, index: int, value: str) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience[index]["role"] = value
            self.profile["experience"] = experience

    def update_experience_company(self, index: int, value: str) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience[index]["company"] = value
            self.profile["experience"] = experience

    def update_experience_duration(self, index: int, value: str) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience[index]["duration"] = value
            self.profile["experience"] = experience

    def update_experience_description(self, index: int, value: str) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience[index]["description"] = value
            self.profile["experience"] = experience

    def remove_experience(self, index: int) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience.pop(index)
            self.profile["experience"] = experience

    def set_new_language_name(self, value: str) -> None:
        self.new_language_name = value

    def set_new_language_level(self, value: str) -> None:
        self.new_language_level = value

    def update_language_name(self, index: int, value: str) -> None:
        languages = list(self.profile.get("languages", []))
        if 0 <= index < len(languages):
            languages[index]["name"] = value
            self.profile["languages"] = languages

    def update_language_level(self, index: int, value: str) -> None:
        languages = list(self.profile.get("languages", []))
        if 0 <= index < len(languages):
            languages[index]["level"] = value
            self.profile["languages"] = languages

    def add_language(self) -> None:
        name = self.new_language_name.strip()
        level = self.new_language_level.strip()
        if not name and not level:
            return
        languages = list(self.profile.get("languages", []))
        languages.append({"name": name, "level": level})
        self.profile["languages"] = languages
        self.new_language_name = ""
        self.new_language_level = ""

    def remove_language(self, index: int) -> None:
        languages = list(self.profile.get("languages", []))
        if 0 <= index < len(languages):
            languages.pop(index)
            self.profile["languages"] = languages

    def _add_preference_item(self, key: str, value: str) -> None:
        item = value.strip()
        if not item:
            return
        preferences = dict(self.profile.get("preferences", {}))
        values = list(preferences.get(key, []))
        values.append(item)
        preferences[key] = values
        self.profile["preferences"] = preferences

    def _add_preference_item_on_key(self, key: str, value: str, event_key: str) -> None:
        if event_key == "Enter":
            self._add_preference_item(key, value)

    def _remove_preference_item(self, key: str, index: int) -> None:
        preferences = dict(self.profile.get("preferences", {}))
        values = list(preferences.get(key, []))
        if 0 <= index < len(values):
            values.pop(index)
            preferences[key] = values
            self.profile["preferences"] = preferences

    def _update_preference_item(self, key: str, index: int, value: str) -> None:
        preferences = dict(self.profile.get("preferences", {}))
        values = list(preferences.get(key, []))
        if 0 <= index < len(values):
            values[index] = value
            preferences[key] = values
            self.profile["preferences"] = preferences

    def set_new_pref_location(self, value: str) -> None:
        self.new_pref_location = value

    def set_new_pref_work_type(self, value: str) -> None:
        self.new_pref_work_type = value

    def set_new_pref_mode(self, value: str) -> None:
        self.new_pref_mode = value

    def set_new_pref_industry(self, value: str) -> None:
        self.new_pref_industry = value

    def set_new_pref_company_size(self, value: str) -> None:
        self.new_pref_company_size = value

    def add_pref_location_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_pref_location()

    def add_pref_work_type_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_pref_work_type()

    def add_pref_mode_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_pref_mode()

    def add_pref_industry_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_pref_industry()

    def add_pref_company_size_on_key(self, key: str, _: dict[str, bool]) -> None:
        if key == "Enter":
            self.add_pref_company_size()

    def update_pref_location(self, index: int, value: str) -> None:
        self._update_preference_item("locations", index, value)

    def update_pref_work_type(self, index: int, value: str) -> None:
        self._update_preference_item("work_types", index, value)

    def update_pref_mode(self, index: int, value: str) -> None:
        self._update_preference_item("remote_hybrid_on_site", index, value)

    def update_pref_industry(self, index: int, value: str) -> None:
        self._update_preference_item("industries", index, value)

    def update_pref_company_size(self, index: int, value: str) -> None:
        self._update_preference_item("company_size", index, value)

    def add_pref_location(self) -> None:
        self._add_preference_item("locations", self.new_pref_location)
        self.new_pref_location = ""

    def remove_pref_location(self, index: int) -> None:
        self._remove_preference_item("locations", index)

    def add_pref_work_type(self) -> None:
        self._add_preference_item("work_types", self.new_pref_work_type)
        self.new_pref_work_type = ""

    def remove_pref_work_type(self, index: int) -> None:
        self._remove_preference_item("work_types", index)

    def add_pref_mode(self) -> None:
        self._add_preference_item("remote_hybrid_on_site", self.new_pref_mode)
        self.new_pref_mode = ""

    def remove_pref_mode(self, index: int) -> None:
        self._remove_preference_item("remote_hybrid_on_site", index)

    def add_pref_industry(self) -> None:
        self._add_preference_item("industries", self.new_pref_industry)
        self.new_pref_industry = ""

    def remove_pref_industry(self, index: int) -> None:
        self._remove_preference_item("industries", index)

    def add_pref_company_size(self) -> None:
        self._add_preference_item("company_size", self.new_pref_company_size)
        self.new_pref_company_size = ""

    def remove_pref_company_size(self, index: int) -> None:
        self._remove_preference_item("company_size", index)
