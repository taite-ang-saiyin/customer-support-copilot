"""Structured JSON schemas used for Gemini output generation."""

TICKET_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply_draft": {"type": "string"},
        "agent_notes": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {"type": "number"},
        "missing_info": {
            "type": "array",
            "items": {"type": "string"},
        },
        "escalation_required": {"type": "boolean"},
        "escalation_reason": {"type": "string", "nullable": True},
    },
    "required": [
        "reply_draft",
        "agent_notes",
        "citations",
        "confidence",
        "missing_info",
        "escalation_required",
        "escalation_reason",
    ],
}


LIVECHAT_SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "suggested_reply": {"type": "string"},
        "agent_notes": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {"type": "number"},
        "missing_info": {
            "type": "array",
            "items": {"type": "string"},
        },
        "escalation_required": {"type": "boolean"},
        "escalation_reason": {"type": "string", "nullable": True},
    },
    "required": [
        "suggested_reply",
        "agent_notes",
        "citations",
        "confidence",
        "missing_info",
        "escalation_required",
        "escalation_reason",
    ],
}
