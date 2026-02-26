from __future__ import annotations

import re

from app.models.clarification import GapDetectionResult, GapQuestion
from app.models.profile import ApplicantProfile


_PREFERENCE_PATHS = {
    "preferences.remote_hybrid_on_site": "remote_hybrid_on_site",
    "preferences.work_types": "work_types",
    "preferences.locations": "locations",
    "preferences.industries": "industries",
    "preferences.company_size": "company_size",
}

_MODE_ALIASES = {
    "remote": "remote",
    "work from home": "remote",
    "wfh": "remote",
    "hybrid": "hybrid",
    "on-site": "on-site",
    "onsite": "on-site",
    "on site": "on-site",
}

_WORK_TYPE_ALIASES = {
    "full-time": "full-time",
    "full time": "full-time",
    "part-time": "part-time",
    "part time": "part-time",
    "contract": "contract",
    "internship": "internship",
    "thesis": "thesis",
    "freelance": "freelance",
    "temporary": "temporary",
}


def _dedupe_keep_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = item.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _canonicalize_mode(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return _MODE_ALIASES.get(normalized, value.strip())


def _canonicalize_work_type(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return _WORK_TYPE_ALIASES.get(normalized, value.strip())


def _normalize_existing(profile: ApplicantProfile, preference_key: str) -> list[str]:
    raw_values = list(getattr(profile.preferences, preference_key, []))
    if preference_key == "remote_hybrid_on_site":
        return _dedupe_keep_order([_canonicalize_mode(item) for item in raw_values])
    if preference_key == "work_types":
        return _dedupe_keep_order([_canonicalize_work_type(item) for item in raw_values])
    return _dedupe_keep_order(raw_values)


def _question_for_field(field_path: str) -> GapQuestion:
    if field_path == "preferences.remote_hybrid_on_site":
        return GapQuestion(
            field_key=field_path,
            label="Preferred Work Environment",
            prompt="Which work environment do you prefer?",
            input_type="multi_select",
            options=["remote", "hybrid", "on-site"],
            required=True,
        )

    if field_path == "preferences.work_types":
        return GapQuestion(
            field_key=field_path,
            label="Preferred Work Types",
            prompt="What work types are you interested in?",
            input_type="multi_select",
            options=["full-time", "part-time", "contract", "internship", "thesis", "freelance"],
            required=True,
        )

    if field_path == "preferences.locations":
        return GapQuestion(
            field_key=field_path,
            label="Preferred Locations",
            prompt="Which locations are you open to?",
            input_type="text_list",
            required=False,
        )

    if field_path == "preferences.industries":
        return GapQuestion(
            field_key=field_path,
            label="Preferred Industries",
            prompt="Which industries are you targeting?",
            input_type="text_list",
            required=False,
        )

    return GapQuestion(
        field_key=field_path,
        label="Preferred Company Size",
        prompt="What company sizes do you prefer?",
        input_type="multi_select",
        options=["startup", "mid-size", "large"],
        required=False,
    )


def detect_profile_gaps(profile: ApplicantProfile, combined_text: str) -> GapDetectionResult:
    _ = combined_text

    missing_fields: list[str] = []

    for field_path, preference_key in _PREFERENCE_PATHS.items():
        normalized = _normalize_existing(profile, preference_key)
        required = field_path in {"preferences.remote_hybrid_on_site", "preferences.work_types"}
        if required and not normalized:
            missing_fields.append(field_path)
        if not required and not normalized:
            missing_fields.append(field_path)

    questions = [_question_for_field(field_path) for field_path in missing_fields]
    return GapDetectionResult(has_gaps=len(questions) > 0, questions=questions)
