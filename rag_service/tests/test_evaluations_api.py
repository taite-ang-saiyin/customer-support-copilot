from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import evaluations as evaluations_api
from app.core.config import settings


class FakeEvaluationService:
    def __init__(self) -> None:
        self.error = {
            "id": "err_eval_test_case_001",
            "module": "rag_service",
            "run_id": "eval_test",
            "error_type": "low_faithfulness",
            "severity": "medium",
            "description": "Low faithfulness",
            "expected_behavior": "Expected",
            "actual_behavior": "Actual",
            "resolved": False,
            "resolved_at": None,
            "resolution_notes": None,
            "metadata": {"case_id": "case_001"},
            "created_at": datetime.now(UTC),
        }

    def create_eval_run(self, **kwargs: Any) -> str:
        return "eval_test"

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self.get_run("eval_test")]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if run_id != "eval_test":
            return None
        return {
            "id": run_id,
            "run_name": "Manual test",
            "module": "rag_service",
            "model_name": None,
            "prompt_version": "rag_prompt_v1",
            "retrieval_version": "chroma_v1",
            "dataset_name": "support_eval",
            "dataset_version": "v1",
            "mlflow_run_id": None,
            "notes": "Test",
            "metadata": {"status": "running"},
            "created_at": datetime.now(UTC),
        }

    def get_metrics(self, run_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "metric_eval_test_faithfulness",
                "run_id": run_id,
                "metric_name": "faithfulness",
                "metric_value": 0.9,
                "metric_unit": "score_0_to_1",
                "created_at": datetime.now(UTC),
            }
        ]

    def get_errors(self, run_id: str) -> list[dict[str, Any]]:
        return [self.error]

    def resolve_error(self, error_id: str, resolution_notes: str) -> bool:
        if error_id != self.error["id"]:
            return False
        self.error["resolved"] = True
        self.error["resolved_at"] = datetime.now(UTC)
        self.error["resolution_notes"] = resolution_notes
        return True

    def get_error(self, error_id: str) -> dict[str, Any] | None:
        return self.error if error_id == self.error["id"] else None

    def save_agent_feedback(
        self,
        error_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        return "feedback_test" if error_id == self.error["id"] else None


def build_client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(evaluations_api.router)
    service = FakeEvaluationService()
    app.dependency_overrides[evaluations_api.get_evaluation_service] = lambda: service
    monkeypatch.setattr(evaluations_api, "run_ragas_evaluation_background", lambda run_id: None)
    monkeypatch.setattr(settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(settings, "internal_api_key", "secret")
    return TestClient(app)


def test_evaluation_run_and_history_endpoints(monkeypatch) -> None:
    client = build_client(monkeypatch)
    headers = {"X-API-Key": "secret"}

    started = client.post(
        "/evaluations/ragas/run",
        headers=headers,
        json={"started_by_agent_id": "agent_001", "notes": "Manual run"},
    )
    runs = client.get("/evaluations/ragas/runs", headers=headers)
    metrics = client.get("/evaluations/ragas/runs/eval_test/metrics", headers=headers)
    errors = client.get("/evaluations/ragas/runs/eval_test/errors", headers=headers)

    assert started.status_code == 202
    assert started.json()["run_id"] == "eval_test"
    assert runs.status_code == 200
    assert len(runs.json()) == 1
    assert metrics.json()[0]["metric_name"] == "faithfulness"
    assert errors.json()[0]["id"] == "err_eval_test_case_001"


def test_evaluation_error_resolution_and_feedback(monkeypatch) -> None:
    client = build_client(monkeypatch)
    headers = {"X-API-Key": "secret"}
    error_id = "err_eval_test_case_001"

    resolved = client.patch(
        f"/evaluations/ragas/errors/{error_id}/resolve",
        headers=headers,
        json={"resolution_notes": "Updated retrieval prompt"},
    )
    feedback = client.post(
        f"/evaluations/ragas/errors/{error_id}/feedback",
        headers=headers,
        json={
            "action": "needs_fix",
            "rating": 2,
            "feedback_note": "Needs correction",
            "edited_text": "Corrected answer",
            "agent_id": "agent_001",
            "agent_name": "Support Manager",
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True
    assert feedback.status_code == 201
    assert feedback.json()["feedback_id"] == "feedback_test"
