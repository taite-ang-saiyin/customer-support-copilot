"""Prompt builder for live chat suggestion generation."""

from __future__ import annotations

import json

from live_chat.prompts.ticket_prompt import SAFETY_RULES


def build_livechat_prompt(input_data: dict) -> str:
    """Build a grounded prompt for live chat suggestion generation."""
    conversation_context = {
        "conversation_id": input_data.get("conversation_id"),
        "known_details": input_data.get("known_details", {}),
        "missing_details": input_data.get("missing_details", []),
        "intent": input_data.get("intent"),
        "category": input_data.get("category"),
        "priority": input_data.get("priority"),
        "sentiment": input_data.get("sentiment"),
        "classification_confidence": input_data.get("classification_confidence"),
        "customer_plan": input_data.get("customer_plan"),
    }

    return (
        "You are a customer support copilot assisting a live support agent.\n"
        "Generate an editable reply suggestion for the agent only.\n"
        "Return valid JSON only.\n\n"
        f"Conversation history:\n"
        f"{json.dumps(input_data.get('conversation_history', []), indent=2, ensure_ascii=True)}\n\n"
        f"Latest customer message:\n{input_data.get('latest_message', '')}\n\n"
        f"Known details and classification:\n"
        f"{json.dumps(conversation_context, indent=2, ensure_ascii=True)}\n\n"
        f"Retrieved evidence:\n"
        f"{json.dumps(input_data.get('retrieved_context', []), indent=2, ensure_ascii=True)}\n\n"
        f"Safety rules:\n- " + "\n- ".join(SAFETY_RULES) + "\n\n"
        "JSON output requirements:\n"
        "- suggested_reply: agent-editable live chat reply.\n"
        "- agent_notes: short private rationale for the agent.\n"
        "- citations: list of source labels in the form 'Source - Section' when available.\n"
        "- confidence: numeric score from 0.0 to 1.0.\n"
        "- missing_info: list of details still needed.\n"
        "- escalation_required: boolean.\n"
        "- escalation_reason: string or null.\n"
        "Do not include reasoning traces."
    )
