from live_chat.escalation.rules import should_escalate


def test_low_retrieval_confidence_escalates():
    result = should_escalate(
        {
            "category": "Billing",
            "priority": "High",
            "sentiment": "Frustrated",
            "retrieved_context": [{"source": "Refund Policy", "score": 0.4}],
        }
    )
    assert result["escalation_required"] is True
    assert result["escalation_reason"] == "Low retrieval confidence requires human review."


def test_security_issue_escalates():
    result = should_escalate(
        {
            "category": "Security",
            "priority": "High",
            "sentiment": "Neutral",
            "retrieved_context": [{"source": "Security Runbook", "score": 0.9}],
        }
    )
    assert result["escalation_required"] is True
    assert result["escalation_reason"] == "Security issues require human review."
