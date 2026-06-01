"""Ticket draft generation pipeline."""

from __future__ import annotations

import sys
import traceback

from live_chat.confidence.scorer import calculate_confidence
from live_chat.escalation.rules import should_escalate
from live_chat.evaluation.draft_evaluation import evaluate_ticket_draft
from live_chat.llm import gemini_client
from live_chat.llm.schemas import TICKET_DRAFT_SCHEMA
from live_chat.prompts.ticket_prompt import build_ticket_prompt


def _retrieval_score(input_data: dict) -> float:
    scores = []
    for item in input_data.get("retrieved_context", []) or []:
        try:
            scores.append(float(item.get("score", 0.0)))
        except (AttributeError, TypeError, ValueError):
            scores.append(0.0)
    return max(scores, default=0.0)


def generate_ticket_draft(input_data: dict) -> dict:
    prompt = build_ticket_prompt(input_data)
    try:
        raw_output = gemini_client.generate_structured_response(
            prompt=prompt,
            response_schema=TICKET_DRAFT_SCHEMA,
            temperature=0.2,
        )
    except Exception as exc:
        print(f"[live_chat.ticket_generator] Gemini request failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        raw_output = None

    output, validation = evaluate_ticket_draft(raw_output, input_data)
    retrieval_score = _retrieval_score(input_data)

    escalation = should_escalate(
        {
            **input_data,
            "retrieval_score": retrieval_score,
            **validation,
        }
    )
    output["escalation_required"] = bool(output["escalation_required"] or escalation["escalation_required"])
    output["escalation_reason"] = output["escalation_reason"] or escalation["escalation_reason"]
    computed_confidence = calculate_confidence(
        retrieval_score=retrieval_score,
        classification_confidence=float(input_data.get("classification_confidence", 0.0) or 0.0),
        missing_info_count=len(output["missing_info"]),
        escalation_required=output["escalation_required"],
    )
    output["confidence"] = min(computed_confidence, output["confidence"]) if validation["validation_failed"] else computed_confidence
    return output
