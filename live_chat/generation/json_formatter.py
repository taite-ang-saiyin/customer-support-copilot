"""Helpers for sanitizing and validating structured model output."""

from __future__ import annotations

from typing import Iterable


def sanitize_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def sanitize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = sanitize_text(item)
        if text and text not in items:
            items.append(text)
    return items


def sanitize_bool(value: object) -> bool:
    return bool(value)


def sanitize_confidence(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def available_citations(retrieved_context: Iterable[dict] | None) -> list[str]:
    labels: list[str] = []
    for item in retrieved_context or []:
        source = sanitize_text(item.get("source")) if isinstance(item, dict) else ""
        section = sanitize_text(item.get("section")) if isinstance(item, dict) else ""
        label = f"{source} - {section}" if source and section else source
        if label and label not in labels:
            labels.append(label)
    return labels


def filter_supported_citations(
    citations: Iterable[str] | None,
    retrieved_context: Iterable[dict] | None,
) -> list[str]:
    allowed = set(available_citations(retrieved_context))
    valid: list[str] = []
    for citation in citations or []:
        text = sanitize_text(citation)
        if text in allowed and text not in valid:
            valid.append(text)
    return valid


def merge_missing_info(primary: Iterable[str] | None, extra: Iterable[str] | None) -> list[str]:
    merged: list[str] = []
    for value in list(primary or []) + list(extra or []):
        text = sanitize_text(value)
        if text and text not in merged:
            merged.append(text)
    return merged


def build_fallback_response(
    mode: str,
    citations: list[str],
    missing_info: list[str],
    reason: str,
) -> dict:
    if mode == "ticket":
        reply_key = "reply_draft"
        reply_text = (
            "Thanks for reaching out. I need a support agent to review the available "
            "evidence before sending a final response."
        )
    else:
        reply_key = "suggested_reply"
        reply_text = (
            "I need to review the available evidence before sending a final reply. "
            "Please let the customer know we are checking the details."
        )

    return {
        reply_key: reply_text,
        "agent_notes": reason,
        "citations": citations,
        "confidence": 0.0,
        "missing_info": missing_info,
        "escalation_required": True,
        "escalation_reason": reason,
    }
