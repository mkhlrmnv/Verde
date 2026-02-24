from __future__ import annotations

import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from pydantic import ValidationError

from app.models.profile import ApplicantProfile

DEFAULT_MODEL = "gemini-1.5-flash"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "profile_prompt.txt"


class ProfileGenerationError(Exception):
    pass


def _extract_json_block(raw: str) -> str:
    content = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProfileGenerationError("Model response does not contain JSON")
    return content[start : end + 1]


def _load_prompt(corpus_text: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return f"{template}\n\n{corpus_text}"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = "" if item is None else str(item).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def _normalize_projects(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append({"name": text, "description": ""})
            continue

        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "") or "").strip()
        description = str(item.get("description", "") or "").strip()

        if not name and not description:
            fallback_name = str(item.get("title", "") or "").strip()
            fallback_description = str(item.get("details", "") or "").strip()
            name = fallback_name
            description = fallback_description

        if not name and not description:
            continue

        normalized.append({"name": name, "description": description})

    return normalized


def _normalize_experience(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(
                    {
                        "role": text,
                        "company": "",
                        "duration": "",
                        "description": "",
                    }
                )
            continue

        if not isinstance(item, dict):
            continue

        role = str(item.get("role", "") or item.get("title", "") or "").strip()
        company = str(item.get("company", "") or item.get("employer", "") or "").strip()
        duration = str(item.get("duration", "") or item.get("period", "") or "").strip()
        description = str(item.get("description", "") or item.get("details", "") or "").strip()

        if not role and not company and not duration and not description:
            continue

        normalized.append(
            {
                "role": role,
                "company": company,
                "duration": duration,
                "description": description,
            }
        )

    return normalized


def _normalize_languages(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append({"name": text, "level": ""})
            continue

        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "") or item.get("language", "") or "").strip()
        level = str(item.get("level", "") or item.get("proficiency", "") or "").strip()
        if not name and not level:
            continue
        normalized.append({"name": name, "level": level})

    return normalized


def _normalize_preferences(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        value = {}

    return {
        "locations": _string_list(value.get("locations", [])),
        "work_types": _string_list(value.get("work_types", [])),
        "remote_hybrid_on_site": _string_list(value.get("remote_hybrid_on_site", [])),
        "industries": _string_list(value.get("industries", [])),
        "company_size": _string_list(value.get("company_size", [])),
    }


def normalize_profile_payload(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    return {
        "summary": str(data.get("summary", "") or "").strip(),
        "skills": _string_list(data.get("skills", [])),
        "projects": _normalize_projects(data.get("projects", [])),
        "experience": _normalize_experience(data.get("experience", [])),
        "preferences": _normalize_preferences(data.get("preferences", {})),
        "languages": _normalize_languages(data.get("languages", [])),
    }


def _create_model(model_name: str):
    try:
        from google import genai
    except Exception as exc:
        raise ProfileGenerationError("google-genai is required for profile generation") from exc

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ProfileGenerationError("GOOGLE_API_KEY is missing. Add it to .env.")
    return genai.Client(api_key=api_key), model_name


def generate_profile_json_once(combined_text: str) -> ApplicantProfile:
    if not combined_text.strip():
        raise ProfileGenerationError("Combined input text is empty")

    load_dotenv()
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client, model = _create_model(model_name=model_name)

    prompt = _load_prompt(corpus_text=combined_text)

    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        raise ProfileGenerationError(f"Google model request failed: {exc}") from exc

    response_text = getattr(response, "text", "") or ""
    if not response_text:
        raise ProfileGenerationError("Google model returned empty response")

    try:
        raw_json = _extract_json_block(response_text)
        parsed = json.loads(raw_json)
        normalized = normalize_profile_payload(parsed)
        return ApplicantProfile.model_validate(normalized)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ProfileGenerationError(f"Invalid model JSON output: {exc}") from exc
