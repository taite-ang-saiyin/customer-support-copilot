"""Rule-based escalation checks used around Gemini output."""

from __future__ import annotations


RISK_CATEGORIES = {"security", "legal", "privacy"}
HIGH_IMPACT_KEYWORDS = (
    "account takeover",
    "legal complaint",
    "privacy request",
    "payment dispute",
    "outage",
    "large refund",
    "production down",
    "service down",
)


def _highest_retrieval_score(retrieved_context: list[dict] | None) -> float:
    scores = []
    for item in retrieved_context or []:
        try:
            scores.append(float(item.get("score", 0.0)))
        except (TypeError, ValueError, AttributeError):
            scores.append(0.0)
    return max(scores, default=0.0)


def _combined_text(input_data: dict) -> str:
    parts = [
        str(input_data.get("customer_message", "")),
        str(input_data.get("latest_message", "")),
        str(input_data.get("intent", "")),
        str(input_data.get("category", "")),
        str(input_data.get("priority", "")),
        str(input_data.get("sentiment", "")),
    ]
    entities = input_data.get("entities", {})
    if isinstance(entities, dict):
        parts.extend(str(value) for value in entities.values())
    history = input_data.get("conversation_history", [])
    if isinstance(history, list):
        parts.extend(str(item.get("message", "")) for item in history if isinstance(item, dict))
    return " ".join(parts).lower()


def should_escalate(input_data: dict) -> dict:
    category = str(input_data.get("category", "")).strip().lower()
    priority = str(input_data.get("priority", "")).strip().lower()
    sentiment = str(input_data.get("sentiment", "")).strip().lower()
    customer_plan = str(input_data.get("customer_plan", "")).strip().lower()
    retrieved_context = input_data.get("retrieved_context") or []
    retrieval_score = input_data.get("retrieval_score")
    if retrieval_score is None:
        retrieval_score = _highest_retrieval_score(retrieved_context)

    full_text = _combined_text(input_data)

    if category in RISK_CATEGORIES:
        return {
            "escalation_required": True,
            "escalation_reason": f"{category.title()} issues require human review.",
        }
    if priority == "urgent":
        return {
            "escalation_required": True,
            "escalation_reason": "Urgent priority requires human review.",
        }
    if sentiment == "angry":
        return {
            "escalation_required": True,
            "escalation_reason": "Angry customer sentiment requires human review.",
        }
    if not retrieved_context:
        return {
            "escalation_required": True,
            "escalation_reason": "No retrieved evidence is available for a grounded response.",
        }
    if float(retrieval_score) < 0.55:
        return {
            "escalation_required": True,
            "escalation_reason": "Low retrieval confidence requires human review.",
        }
    if customer_plan in {"enterprise", "vip"} and (
        priority in {"high", "urgent"}
        or "cannot log in" in full_text
        or "service down" in full_text
        or "outage" in full_text
    ):
        return {
            "escalation_required": True,
            "escalation_reason": "High-impact enterprise or VIP issue requires human review.",
        }
    if any(keyword in full_text for keyword in HIGH_IMPACT_KEYWORDS):
        return {
            "escalation_required": True,
            "escalation_reason": "High-risk issue type requires human review.",
        }
    if input_data.get("validation_failed"):
        return {
            "escalation_required": True,
            "escalation_reason": str(
                input_data.get(
                    "validation_reason",
                    "Model output validation failed and requires human review.",
                )
            ),
        }

    return {"escalation_required": False, "escalation_reason": None}
