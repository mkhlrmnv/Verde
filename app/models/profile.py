from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _as_clean_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


class LanguageEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="")
    level: str = Field(default="")


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="")
    description: str = Field(default="")


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(default="")
    company: str = Field(default="")
    duration: str = Field(default="")
    description: str = Field(default="")


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locations: list[str] = Field(default_factory=list)
    work_types: list[str] = Field(default_factory=list)
    remote_hybrid_on_site: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    company_size: list[str] = Field(default_factory=list)


class ApplicantProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="")
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    languages: list[LanguageEntry] = Field(default_factory=list)

    @field_validator("projects", mode="before")
    @classmethod
    def _coerce_projects(cls, value: object) -> list[dict[str, str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                normalized.append({"name": text, "description": ""})
                continue

            if not isinstance(item, dict):
                continue

            name = _as_clean_string(item.get("name", ""))
            description = _as_clean_string(item.get("description", ""))
            if not name and not description:
                legacy_text = _as_clean_string(item.get("title", ""))
                if legacy_text:
                    name = legacy_text
            normalized.append({"name": name, "description": description})

        return normalized

    @field_validator("experience", mode="before")
    @classmethod
    def _coerce_experience(cls, value: object) -> list[dict[str, str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                normalized.append(
                    {
                        "role": text,
                        "company": "",
                        "duration": "",
                        "description": "",
                    }
                )
                continue

            if not isinstance(item, dict):
                continue

            role = _as_clean_string(item.get("role", ""))
            company = _as_clean_string(item.get("company", ""))
            duration = _as_clean_string(item.get("duration", ""))
            description = _as_clean_string(item.get("description", ""))

            if not role and not company and not duration and not description:
                legacy_text = _as_clean_string(item.get("title", ""))
                if legacy_text:
                    role = legacy_text

            normalized.append(
                {
                    "role": role,
                    "company": company,
                    "duration": duration,
                    "description": description,
                }
            )

        return normalized
