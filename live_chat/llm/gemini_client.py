"""Gemini client wrapper isolated behind a small structured-output interface."""

from __future__ import annotations

import json
import os
from typing import Any

from live_chat.config import load_project_env


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_api_key() -> str:
    """Return the Gemini API key or raise a clear error."""
    load_project_env()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")
    return api_key


def get_model_name() -> str:
    """Return the configured Gemini model name."""
    load_project_env()
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def _get_sdk_modules() -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Run `pip install google-genai`."
        ) from exc
    return genai, types


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object.")
    return parsed


def generate_structured_response(
    prompt: str,
    response_schema: dict,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Generate structured JSON using Gemini and return a parsed Python dict."""
    genai, types = _get_sdk_modules()
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(
        model=get_model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    return _parse_json_response(getattr(response, "text", ""))
