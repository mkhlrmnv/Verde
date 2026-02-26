from __future__ import annotations

from app.models.clarification import ClarificationAnswerSet
from app.models.profile import ApplicantProfile
from app.services.profile_refiner import merge_clarifications_into_profile


def test_merge_clarifications_into_profile_merges_without_overwriting_existing_data() -> None:
    profile = ApplicantProfile(
        summary="Existing summary",
        skills=["Python"],
        preferences={
            "locations": ["Helsinki"],
            "work_types": ["full-time"],
            "remote_hybrid_on_site": ["remote"],
            "industries": [],
            "company_size": [],
        },
    )
    answers = ClarificationAnswerSet(
        answers={
            "preferences.locations": ["Espoo"],
            "preferences.work_types": ["Part time"],
            "preferences.remote_hybrid_on_site": ["On site"],
        }
    )

    refined = merge_clarifications_into_profile(profile, answers).model_dump()

    assert refined["summary"] == "Existing summary"
    assert refined["skills"] == ["Python"]
    assert refined["preferences"]["locations"] == ["Helsinki", "Espoo"]
    assert refined["preferences"]["work_types"] == ["full-time", "part-time"]
    assert refined["preferences"]["remote_hybrid_on_site"] == ["remote", "on-site"]


def test_merge_clarifications_into_profile_is_idempotent_with_duplicates() -> None:
    profile = ApplicantProfile(
        preferences={
            "locations": ["Berlin"],
            "work_types": ["full-time"],
            "remote_hybrid_on_site": ["remote"],
            "industries": ["AI"],
            "company_size": ["startup"],
        }
    )
    answers = ClarificationAnswerSet(
        answers={
            "preferences.locations": ["berlin", "Berlin"],
            "preferences.work_types": ["Full Time"],
            "preferences.remote_hybrid_on_site": ["work from home"],
            "preferences.industries": ["AI"],
            "preferences.company_size": ["startup"],
        }
    )

    refined_once = merge_clarifications_into_profile(profile, answers)
    refined_twice = merge_clarifications_into_profile(refined_once, answers)

    assert refined_once.model_dump() == refined_twice.model_dump()
