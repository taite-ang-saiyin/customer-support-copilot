from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_chat.api.livechat_suggestion_api import router as livechat_router
from live_chat.generation.livechat_generator import generate_livechat_suggestion
from live_chat.llm import gemini_client


def _chat_input():
    return {
        "conversation_id": "CHAT-101",
        "conversation_history": [
            {"sender": "customer", "message": "My account was charged twice."},
            {"sender": "agent", "message": "I am sorry to hear that."},
            {"sender": "customer", "message": "I need this fixed now."},
        ],
        "latest_message": "I need this fixed now.",
        "intent": "refund_request",
        "category": "Billing",
        "priority": "High",
        "sentiment": "Frustrated",
        "classification_confidence": 0.84,
        "retrieved_context": [
            {
                "source": "Refund Policy",
                "section": "Duplicate Charges",
                "text": "Duplicate charges are eligible for refund after payment verification.",
                "score": 0.88,
            }
        ],
    }


def test_livechat_billing_suggestion(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "suggested_reply": (
                "I am sorry for the trouble. Please share the transaction ID or payment receipt "
                "so we can verify the duplicate charge."
            ),
            "agent_notes": "Asks for missing verification details before discussing refund steps.",
            "citations": ["Refund Policy - Duplicate Charges"],
            "confidence": 0.88,
            "missing_info": [],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    result = generate_livechat_suggestion(_chat_input())

    assert result["suggested_reply"]
    assert "transaction_id" in result["missing_info"]
    assert "payment_receipt" in result["missing_info"]
    assert result["citations"] == ["Refund Policy - Duplicate Charges"]


def test_livechat_missing_information_detection(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "suggested_reply": "Please share the transaction ID.",
            "agent_notes": "Need more information.",
            "citations": ["Refund Policy - Duplicate Charges"],
            "confidence": 0.8,
            "missing_info": [],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    result = generate_livechat_suggestion(_chat_input())

    assert result["missing_info"] == ["transaction_id", "payment_receipt"]


def test_livechat_api_response_shape(monkeypatch):
    def fake_generate_structured_response(prompt, response_schema, temperature=0.2):
        return {
            "suggested_reply": "Please share the transaction ID.",
            "agent_notes": "Need more information.",
            "citations": ["Refund Policy - Duplicate Charges"],
            "confidence": 0.8,
            "missing_info": ["transaction_id"],
            "escalation_required": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(gemini_client, "generate_structured_response", fake_generate_structured_response)
    app = FastAPI()
    app.include_router(livechat_router)
    client = TestClient(app)

    payload = _chat_input()
    payload.pop("conversation_id")
    response = client.post("/chat/conversations/CHAT-101/suggest", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert "suggested_reply" in body
    assert "citations" in body
    assert "confidence" in body
