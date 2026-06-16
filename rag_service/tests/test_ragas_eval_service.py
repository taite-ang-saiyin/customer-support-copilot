import json
from types import SimpleNamespace
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services import ragas_eval_service as eval_module
from app.services.ragas_eval_service import RagasEvalService


class InMemoryEvaluationStore:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "evaluation_runs": [],
            "evaluation_metrics": [],
            "error_analysis": [],
            "agent_feedback": [],
        }

    def insert(self, table: str, rows: dict[str, Any] | list[dict[str, Any]]):
        inserted = [dict(row) for row in rows] if isinstance(rows, list) else [dict(rows)]
        self.tables[table].extend(inserted)
        return inserted

    def select(self, table: str, filters=None, order=None, limit=None):
        rows = [
            dict(row)
            for row in self.tables[table]
            if all(row.get(key) == value for key, value in (filters or {}).items())
        ]
        if order:
            field, direction = order.split(".")
            rows.sort(key=lambda row: row.get(field, ""), reverse=direction == "desc")
        return rows[:limit] if limit is not None else rows

    def update(self, table: str, values: dict[str, Any], filters: dict[str, Any]):
        updated = []
        for row in self.tables[table]:
            if all(row.get(key) == value for key, value in filters.items()):
                row.update(values)
                updated.append(dict(row))
        return updated

    def delete(self, table: str, filters: dict[str, Any]) -> None:
        self.tables[table] = [
            row
            for row in self.tables[table]
            if not all(row.get(key) == value for key, value in filters.items())
        ]


class FakeKnowledgeService:
    def search(self, db, request, allowed_access_levels):
        text = (
            "Support should verify the payment and follow the duplicate charge refund process."
            if "duplicate" in request.query.lower()
            else "Customers receive a generated tracking code."
        )
        return SimpleNamespace(results=[SimpleNamespace(text=text)])


def score_case(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> dict[str, float]:
    if "track" in question.lower():
        return {
            "faithfulness": 0.50,
            "answer_relevancy": 0.60,
            "context_precision": 0.80,
            "context_recall": 0.70,
        }
    return {
        "faithfulness": 0.95,
        "answer_relevancy": 0.90,
        "context_precision": 0.85,
        "context_recall": 0.80,
    }


def score_case_with_one_error(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> dict[str, float]:
    if "track" in question.lower():
        raise RuntimeError("The output is incomplete due to a max_tokens length limit.")
    return score_case(question, answer, contexts, ground_truth)


def test_ragas_run_persists_metrics_errors_and_status(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "support_eval_v1.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "case_001",
                    "question": "How can a customer track a submitted ticket?",
                    "ground_truth": "Use the generated tracking code.",
                },
                {
                    "case_id": "case_002",
                    "question": "What should support do for a duplicate payment issue?",
                    "ground_truth": "Verify payment and follow the duplicate charge process.",
                },
            ]
        ),
        encoding="utf-8",
    )
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(eval_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(settings, "ragas_dataset_path", str(dataset_path))
    store = InMemoryEvaluationStore()
    service = RagasEvalService(
        knowledge_service=FakeKnowledgeService(),
        metric_scorer=score_case,
        store=store,
    )
    run_id = service.create_eval_run(
        trigger_type="manual",
        started_by_agent_id="agent_001",
        started_by_agent_name="Support Manager",
    )

    service.run_ragas_evaluation_for_run(run_id)

    run = service.get_run(run_id)
    metrics = service.get_metrics(run_id)
    errors = service.get_errors(run_id)

    assert run is not None
    assert run["metadata"]["status"] == "failed"
    assert run["metadata"]["total_questions"] == 2
    assert run["metadata"]["passed_questions"] == 1
    assert len(metrics) == 4
    assert {metric["metric_name"] for metric in metrics} == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    }
    assert len(errors) == 1
    assert errors[0]["error_type"] == "multiple_rag_failures"
    assert errors[0]["metadata"]["case_id"] == "case_001"


