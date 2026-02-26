from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrengthItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched_skill: str = Field(default="")
    job_requirement: str = Field(default="")
    why_it_matches: str = Field(default="")
    evidence_from_profile: str = Field(default="")


class GapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_or_weak_skill: str = Field(default="")
    job_requirement: str = Field(default="")
    gap_impact: str = Field(default="")
    improvement_suggestion: str = Field(default="")


class StrategyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus_skill: str = Field(default="")
    reason_to_highlight: str = Field(default="")
    example_snippet: str = Field(default="")


class CoverHelperAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: list[StrengthItem] = Field(default_factory=list)
    weaknesses_gaps: list[GapItem] = Field(default_factory=list)
    cover_letter_strategy: list[StrategyItem] = Field(default_factory=list)
    disclaimer: str = Field(default="")
