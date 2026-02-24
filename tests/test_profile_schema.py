from pathlib import Path

import pytest

from app.models.profile import ApplicantProfile
from app.services.profile_store import load_profile, save_profile


EXPECTED_KEYS = {"summary", "skills", "projects", "experience", "preferences", "languages"}
EXPECTED_PREFERENCE_KEYS = {
    "locations",
    "work_types",
    "remote_hybrid_on_site",
    "industries",
    "company_size",
}

EXPECTED_PROJECT_KEYS = {"name", "description"}
EXPECTED_EXPERIENCE_KEYS = {"role", "company", "duration", "description"}


def test_profile_schema_keys_exact() -> None:
    profile = ApplicantProfile()
    data = profile.model_dump()

    assert set(data.keys()) == EXPECTED_KEYS
    assert set(data["preferences"].keys()) == EXPECTED_PREFERENCE_KEYS


def test_profile_nested_keys_exact() -> None:
    profile = ApplicantProfile(
        projects=[{"name": "P", "description": "D"}],
        experience=[{"role": "R", "company": "C", "duration": "Now", "description": "D"}],
    )

    data = profile.model_dump()
    assert set(data["projects"][0].keys()) == EXPECTED_PROJECT_KEYS
    assert set(data["experience"][0].keys()) == EXPECTED_EXPERIENCE_KEYS


def test_saved_profile_validates_same_as_generated(tmp_path: Path) -> None:
    profile = ApplicantProfile(summary="Loaded profile")
    target = tmp_path / "applicant_profile.json"

    save_profile(profile=profile, path=str(target))
    loaded = load_profile(str(target))

    assert loaded.model_dump() == profile.model_dump()


def test_load_profile_with_corrupted_json_raises(tmp_path: Path) -> None:
    target = tmp_path / "corrupted.json"
    target.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(Exception):
        load_profile(str(target))


def test_load_profile_migrates_legacy_string_lists(tmp_path: Path) -> None:
    target = tmp_path / "legacy.json"
    target.write_text(
        '{"summary":"x","skills":[],"projects":["Legacy Project"],"experience":["Legacy Role"],"preferences":{"locations":[],"work_types":[],"remote_hybrid_on_site":[],"industries":[],"company_size":[]},"languages":[]}',
        encoding="utf-8",
    )

    loaded = load_profile(str(target)).model_dump()
    assert loaded["projects"][0] == {"name": "Legacy Project", "description": ""}
    assert loaded["experience"][0] == {
        "role": "Legacy Role",
        "company": "",
        "duration": "",
        "description": "",
    }