def test_eval_run_dataset_identity_comes_from_dataset_path(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "ragas_dataset_path",
        "./evals/datasets/support_eval_v2.json",
    )
    store = InMemoryEvaluationStore()
    service = RagasEvalService(
        knowledge_service=FakeKnowledgeService(),
        metric_scorer=score_case,
        store=store,
    )

    run_id = service.create_eval_run(trigger_type="manual")
    run = service.get_run(run_id)

    assert run is not None
    assert run["dataset_name"] == "support_eval"
    assert run["dataset_version"] == "v2"


def test_eval_run_dataset_identity_falls_back_for_unversioned_path(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ragas_dataset_path", "./evals/datasets/custom.json")
    store = InMemoryEvaluationStore()
    service = RagasEvalService(
        knowledge_service=FakeKnowledgeService(),
        metric_scorer=score_case,
        store=store,
    )

    run_id = service.create_eval_run(trigger_type="manual")
    run = service.get_run(run_id)

    assert run is not None
    assert run["dataset_name"] == "custom"
    assert run["dataset_version"] == "v1"


def test_ragas_run_continues_when_one_case_evaluator_fails(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "support_eval_v1.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "case_001",
                    "question": "How can a customer track a submitted ticket?",
                    "ground_truth": "Use the generated tracking code.",
                },
                {
                    "case_id": "case_002",
                    "question": "What should support do for a duplicate payment issue?",
                    "ground_truth": "Verify payment and follow the duplicate charge process.",
                },
            ]
        ),
        encoding="utf-8",
    )
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(eval_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(settings, "ragas_dataset_path", str(dataset_path))
    store = InMemoryEvaluationStore()
    service = RagasEvalService(
        knowledge_service=FakeKnowledgeService(),
        metric_scorer=score_case_with_one_error,
        store=store,
    )
    run_id = service.create_eval_run(trigger_type="manual")

    service.run_ragas_evaluation_for_run(run_id)

    run = service.get_run(run_id)
    errors = service.get_errors(run_id)

    assert run is not None
    assert run["metadata"]["status"] == "failed"
    assert run["metadata"]["processed_questions"] == 2
    assert run["metadata"]["progress_percent"] == 100
    assert len(service.get_metrics(run_id)) == 4
    assert len(errors) == 1
    assert errors[0]["error_type"] == "evaluation_error"
    assert "max_tokens" in errors[0]["metadata"]["evaluation_error"]


def test_error_resolution_and_agent_feedback() -> None:
    store = InMemoryEvaluationStore()
    service = RagasEvalService(
        knowledge_service=FakeKnowledgeService(),
        metric_scorer=score_case,
        store=store,
    )
    run_id = service.create_eval_run(trigger_type="manual")
    error_id = f"err_{run_id}_case_001"
    store.insert(
        "error_analysis",
        {
            "id": error_id,
            "module": "rag_service",
            "run_id": run_id,
            "error_type": "low_faithfulness",
            "severity": "medium",
            "description": "Low faithfulness",
            "expected_behavior": "Expected",
            "actual_behavior": "Actual",
            "resolved": False,
            "resolved_at": None,
            "resolution_notes": None,
            "metadata": {"case_id": "case_001"},
            "created_at": service._now().isoformat(),
        },
    )

    assert service.resolve_error(error_id, "Updated retrieval content")
    feedback_id = service.save_agent_feedback(
        error_id,
        {
            "action": "needs_fix",
            "rating": 2,
            "feedback_note": "Needs a clearer answer",
            "edited_text": "Use the generated tracking code.",
            "agent_id": "agent_001",
            "agent_name": "Support Manager",
        },
    )

    error = service.get_error(error_id)

    assert error is not None
    assert error["resolved"] is True
    assert error["resolution_notes"] == "Updated retrieval content"
    assert feedback_id is not None
    assert len(store.tables["agent_feedback"]) == 1
    assert not store.tables["evaluation_metrics"]
