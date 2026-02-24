from __future__ import annotations

import json
from pathlib import Path

from app.models.profile import ApplicantProfile


def save_profile(profile: ApplicantProfile, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    temp_file = target.with_suffix(target.suffix + ".tmp")
    payload = profile.model_dump()
    temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(target)


def load_profile(path: str) -> ApplicantProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ApplicantProfile.model_validate(data)


def saved_profile_exists(path: str) -> bool:
    return Path(path).is_file()
