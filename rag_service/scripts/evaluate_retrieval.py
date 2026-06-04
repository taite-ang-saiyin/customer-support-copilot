import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    expected_doc: str
    expected_section: str
    top_k: int


def load_cases(path: Path) -> list[EvaluationCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvaluationCase(
            query=item["query"],
            expected_doc=item["expected_doc"],
            expected_section=item["expected_section"],
            top_k=int(item.get("top_k", 3)),
        )
        for item in data
    ]


def search(
    base_url: str,
    case: EvaluationCase,
    timeout: float,
    api_key: str | None,
) -> list[dict[str, Any]]:
    headers = {"X-API-Key": api_key} if api_key else {}
    response = httpx.post(
        f"{base_url.rstrip('/')}/knowledge/search",
        json={"query": case.query, "top_k": case.top_k},
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def evaluate(
    base_url: str,
    cases: list[EvaluationCase],
    timeout: float,
    api_key: str | None,
) -> dict[str, Any]:
    reciprocal_ranks: list[float] = []
    top_1_hits = 0
    top_k_hits = 0
    failures: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.query}")
        try:
            results = search(base_url, case, timeout=timeout, api_key=api_key)
        except httpx.ReadTimeout:
            failures.append(
                {
                    "query": case.query,
                    "expected": f"{case.expected_doc} > {case.expected_section}",
                    "actual_top_result": (
                        f"Request timed out after {timeout} seconds. "
                        "The embedding model may still be loading, or the API may be stuck."
                    ),
                }
            )
            reciprocal_ranks.append(0)
            continue
        except httpx.HTTPStatusError as exc:
            failures.append(
                {
                    "query": case.query,
                    "expected": f"{case.expected_doc} > {case.expected_section}",
                    "actual_top_result": (
                        f"API returned HTTP {exc.response.status_code}. "
                        "Check --api-key or INTERNAL_API_KEY."
                    ),
                }
            )
            reciprocal_ranks.append(0)
            continue
        except httpx.ConnectError:
            failures.append(
                {
                    "query": case.query,
                    "expected": f"{case.expected_doc} > {case.expected_section}",
                    "actual_top_result": (
                        "Could not connect to the API. Start FastAPI first, then rerun evaluation."
                    ),
                }
            )
            reciprocal_ranks.append(0)
            continue

        rank = _expected_rank(case, results)
        if rank == 1:
            top_1_hits += 1
        if rank is not None:
            top_k_hits += 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)

        if rank is None:
            failures.append(_failure_record(case, results))

    total_cases = len(cases)
    return {
        "total_cases": total_cases,
        "top_1_accuracy": _rate(top_1_hits, total_cases),
        "top_k_hit_rate": _rate(top_k_hits, total_cases),
        "mrr": round(sum(reciprocal_ranks) / total_cases, 4) if total_cases else 0,
        "failures": failures,
    }


def print_report(report: dict[str, Any]) -> None:
    print("Retrieval Evaluation Report")
    print("===========================")
    print(f"Total cases: {report['total_cases']}")
    print(f"Top-1 accuracy: {report['top_1_accuracy']:.2%}")
    print(f"Top-k hit rate: {report['top_k_hit_rate']:.2%}")
    print(f"MRR: {report['mrr']:.4f}")

    failures = report["failures"]
    if not failures:
        print("\nNo failed cases.")
        return

    print("\nFailed cases:")
    for failure in failures:
        print("-" * 72)
        print(f"Query: {failure['query']}")
        print(f"Expected: {failure['expected']}")
        print(f"Actual top result: {failure['actual_top_result']}")


def _expected_rank(case: EvaluationCase, results: list[dict[str, Any]]) -> int | None:
    expected_doc = case.expected_doc.lower()
    expected_section = case.expected_section.lower()
    for index, result in enumerate(results, start=1):
        title = str(result.get("title", "")).lower()
        section = str(result.get("section", "")).lower()
        citation = str(result.get("citation", "")).lower()
        doc_matches = expected_doc in title or expected_doc in citation
        section_matches = expected_section in section or expected_section in citation
        if doc_matches and section_matches:
            return index
    return None


def _failure_record(case: EvaluationCase, results: list[dict[str, Any]]) -> dict[str, Any]:
    top_result = results[0] if results else {}
    actual_top = "No results"
    if top_result:
        actual_top = (
            f"{top_result.get('title', 'Unknown')} > "
            f"{top_result.get('section', 'Unknown')} "
            f"(score={top_result.get('score', 'n/a')})"
        )
    return {
        "query": case.query,
        "expected": f"{case.expected_doc} > {case.expected_section}",
        "actual_top_result": actual_top,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running FastAPI service base URL.",
    )
    parser.add_argument(
        "--cases",
        default="eval/retrieval_test_cases.json",
        help="Path to retrieval test case JSON file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180,
        help="HTTP timeout per search request in seconds.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("INTERNAL_API_KEY"),
        help="API key for X-API-Key. Defaults to INTERNAL_API_KEY.",
    )
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    report = evaluate(args.base_url, cases, timeout=args.timeout, api_key=args.api_key)
    print_report(report)


if __name__ == "__main__":
    main()
