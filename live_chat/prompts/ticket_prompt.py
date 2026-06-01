"""Prompt builder for ticket draft generation."""

from __future__ import annotations

import json


SAFETY_RULES = [
    "Use only retrieved evidence.",
    "Do not invent policy details.",
    "Do not promise refunds unless evidence allows it.",
    "Do not make legal, privacy, security, or billing decisions.",
    "Ask for missing information when needed.",
    "Recommend escalation for risky or uncertain cases.",
    "Never auto-send a customer-facing reply.",
    "Keep the support agent in control.",
]


def build_ticket_prompt(input_data: dict) -> str:
    """Build a grounded prompt for ticket draft generation."""
    ticket_metadata = {
        "ticket_id": input_data.get("ticket_id"),
        "channel": input_data.get("channel"),
        "customer_plan": input_data.get("customer_plan"),
        "created_at": input_data.get("created_at"),
    }
    classification = {
        "intent": input_data.get("intent"),
        "category": input_data.get("category"),
        "priority": input_data.get("priority"),
        "sentiment": input_data.get("sentiment"),
        "classification_confidence": input_data.get("classification_confidence"),
        "entities": input_data.get("entities", {}),
    }

    return (
        "You are a customer support copilot.\n"
        "Generate an editable support reply draft for an internal agent.\n"
        "Return valid JSON only.\n\n"
        f"Customer message:\n{input_data.get('customer_message', '')}\n\n"
        f"Ticket metadata:\n{json.dumps(ticket_metadata, indent=2, ensure_ascii=True)}\n\n"
        f"Member 1 classification result:\n"
        f"{json.dumps(classification, indent=2, ensure_ascii=True)}\n\n"
        f"Member 2 retrieved evidence:\n"
        f"{json.dumps(input_data.get('retrieved_context', []), indent=2, ensure_ascii=True)}\n\n"
        f"Safety rules:\n- " + "\n- ".join(SAFETY_RULES) + "\n\n"
        "JSON output requirements:\n"
        "- reply_draft: customer-facing draft for the agent to review.\n"
        "- agent_notes: short private rationale for the agent.\n"
        "- citations: list of source labels in the form 'Source - Section' when available.\n"
        "- confidence: numeric score from 0.0 to 1.0.\n"
        "- missing_info: list of details still needed.\n"
        "- escalation_required: boolean.\n"
        "- escalation_reason: string or null.\n"
        "Do not include reasoning traces."
    )
