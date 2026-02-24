from __future__ import annotations

from pathlib import Path
import traceback
from typing import Any
import uuid

import reflex as rx
from pydantic import ValidationError

from app.models.profile import ApplicantProfile
from app.services.aggregate_input import aggregate_profile_input
from app.services.file_storage import is_supported_extension, save_upload_bytes
from app.services.google_profile_builder import ProfileGenerationError, generate_profile_json_once
from app.services.profile_store import load_profile, save_profile, saved_profile_exists
from app.services.text_extract import TextExtractionError, extract_text_from_file


MAX_COVER_LETTERS = 10


class AppState(rx.State):
    session_id: str = uuid.uuid4().hex
    uploaded_cv: dict[str, str] = {}
    uploaded_cover_letters: list[dict[str, str]] = []
    combined_text: str = ""
    extraction_warnings: list[str] = []
    error_message: str = ""
    success_message: str = ""
    is_parsing: bool = False
    is_generating: bool = False
    is_saving: bool = False
    has_saved_profile: bool = False

    profile: dict[str, Any] = ApplicantProfile().model_dump()

    new_skill: str = ""
    new_project: str = ""
    new_experience: str = ""
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
    def summary(self) -> str:
        return str(self.profile.get("summary", ""))

    @rx.var
    def skills(self) -> list[str]:
        return list(self.profile.get("skills", []))

    @rx.var
    def projects(self) -> list[str]:
        return list(self.profile.get("projects", []))

    @rx.var
    def experience(self) -> list[str]:
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

    def check_saved_profile_exists(self) -> None:
        output_path = Path("output") / "applicant_profile.json"
        self.has_saved_profile = saved_profile_exists(str(output_path))

    def _reset_parsed_artifacts(self) -> None:
        self.combined_text = ""
        self.extraction_warnings = []

    async def handle_cv_upload(self, files: list[rx.UploadFile]) -> None:
        self._debug("handle_cv_upload called")
        try:
            self._clear_messages()
            self._reset_parsed_artifacts()

            incoming_count = len(files) if files else 0
            self._debug(f"Incoming CV files count: {incoming_count}")

            if not files:
                self.error_message = "No CV file selected."
                self._debug("No CV selected by user")
                return

            if len(files) > 1:
                warning = "Multiple CV files selected. Keeping the first file only."
                self.extraction_warnings.append(warning)
                self._debug(warning)

            upload = files[0]
            filename = upload.filename or "uploaded_cv.txt"
            self._debug(f"Processing CV upload: {filename}")
            if not is_supported_extension(filename):
                self.error_message = f"Unsupported CV file: {filename}. Allowed formats: .pdf, .docx, .txt"
                self._debug(self.error_message)
                return

            data = await upload.read()
            self._debug(f"Read CV bytes for {filename}: {len(data)}")
            path = save_upload_bytes(file_bytes=data, filename=filename, session_id=self.session_id)
            self.uploaded_cv = {"name": filename, "path": str(path)}
            self.success_message = f"CV uploaded: {filename}."
            self._debug(self.success_message)
        except Exception as exc:
            self.error_message = f"CV upload failed: {exc}"
            self._debug(f"CV upload exception: {exc}")
            self._debug(traceback.format_exc())

    async def handle_cover_letter_uploads(self, files: list[rx.UploadFile]) -> None:
        self._debug("handle_cover_letter_uploads called")
        try:
            self._clear_messages()
            self._reset_parsed_artifacts()

            incoming_count = len(files) if files else 0
            self._debug(f"Incoming cover-letter files count: {incoming_count}")
            if not files:
                self.error_message = "No cover-letter files selected."
                self._debug("No cover letters selected by user")
                return

            if len(files) > MAX_COVER_LETTERS:
                self.error_message = f"Select up to {MAX_COVER_LETTERS} cover letters."
                self._debug(self.error_message)
                return

            stored: list[dict[str, str]] = []
            for upload in files:
                filename = upload.filename or "cover_letter.txt"
                self._debug(f"Processing cover letter upload: {filename}")
                if not is_supported_extension(filename):
                    warning = f"Skipped unsupported cover letter: {filename}"
                    self.extraction_warnings.append(warning)
                    self._debug(warning)
                    continue

                data = await upload.read()
                self._debug(f"Read cover letter bytes for {filename}: {len(data)}")
                path = save_upload_bytes(file_bytes=data, filename=filename, session_id=self.session_id)
                stored.append({"name": filename, "path": str(path)})

            self.uploaded_cover_letters = stored
            if not self.uploaded_cover_letters:
                self.error_message = "No supported cover letters uploaded. Allowed formats: .pdf, .docx, .txt"
                self._debug(self.error_message)
                return

            self.success_message = f"Stored {len(self.uploaded_cover_letters)} cover letter(s)."
            self._debug(self.success_message)
        except Exception as exc:
            self.error_message = f"Cover-letter upload failed: {exc}"
            self._debug(f"Cover-letter upload exception: {exc}")
            self._debug(traceback.format_exc())

    def parse_uploaded_documents(self) -> None:
        self._debug("parse_uploaded_documents called")
        self._clear_messages()
        self.is_parsing = True
        self.extraction_warnings = []

        try:
            if not self.uploaded_cv:
                self.error_message = "Upload a CV before parsing."
                self._debug("Parse aborted: no uploaded_cv in state")
                return

            cv_name = self.uploaded_cv["name"]
            cv_path = self.uploaded_cv["path"]
            self._debug(f"Extracting CV text from {cv_name} at {cv_path}")
            try:
                cv_text = extract_text_from_file(cv_path)
            except TextExtractionError as exc:
                self.error_message = f"CV extraction failed: {cv_name}: {exc}"
                self._debug(self.error_message)
                return

            cover_letters: list[str] = []
            for file_info in self.uploaded_cover_letters[:MAX_COVER_LETTERS]:
                file_name = file_info["name"]
                file_path = file_info["path"]
                self._debug(f"Extracting cover letter text from {file_name} at {file_path}")
                try:
                    text = extract_text_from_file(file_path)
                    self._debug(f"Extracted cover-letter chars from {file_name}: {len(text)}")
                    cover_letters.append(text)
                except TextExtractionError as exc:
                    warning = f"Cover letter extraction failed for {file_name}: {exc}"
                    self.extraction_warnings.append(warning)
                    self._debug(f"Extraction warning: {warning}")

            self._debug(f"CV chars: {len(cv_text)} | cover letters: {len(cover_letters)}")
            self.combined_text = aggregate_profile_input(cv_text=cv_text, cover_letters=cover_letters)
            self._debug(f"Combined text chars: {len(self.combined_text)}")
            self.success_message = "Documents parsed successfully."
            self._debug(self.success_message)
        except Exception as exc:
            self.error_message = f"Parse failed: {exc}"
            self._debug(f"Parse exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self.is_parsing = False
            self._debug("parse_uploaded_documents finished")

    def build_profile_once(self) -> None:
        self._debug("build_profile_once called")
        self._clear_messages()
        if self.is_generating:
            self._debug("Generation skipped: already in progress")
            return

        if not self.combined_text.strip():
            self.error_message = "Parse uploaded documents before generating profile."
            self._debug("Generation aborted: combined_text is empty")
            return

        self.is_generating = True
        try:
            generated = generate_profile_json_once(self.combined_text)
            self.profile = generated.model_dump()
            self.success_message = "Profile generated successfully. Review and edit before saving."
            self._debug(self.success_message)
        except ProfileGenerationError as exc:
            self.error_message = str(exc)
            self._debug(f"Profile generation error: {exc}")
        except Exception as exc:
            self.error_message = f"Unexpected generation failure: {exc}"
            self._debug(f"Unexpected generation exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self.is_generating = False
            self._debug("build_profile_once finished")

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
            self._debug(self.success_message)
        except ValidationError as exc:
            self.error_message = f"Profile is invalid and cannot be saved: {exc}"
            self._debug(f"Save validation error: {exc}")
        except Exception as exc:
            self.error_message = f"Failed to save profile: {exc}"
            self._debug(f"Save exception: {exc}")
            self._debug(traceback.format_exc())
        finally:
            self.is_saving = False
            self._debug("save_profile_json finished")

    def load_saved_profile_json(self) -> None:
        self._debug("load_saved_profile_json called")
        self._clear_messages()
        output_path = Path("output") / "applicant_profile.json"
        try:
            if not saved_profile_exists(str(output_path)):
                self.has_saved_profile = False
                self.error_message = "No saved profile found at output/applicant_profile.json"
                self._debug(self.error_message)
                return

            loaded = load_profile(str(output_path))
            self.profile = loaded.model_dump()
            self.has_saved_profile = True
            self.success_message = "Loaded saved profile from output/applicant_profile.json (AI generation skipped)."
            self._debug(self.success_message)
        except Exception as exc:
            self.error_message = f"Failed to load saved profile JSON: {exc}"
            self._debug(self.error_message)
            self._debug(traceback.format_exc())

    def update_summary(self, value: str) -> None:
        self.profile["summary"] = value

    def set_new_skill(self, value: str) -> None:
        self.new_skill = value

    def set_new_project(self, value: str) -> None:
        self.new_project = value

    def set_new_experience(self, value: str) -> None:
        self.new_experience = value

    def set_new_language_name(self, value: str) -> None:
        self.new_language_name = value

    def set_new_language_level(self, value: str) -> None:
        self.new_language_level = value

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

    def update_project(self, index: int, value: str) -> None:
        projects = list(self.profile.get("projects", []))
        if 0 <= index < len(projects):
            projects[index] = value
            self.profile["projects"] = projects

    def add_project(self) -> None:
        value = self.new_project.strip()
        if not value:
            return
        projects = list(self.profile.get("projects", []))
        projects.append(value)
        self.profile["projects"] = projects
        self.new_project = ""

    def remove_project(self, index: int) -> None:
        projects = list(self.profile.get("projects", []))
        if 0 <= index < len(projects):
            projects.pop(index)
            self.profile["projects"] = projects

    def update_experience(self, index: int, value: str) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience[index] = value
            self.profile["experience"] = experience

    def add_experience(self) -> None:
        value = self.new_experience.strip()
        if not value:
            return
        experience = list(self.profile.get("experience", []))
        experience.append(value)
        self.profile["experience"] = experience
        self.new_experience = ""

    def remove_experience(self, index: int) -> None:
        experience = list(self.profile.get("experience", []))
        if 0 <= index < len(experience):
            experience.pop(index)
            self.profile["experience"] = experience

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
