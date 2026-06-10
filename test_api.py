import json
import time

import requests


API_URL = "http://localhost:8000"


def test_health():
    print("\n" + "=" * 60)
    print("TESTING HEALTH ENDPOINT")
    print("=" * 60)
    response = requests.get(f"{API_URL}/health", timeout=120)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_taxonomy():
    print("\n" + "=" * 60)
    print("TESTING TAXONOMY ENDPOINT")
    print("=" * 60)
    response = requests.get(f"{API_URL}/taxonomy", timeout=120)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Categories: {len(data['categories'])}")
        print(f"Priorities: {data['priorities']}")
        print(f"Sentiments: {data['sentiments']}")
    return response.status_code == 200


def test_analysis():
    print("\n" + "=" * 60)
    print("TESTING TICKET ANALYSIS")
    print("=" * 60)

    test_cases = [
        {"id": "001", "message": "I can't access my account after resetting my password."},
        {"id": "002", "message": "My invoice shows a duplicate charge for this month."},
        {"id": "003", "message": "The VPN keeps disconnecting every few minutes."},
        {"id": "004", "message": "The website is down and our team cannot work."},
        {"id": "005", "message": "I want to cancel my subscription plan."},
    ]

    valid_categories = {
        "Account",
        "Billing",
        "General",
        "Hardware",
        "Network",
        "Outage",
        "Product",
        "Refund",
        "Security",
        "Subscription",
        "Technical",
    }
    valid_priorities = {"Low", "Medium", "High", "Urgent"}
    valid_sentiments = {"Angry", "Frustrated", "Confused", "Neutral", "Positive"}

    results = []
    for test in test_cases:
        print(f"\nTesting Ticket {test['id']}:")
        print(f"   Message: {test['message']}")

        response = requests.post(
            f"{API_URL}/tickets/analyze",
            json={"message": test["message"], "ticket_id": test["id"]},
            timeout=120,
        )

        if response.status_code == 200:
            data = response.json()
            predictions = data["predictions"]
            has_model_fields = (
                predictions["category"] in valid_categories
                and predictions["priority"] in valid_priorities
                and predictions["sentiment"] in valid_sentiments
                and 0 <= predictions["confidence"] <= 1
                and set(predictions["confidence_breakdown"]) == {"category", "priority", "sentiment", "entity"}
                and "intent" not in predictions
            )

            print(f"   Category: {predictions['category']}")
            print(f"   Priority: {predictions['priority']}")
            print(f"   Sentiment: {predictions['sentiment']}")
            print(f"   Overall Confidence: {predictions['confidence']}")
            print(f"   Confidence Breakdown: {predictions['confidence_breakdown']}")
            print(f"   Entities Found: {data['entities']['entity_count']}")
            results.append({"id": test["id"], "success": has_model_fields})
        else:
            print(f"   Error: {response.status_code}")
            print(f"   Response: {response.text}")
            results.append({"id": test["id"], "success": False})

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    successful = sum(1 for result in results if result["success"])
    print(f"Total Tests: {len(test_cases)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(test_cases) - successful}")
    print(f"Success Rate: {successful / len(test_cases) * 100:.1f}%")

    return successful == len(test_cases)


def run_all_tests():
    print("\n" + "=" * 60)
    print("TICKET INTELLIGENCE API TEST SUITE")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("Taxonomy", test_taxonomy),
        ("Ticket Analysis", test_analysis),
    ]

    for name, test_func in tests:
        if not test_func():
            print(f"\n{name} test failed!")
            return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    run_all_tests()
