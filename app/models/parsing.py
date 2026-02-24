from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParsingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_files: list[str] = Field(default_factory=list)
    combined_text: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)
