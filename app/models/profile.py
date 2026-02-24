from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LanguageEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="")
    level: str = Field(default="")


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
    projects: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    languages: list[LanguageEntry] = Field(default_factory=list)
