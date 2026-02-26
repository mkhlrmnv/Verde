from __future__ import annotations

import re

from app.models.clarification import ClarificationAnswerSet
from app.models.profile import ApplicantProfile


_FIELD_TO_PREFERENCE_KEY = {
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
    "full time": "full-time",
    "full-time": "full-time",
    "part time": "part-time",
    "part-time": "part-time",
    "contract": "contract",
    "internship": "internship",
    "thesis": "thesis",
    "freelance": "freelance",
    "temporary": "temporary",
}


def _dedupe_keep_order(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = item.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _canonicalize_for_field(field_key: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    if field_key == "preferences.remote_hybrid_on_site":
        return _MODE_ALIASES.get(normalized, value.strip())
    if field_key == "preferences.work_types":
        return _WORK_TYPE_ALIASES.get(normalized, value.strip())
    return value.strip()


def merge_clarifications_into_profile(
    profile: ApplicantProfile,
    answers: ClarificationAnswerSet,
) -> ApplicantProfile:
    data = profile.model_dump()
    preferences = dict(data.get("preferences", {}))

    for field_key, preference_key in _FIELD_TO_PREFERENCE_KEY.items():
        existing = list(preferences.get(preference_key, []))
        provided = list(answers.answers.get(field_key, []))

        merged_values = [
            _canonicalize_for_field(field_key, value) for value in [*existing, *provided] if str(value).strip()
        ]
        preferences[preference_key] = _dedupe_keep_order(merged_values)

    data["preferences"] = preferences
    return ApplicantProfile.model_validate(data)
