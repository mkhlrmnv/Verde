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
        return ApplicantProfile.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ProfileGenerationError(f"Invalid model JSON output: {exc}") from exc
