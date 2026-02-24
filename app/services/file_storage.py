from __future__ import annotations

from pathlib import Path
import os
import re
import tempfile
import uuid

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _default_upload_base_dir() -> str:
    configured = os.getenv("UPLOAD_BASE_DIR", "").strip()
    if configured:
        return configured
    return str(Path(tempfile.gettempdir()) / "jae_uploads")


def normalize_filename(filename: str) -> str:
    raw_name = Path(filename).name.strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name)
    if not safe_name:
        safe_name = "uploaded_file"
    return safe_name


def is_supported_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_session_folder(session_id: str, base_dir: str | None = None) -> Path:
    resolved_base_dir = base_dir or _default_upload_base_dir()
    folder = Path(resolved_base_dir) / session_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_upload_bytes(file_bytes: bytes, filename: str, session_id: str, base_dir: str | None = None) -> Path:
    safe_name = normalize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")

    session_folder = get_session_folder(session_id=session_id, base_dir=base_dir)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    target = session_folder / unique_name
    target.write_bytes(file_bytes)
    return target


def cleanup_session_folder(session_id: str, base_dir: str | None = None) -> None:
    resolved_base_dir = base_dir or _default_upload_base_dir()
    folder = Path(resolved_base_dir) / session_id
    if not folder.exists():
        return
    for child in folder.glob("**/*"):
        if child.is_file():
            child.unlink(missing_ok=True)
    for child in sorted(folder.glob("**/*"), reverse=True):
        if child.is_dir():
            child.rmdir()
    folder.rmdir()
