from pathlib import Path

import pytest

from app.services.aggregate_input import aggregate_profile_input
from app.services.text_extract import TextExtractionError, extract_text_from_file


def test_extract_text_from_txt(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello world", encoding="utf-8")

    text = extract_text_from_file(str(file_path))
    assert text == "hello world"


def test_extract_text_dispatch_unsupported(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.md"
    file_path.write_text("# heading", encoding="utf-8")

    with pytest.raises(TextExtractionError):
        extract_text_from_file(str(file_path))


def test_aggregate_profile_input_cv_only() -> None:
    combined = aggregate_profile_input(cv_text="Senior backend engineer", cover_letters=[])
    assert combined.startswith("=== CV ===")
    assert "Senior backend engineer" in combined
    assert "COVER_LETTER" not in combined


def test_aggregate_profile_input_cv_and_cover_letters_deterministic() -> None:
    combined = aggregate_profile_input(
        cv_text="CV BODY",
        cover_letters=["LETTER A", "LETTER B"],
    )
    assert "=== CV ===\nCV BODY" in combined
    assert "=== COVER_LETTER_1 ===\nLETTER A" in combined
    assert "=== COVER_LETTER_2 ===\nLETTER B" in combined
    assert combined.find("LETTER A") < combined.find("LETTER B")
