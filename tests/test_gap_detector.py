from __future__ import annotations

from app.models.profile import ApplicantProfile
from app.services.gap_detector import detect_profile_gaps


def test_detect_profile_gaps_returns_questions_for_missing_preferences() -> None:
    profile = ApplicantProfile()

    result = detect_profile_gaps(profile, combined_text="candidate corpus")

    assert result.has_gaps is True
    assert len(result.questions) >= 2
    keys = {item.field_key for item in result.questions}
    assert "preferences.remote_hybrid_on_site" in keys
    assert "preferences.work_types" in keys


def test_detect_profile_gaps_no_required_gaps_when_preferences_present() -> None:
    profile = ApplicantProfile(
        preferences={
            "locations": ["Berlin"],
            "work_types": ["Full time"],
            "remote_hybrid_on_site": ["Work from home"],
            "industries": ["FinTech"],
            "company_size": ["Startup"],
        }
    )

    result = detect_profile_gaps(profile, combined_text="candidate corpus")

    assert result.has_gaps is False
    assert result.questions == []


def test_detect_profile_gaps_asks_only_for_missing_fields() -> None:
    profile = ApplicantProfile(
        preferences={
            "locations": ["Berlin"],
            "work_types": [],
            "remote_hybrid_on_site": ["remote"],
            "industries": ["FinTech"],
            "company_size": ["Startup"],
        }
    )

    result = detect_profile_gaps(profile, combined_text="candidate corpus")

    assert result.has_gaps is True
    keys = [item.field_key for item in result.questions]
    assert keys == ["preferences.work_types"]


def test_detect_profile_gaps_is_deterministic() -> None:
    profile = ApplicantProfile()

    first = detect_profile_gaps(profile, combined_text="candidate corpus")
    second = detect_profile_gaps(profile, combined_text="candidate corpus")

    assert first.model_dump() == second.model_dump()
