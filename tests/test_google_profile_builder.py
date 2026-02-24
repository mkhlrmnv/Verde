from pathlib import Path

from app.models.profile import ApplicantProfile
from app.services.google_profile_builder import _extract_json_block
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
