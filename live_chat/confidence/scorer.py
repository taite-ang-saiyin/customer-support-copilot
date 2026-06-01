"""Confidence scoring for ticket drafts and live chat suggestions."""

from __future__ import annotations


def calculate_confidence(
    retrieval_score: float,
    classification_confidence: float,
    missing_info_count: int,
    escalation_required: bool,
) -> float:
    completeness_score = max(0.0, 1.0 - (0.15 * max(0, missing_info_count)))
    if escalation_required:
        completeness_score = max(0.0, completeness_score - 0.2)

    confidence = (
        (max(0.0, min(1.0, retrieval_score)) * 0.5)
        + (max(0.0, min(1.0, classification_confidence)) * 0.3)
        + (completeness_score * 0.2)
    )
    return max(0.0, min(1.0, confidence))
