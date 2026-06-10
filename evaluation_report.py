import json
from datetime import datetime

import requests


API_URL = "http://localhost:8000"

test_dataset = [
    {"message": "I can't access my account", "expected_category": "Account", "expected_priority": "High"},
    {"message": "My invoice has a duplicate charge", "expected_category": "Billing", "expected_priority": "High"},
    {"message": "I want to cancel my subscription", "expected_category": "Subscription", "expected_priority": "Medium"},
    {"message": "Product arrived damaged and I want a refund", "expected_category": "Refund", "expected_priority": "High"},
    {"message": "How do I export my data?", "expected_category": "Product", "expected_priority": "Low"},
    {"message": "The app crashes when I upload files", "expected_category": "Technical", "expected_priority": "Medium"},
    {"message": "The VPN keeps disconnecting", "expected_category": "Network", "expected_priority": "Medium"},
    {"message": "My laptop will not power on", "expected_category": "Hardware", "expected_priority": "High"},
    {"message": "Someone hacked my account", "expected_category": "Security", "expected_priority": "Urgent"},
    {"message": "The website is completely down", "expected_category": "Outage", "expected_priority": "Urgent"},
    {"message": "What are your support hours?", "expected_category": "General", "expected_priority": "Low"},
]

print("\n" + "=" * 70)
print("TICKET ANALYSIS EVALUATION REPORT")
print("=" * 70)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

results = []
for test in test_dataset:
    response = requests.post(
        f"{API_URL}/tickets/analyze",
        json={"message": test["message"], "ticket_id": "eval"},
        timeout=120,
    )

    if response.status_code != 200:
        results.append(
            {
                "message": test["message"],
                "error": response.text,
                "category": {"predicted": None, "expected": test["expected_category"], "correct": False},
                "priority": {"predicted": None, "expected": test["expected_priority"], "correct": False},
                "sentiment": None,
                "confidence": 0,
                "confidence_breakdown": {"category": 0, "priority": 0, "sentiment": 0, "entity": 0},
            }
        )
        continue

    data = response.json()
    predictions = data["predictions"]
    category_correct = predictions["category"] == test["expected_category"]
    priority_correct = predictions["priority"] == test["expected_priority"]

    results.append(
        {
            "message": test["message"],
            "category": {
                "predicted": predictions["category"],
                "expected": test["expected_category"],
                "correct": category_correct,
            },
            "priority": {
                "predicted": predictions["priority"],
                "expected": test["expected_priority"],
                "correct": priority_correct,
            },
            "sentiment": predictions["sentiment"],
            "confidence": predictions["confidence"],
            "confidence_breakdown": predictions["confidence_breakdown"],
        }
    )

category_accuracy = sum(1 for result in results if result["category"]["correct"]) / len(results) * 100
priority_accuracy = sum(1 for result in results if result["priority"]["correct"]) / len(results) * 100
exact_match_accuracy = (
    sum(1 for result in results if result["category"]["correct"] and result["priority"]["correct"])
    / len(results)
    * 100
)
avg_confidence = sum(result["confidence"] for result in results) / len(results)
avg_confidence_breakdown = {
    key: sum(result["confidence_breakdown"][key] for result in results) / len(results)
    for key in ["category", "priority", "sentiment", "entity"]
}

print("\nMODEL PERFORMANCE METRICS")
print("-" * 50)
print(f"Category Accuracy:   {category_accuracy:.1f}%")
print(f"Priority Accuracy:   {priority_accuracy:.1f}%")
print(f"Exact Match:         {exact_match_accuracy:.1f}%")
print(f"Average Confidence:  {avg_confidence:.2f}")
print(f"Average Breakdown:   {avg_confidence_breakdown}")
print(f"Total Test Samples:  {len(results)}")

print("\nDETAILED RESULTS")
print("-" * 80)
for index, result in enumerate(results, 1):
    category_mark = "OK" if result["category"]["correct"] else "FAIL"
    priority_mark = "OK" if result["priority"]["correct"] else "FAIL"
    print(f"\n{index:2}. {result['message']}")
    print(
        f"    Category: {result['category']['predicted']} {category_mark} "
        f"(expected: {result['category']['expected']})"
    )
    print(
        f"    Priority: {result['priority']['predicted']} {priority_mark} "
        f"(expected: {result['priority']['expected']})"
    )
    print(f"    Sentiment: {result['sentiment']}")
    print(f"    Overall Confidence: {result['confidence']:.2f}")
    print(f"    Breakdown: {result['confidence_breakdown']}")

report = {
    "timestamp": datetime.now().isoformat(),
    "metrics": {
        "category_accuracy": category_accuracy,
        "priority_accuracy": priority_accuracy,
        "exact_match_accuracy": exact_match_accuracy,
        "average_confidence": avg_confidence,
        "average_confidence_breakdown": avg_confidence_breakdown,
    },
    "results": results,
}

with open("evaluation_report.json", "w", encoding="utf-8") as file:
    json.dump(report, file, indent=2)

print("\n" + "=" * 70)
print("EVALUATION COMPLETE")
print("=" * 70)
print("\nFull report saved to: evaluation_report.json")
