"""Validation helpers for Gemini-generated ticket drafts and chat suggestions."""

from __future__ import annotations

import re
from typing import Any

from live_chat.generation.json_formatter import (
    available_citations,
    build_fallback_response,
    filter_supported_citations,
    merge_missing_info,
    sanitize_bool,
    sanitize_confidence,
    sanitize_string_list,
    sanitize_text,
)


REFUND_PROMISE_PATTERN = re.compile(
    r"\b(we will refund|refund has been approved|refund will be processed|you will receive a refund)\b",
    re.IGNORECASE,
)


def _context_text(retrieved_context: list[dict] | None) -> str:
    return " ".join(
        sanitize_text(item.get("text"))
        for item in (retrieved_context or [])
        if isinstance(item, dict)
    ).lower()


def _response_mentions_restricted_claim(text: str, input_data: dict) -> bool:
    category = str(input_data.get("category", "")).strip().lower()
    if category in {"security", "legal", "privacy"}:
        return True
    restricted_keywords = ("privacy", "legal", "security", "breach", "account takeover")
    return any(keyword in text.lower() for keyword in restricted_keywords) and not input_data.get(
        "force_allow_restricted_claims",
        False,
    )


def detect_missing_information(input_data: dict) -> list[str]:
    text_parts = [
        str(input_data.get("customer_message", "")),
        str(input_data.get("latest_message", "")),
        str(input_data.get("intent", "")),
        str(input_data.get("category", "")),
    ]
    history = input_data.get("conversation_history", [])
    if isinstance(history, list):
        text_parts.extend(str(item.get("message", "")) for item in history if isinstance(item, dict))
    full_text = " ".join(text_parts).lower()

    entities = input_data.get("entities", {})
    known_details = input_data.get("known_details", {})
    missing: list[str] = []

    def has_detail(*keys: str) -> bool:
        return any(
            (
                isinstance(entities, dict)
                and sanitize_text(entities.get(key))
            )
            or (
                isinstance(known_details, dict)
                and sanitize_text(known_details.get(key))
            )
            for key in keys
        )

    if any(token in full_text for token in ("duplicate charge", "charged twice", "refund", "payment dispute")):
        if not has_detail("transaction_id", "payment_transaction_id") and "transaction id" not in full_text:
            missing.append("transaction_id")
        if not has_detail("payment_receipt", "receipt") and "receipt" not in full_text:
            missing.append("payment_receipt")

    if any(token in full_text for token in ("cannot log in", "can't log in", "login", "access urgently")):
        if not has_detail("error_message") and "error message" not in full_text:
            missing.append("error_message")
        if not has_detail("account_email", "email") and "@" not in full_text:
            missing.append("account_email")

    return missing


def _sanitize_common_output(
    raw_output: Any,
    text_key: str,
    mode: str,
    input_data: dict,
) -> tuple[dict, dict]:
    heuristic_missing = detect_missing_information(input_data)
    citations_from_context = available_citations(input_data.get("retrieved_context"))

    if not isinstance(raw_output, dict):
        reason = "Gemini returned malformed output that could not be validated."
        return (
            build_fallback_response(mode, citations_from_context[:2], heuristic_missing, reason),
            {"validation_failed": True, "validation_reason": reason},
        )

    output = {
        text_key: sanitize_text(raw_output.get(text_key)),
        "agent_notes": sanitize_text(raw_output.get("agent_notes")),
        "citations": filter_supported_citations(
            sanitize_string_list(raw_output.get("citations")),
            input_data.get("retrieved_context"),
        ),
        "confidence": sanitize_confidence(raw_output.get("confidence")),
        "missing_info": merge_missing_info(
            sanitize_string_list(raw_output.get("missing_info")),
            heuristic_missing,
        ),
        "escalation_required": sanitize_bool(raw_output.get("escalation_required")),
        "escalation_reason": raw_output.get("escalation_reason"),
    }

    validation_errors: list[str] = []
    if not output[text_key]:
        validation_errors.append("Missing generated response text.")
    if not output["citations"]:
        if citations_from_context:
            output["citations"] = citations_from_context[:2]
        validation_errors.append("Citations were missing or unsupported.")

    response_text = output[text_key]
    context_text = _context_text(input_data.get("retrieved_context"))
    if REFUND_PROMISE_PATTERN.search(response_text) and "eligible for refund after payment verification" not in context_text:
        validation_errors.append("Unsupported refund promise detected.")
    if _response_mentions_restricted_claim(response_text, input_data):
        validation_errors.append("Restricted legal, privacy, or security claim detected.")

    if validation_errors:
        reason = " ".join(validation_errors)
        output["agent_notes"] = sanitize_text(output["agent_notes"]) or reason
        output["confidence"] = min(output["confidence"], 0.35)
        output["escalation_required"] = True
        output["escalation_reason"] = reason
        return output, {"validation_failed": True, "validation_reason": reason}

    if output["escalation_reason"] is not None:
        output["escalation_reason"] = sanitize_text(output["escalation_reason"]) or None

    return output, {"validation_failed": False, "validation_reason": None}


def evaluate_ticket_draft(raw_output: Any, input_data: dict) -> tuple[dict, dict]:
    return _sanitize_common_output(raw_output, "reply_draft", "ticket", input_data)


def evaluate_livechat_suggestion(raw_output: Any, input_data: dict) -> tuple[dict, dict]:
    return _sanitize_common_output(raw_output, "suggested_reply", "livechat", input_data)
