from pathlib import Path

from app.models.profile import ApplicantProfile
from app.services.google_profile_builder import _extract_json_block, normalize_profile_payload
from app.services.profile_store import save_profile
import app.state as state_module
from app.state import AppState


def test_extract_json_block_from_fenced_text() -> None:
    raw = """```json
    {"summary":"x","skills":[],"projects":[],"experience":[],"preferences":{"locations":[],"work_types":[],"remote_hybrid_on_site":[],"industries":[],"company_size":[]},"languages":[]}
    ```"""

    parsed = _extract_json_block(raw)
    profile = ApplicantProfile.model_validate_json(parsed)

    assert profile.summary == "x"


def test_load_saved_profile_path_bypasses_generation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    profile = ApplicantProfile(summary="from saved")
    save_profile(profile=profile, path=str(tmp_path / "output" / "applicant_profile.json"))

    def fail_generate(_: str):
        raise AssertionError("generation path must not be called when loading saved profile")

    monkeypatch.setattr(state_module, "generate_profile_json_once", fail_generate)

    state = AppState()
    state.load_saved_profile_json()

    assert state.error_message == ""
    assert state.profile["summary"] == "from saved"
    assert "AI generation skipped" in state.success_message


def test_normalize_profile_payload_coerces_legacy_shapes() -> None:
    raw = {
        "summary": " Candidate summary ",
        "skills": ["Python", "python", "  ", None],
        "projects": ["Legacy project", {"title": "Migrated", "details": "Converted"}],
        "experience": [
            "Senior Engineer",
            {
                "title": "Lead",
                "employer": "Acme",
                "period": "2020-2024",
                "details": "Built systems",
            },
        ],
        "preferences": {
            "locations": ["Berlin", "berlin"],
            "work_types": ["Full-time"],
            "remote_hybrid_on_site": ["Remote"],
            "industries": ["FinTech"],
            "company_size": ["Startup"],
        },
        "languages": ["English", {"language": "German", "proficiency": "B2"}],
    }

    normalized = normalize_profile_payload(raw)
    validated = ApplicantProfile.model_validate(normalized).model_dump()

    assert validated["summary"] == "Candidate summary"
    assert validated["skills"] == ["Python"]
    assert validated["projects"] == [
        {"name": "Legacy project", "description": ""},
        {"name": "Migrated", "description": "Converted"},
    ]
    assert validated["experience"][0]["role"] == "Senior Engineer"
    assert validated["experience"][1] == {
        "role": "Lead",
        "company": "Acme",
        "duration": "2020-2024",
        "description": "Built systems",
    }
    assert validated["languages"] == [
        {"name": "English", "level": ""},
        {"name": "German", "level": "B2"},
    ]


def test_normalize_profile_payload_ignores_extra_keys() -> None:
    normalized = normalize_profile_payload(
        {
            "summary": "ok",
            "skills": ["A"],
            "projects": [{"name": "P", "description": "D", "extra": "x"}],
            "experience": [{"role": "R", "company": "C", "duration": "1y", "description": "D", "extra": "x"}],
            "preferences": {"locations": ["NYC"], "unexpected": ["x"]},
            "languages": [{"name": "English", "level": "Native", "unexpected": "x"}],
            "unexpected_root": "x",
        }
    )

    validated = ApplicantProfile.model_validate(normalized).model_dump()
    assert set(validated.keys()) == {
        "summary",
        "skills",
        "projects",
        "experience",
        "preferences",
        "languages",
    }
