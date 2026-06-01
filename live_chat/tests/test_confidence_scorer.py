from live_chat.confidence.scorer import calculate_confidence


def test_confidence_score_is_clamped_to_upper_bound():
    result = calculate_confidence(
        retrieval_score=2.0,
        classification_confidence=2.0,
        missing_info_count=0,
        escalation_required=False,
    )
    assert result == 1.0


def test_confidence_score_is_clamped_to_lower_bound():
    result = calculate_confidence(
        retrieval_score=-1.0,
        classification_confidence=-1.0,
        missing_info_count=10,
        escalation_required=True,
    )
    assert result == 0.0
