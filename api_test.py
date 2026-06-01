"""Simple API test client for the local FastAPI app."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def build_ticket_payload() -> dict:
    return {
        "customer_message": "I was charged twice yesterday and I still have not received my refund.",
        "intent": "refund_request",
        "category": "Billing",
        "priority": "High",
        "sentiment": "Frustrated",
        "classification_confidence": 0.86,
        "entities": {
            "issue": "duplicate charge",
            "time": "yesterday",
        },
        "retrieved_context": [
            {
                "source": "Refund Policy",
                "section": "Duplicate Charges",
                "text": "Duplicate charges are eligible for refund after payment verification.",
                "score": 0.91,
            }
        ],
    }


def build_livechat_payload() -> dict:
    return {
        "conversation_history": [
            {
                "sender": "customer",
                "message": "My account was charged twice.",
            },
            {
                "sender": "agent",
                "message": "I am sorry to hear that.",
            },
            {
                "sender": "customer",
                "message": "I need this fixed now.",
            },
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


def post_json(client: httpx.Client, path: str, payload: dict) -> dict:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def print_result(title: str, result: dict) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(result, indent=2, ensure_ascii=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the local Customer Support AI API.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for the FastAPI app. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--mode",
        choices=("ticket", "chat", "all"),
        default="all",
        help="Which endpoint to test.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds.",
    )
    args = parser.parse_args()

    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            if args.mode in {"ticket", "all"}:
                ticket_result = post_json(
                    client,
                    "/tickets/TCK-001/draft",
                    build_ticket_payload(),
                )
                print_result("Ticket Draft Response", ticket_result)

            if args.mode in {"chat", "all"}:
                livechat_result = post_json(
                    client,
                    "/chat/conversations/CHAT-101/suggest",
                    build_livechat_payload(),
                )
                print_result("Live Chat Suggestion Response", livechat_result)
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error: {exc.response.status_code}", file=sys.stderr)
        try:
            print(json.dumps(exc.response.json(), indent=2, ensure_ascii=True), file=sys.stderr)
        except ValueError:
            print(exc.response.text, file=sys.stderr)
        return 1
    except httpx.RequestError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        print("Make sure `uvicorn app:app --reload` is running.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
