from __future__ import annotations

from pathlib import Path


class TextExtractionError(Exception):
    pass


def extract_text_from_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise TextExtractionError("pypdf is required for PDF extraction") from exc

    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise TextExtractionError(f"Failed to open PDF: {exc}") from exc

    if reader.is_encrypted:
        raise TextExtractionError("PDF is encrypted and cannot be parsed")

    chunks: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            chunks.append(page_text.strip())

    text = "\n\n".join(chunks).strip()
    if not text:
        raise TextExtractionError("No text found in PDF")
    return text


def extract_text_from_docx(path: str) -> str:
    try:
        from docx import Document
    except Exception as exc:
        raise TextExtractionError("python-docx is required for DOCX extraction") from exc

    try:
        document = Document(path)
    except Exception as exc:
        raise TextExtractionError(f"Failed to open DOCX: {exc}") from exc

    chunks = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    text = "\n".join(chunks).strip()
    if not text:
        raise TextExtractionError("No text found in DOCX")
    return text


def extract_text_from_txt(path: str) -> str:
    try:
        data = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            data = Path(path).read_text(encoding="latin-1")
        except Exception as exc:
            raise TextExtractionError(f"Failed to decode TXT: {exc}") from exc
    except Exception as exc:
        raise TextExtractionError(f"Failed to open TXT: {exc}") from exc

    text = data.strip()
    if not text:
        raise TextExtractionError("Text file is empty")
    return text


def extract_text_from_file(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix == ".txt":
        return extract_text_from_txt(path)
    raise TextExtractionError(f"Unsupported file type: {suffix}")
