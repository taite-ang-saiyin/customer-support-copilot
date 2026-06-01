from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_chat.api.ticket_draft_api import router as ticket_router
from live_chat.generation.ticket_generator import generate_ticket_draft
from live_chat.llm import gemini_client


def _ticket_input():
    return {
        "ticket_id": "TCK-001",
        "customer_message": "I was charged twice yesterday and I still have not received my refund.",
        "intent": "refund_request",
        "category": "Billing",
        "priority": "High",
        "sentiment": "Frustrated",
        "classification_confidence": 0.86,
        "entities": {"issue": "duplicate charge", "time": "yesterday"},
        "retrieved_context": [
            {
                "source": "Refund Policy",
                "section": "Duplicate Charges",
                "text": "Duplicate charges are eligible for refund after payment verification.",
                "score": 0.91,
            }
        ],
    }


def test_ticket_draft_generation_duplicate_charge(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "reply_draft": (
                "I am sorry for the trouble. Please share your transaction ID or payment receipt "
                "so we can verify the duplicate charge and help with the next steps."
            ),
            "agent_notes": "Grounded in refund policy and still needs payment verification.",
            "citations": ["Refund Policy - Duplicate Charges"],
            "confidence": 0.93,
            "missing_info": ["transaction_id"],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    result = generate_ticket_draft(_ticket_input())

    assert "transaction_id" in result["missing_info"]
    assert "payment_receipt" in result["missing_info"]
    assert result["citations"] == ["Refund Policy - Duplicate Charges"]
    assert result["escalation_required"] is False
    assert result["reply_draft"]


def test_ticket_citation_validation_forces_escalation(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "reply_draft": "We will refund this right away.",
            "agent_notes": "",
            "citations": ["Random Blog - Unsupported"],
            "confidence": 0.9,
            "missing_info": [],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    result = generate_ticket_draft(_ticket_input())

    assert result["escalation_required"] is True
    assert "Citations were missing or unsupported." in result["escalation_reason"]
    assert result["citations"] == ["Refund Policy - Duplicate Charges"]


def test_ticket_malformed_gemini_output_fallback(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return "not-json"

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    result = generate_ticket_draft(_ticket_input())

    assert result["escalation_required"] is True
    assert result["confidence"] <= 0.5
    assert "review" in result["reply_draft"].lower()


def test_ticket_api_response_shape(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "reply_draft": "Please share your transaction ID.",
            "agent_notes": "Need verification.",
            "citations": ["Refund Policy - Duplicate Charges"],
            "confidence": 0.8,
            "missing_info": ["transaction_id"],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    app = FastAPI()
    app.include_router(ticket_router)
    client = TestClient(app)

    payload = _ticket_input()
    payload.pop("ticket_id")
    response = client.post("/tickets/TCK-001/draft", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert "reply_draft" in body
    assert "citations" in body
    assert "confidence" in body
