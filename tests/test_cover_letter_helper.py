from __future__ import annotations

import pytest

from app.models.cover_helper import CoverHelperAnalysis
from app.services.cover_letter_helper import (
    CoverHelperGenerationError,
    _enforce_output_guardrails,
    _safe_parse_analysis,
)


def test_safe_parse_analysis_accepts_valid_json() -> None:
    raw = """
    {
      "strengths": [
        {
          "matched_skill": "Python",
          "job_requirement": "Backend APIs",
          "why_it_matches": "Built API services",
          "evidence_from_profile": "Designed REST APIs for 3 years"
        }
      ],
      "weaknesses_gaps": [
        {
          "missing_or_weak_skill": "Kubernetes",
          "job_requirement": "Container orchestration",
          "gap_impact": "May slow onboarding",
          "improvement_suggestion": "Take a focused AKS project"
        }
      ],
      "cover_letter_strategy": [
        {
          "focus_skill": "API reliability",
          "reason_to_highlight": "Directly aligns with SRE collaboration",
          "example_snippet": "I improved API uptime by redesigning error handling and observability."
        }
      ]
    }
    """

    result = _safe_parse_analysis(raw)
    assert isinstance(result, CoverHelperAnalysis)
    assert result.strengths[0].matched_skill == "Python"


def test_safe_parse_analysis_recovers_fenced_json() -> None:
    raw = """```json
    {
      "strengths": [],
      "weaknesses_gaps": [],
      "cover_letter_strategy": []
    }
    ```"""

    result = _safe_parse_analysis(raw)
    assert isinstance(result, CoverHelperAnalysis)
    assert result.cover_letter_strategy == []


def test_safe_parse_analysis_rejects_prose_only() -> None:
    with pytest.raises(CoverHelperGenerationError):
        _safe_parse_analysis("This candidate seems like a great fit. Highlight adaptability and impact.")


def test_enforce_output_guardrails_rejects_letter_style() -> None:
    analysis = CoverHelperAnalysis.model_validate(
        {
            "strengths": [],
            "weaknesses_gaps": [],
            "cover_letter_strategy": [
                {
                    "focus_skill": "Leadership",
                    "reason_to_highlight": "Team enablement",
                    "example_snippet": "Dear Hiring Manager, I am excited to apply for this role. Sincerely, Candidate",
                }
            ],
        }
    )

    with pytest.raises(CoverHelperGenerationError):
        _enforce_output_guardrails(analysis)
