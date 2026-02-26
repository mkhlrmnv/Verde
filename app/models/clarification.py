from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


QuestionInputType = Literal["multi_select", "text_list"]


class GapQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_key: str
    label: str
    prompt: str
    input_type: QuestionInputType = "multi_select"
    required: bool = True
    options: list[str] = Field(default_factory=list)


class GapDetectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_gaps: bool = False
    questions: list[GapQuestion] = Field(default_factory=list)


class GapQuestionData(TypedDict):
    field_key: str
    label: str
    prompt: str
    input_type: QuestionInputType
    required: bool
    options: list[str]


class ClarificationAnswerSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, list[str]] = Field(default_factory=dict)
