import asyncio
import json
import math
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.schemas.knowledge import SearchRequest
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_service import KnowledgeService
from app.services.supabase_eval_store import SupabaseEvaluationStore

THRESHOLDS = {
    "faithfulness": 0.80,
    "answer_relevancy": 0.75,
    "context_precision": 0.70,
    "context_recall": 0.70,
}

MetricScorer = Callable[[str, str, list[str], str], dict[str, float]]


class RagasEvalService:
    def __init__(
        self,
        knowledge_service: KnowledgeService | None = None,
        metric_scorer: MetricScorer | None = None,
        store: SupabaseEvaluationStore | None = None,
    ) -> None:
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.metric_scorer = metric_scorer or self._score_with_ragas
        self.store = store or SupabaseEvaluationStore()

    def create_eval_run(
        self,
        trigger_type: str,
        started_by_agent_id: str | None = None,
        started_by_agent_name: str | None = None,
        uploaded_document_id: str | None = None,
        notes: str | None = None,
    ) -> str:
        now = self._now()
        run_id = self._run_id(now)
        dataset_name, dataset_version = self._dataset_identity(settings.ragas_dataset_path)
        metadata = {
            "trigger_type": trigger_type,
            "status": "running",
            "total_questions": 0,
            "passed_questions": 0,
            "failed_questions": 0,
            "started_by_agent_id": started_by_agent_id,
            "started_by_agent_name": started_by_agent_name,
            "uploaded_document_id": uploaded_document_id,
            "started_at": now.isoformat(),
            "completed_at": None,
            "thresholds": THRESHOLDS,
            "error_message": None,
            "answer_mode": "extractive_top_context",
            "current_step": "queued",
            "current_case_id": None,
            "processed_questions": 0,
            "progress_percent": 0,
        }
        self.store.insert(
            "evaluation_runs",
            {
                "id": run_id,
                "run_name": f"Ragas {trigger_type} {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "module": "rag_service",
                "model_name": settings.ragas_evaluator_model,
                "prompt_version": settings.ragas_prompt_version,
                "retrieval_version": settings.ragas_retrieval_version,
                "dataset_name": dataset_name,
                "dataset_version": dataset_version,
                "mlflow_run_id": None,
                "notes": notes or f"Ragas evaluation triggered by {trigger_type}",
                "metadata": metadata,
                "created_at": now.isoformat(),
            },
        )
        return run_id

    def run_ragas_evaluation_for_run(self, run_id: str) -> None:
        db = SessionLocal()
        try:
            cases = self.load_eval_dataset()
            case_results: list[dict[str, Any]] = []
            self.update_eval_run_progress(
                run_id=run_id,
                total_questions=len(cases),
                processed_questions=0,
                current_step="loaded_dataset",
            )

            for index, case in enumerate(cases, start=1):
                self.update_eval_run_progress(
                    run_id=run_id,
                    total_questions=len(cases),
                    processed_questions=index - 1,
                    current_case_id=case["case_id"],
                    current_step="retrieving_context",
                )
                rag_output = self.call_existing_rag_pipeline(db, case["question"])
                self.update_eval_run_progress(
                    run_id=run_id,
                    total_questions=len(cases),
                    processed_questions=index - 1,
                    current_case_id=case["case_id"],
                    current_step="scoring_metrics",
                )
                evaluation_error = None
                try:
                    scores = self.metric_scorer(
                        case["question"],
                        rag_output["answer"],
                        rag_output["contexts"],
                        case["ground_truth"],
                    )
                    failure_reasons = self.determine_failure_reasons(scores)
                except Exception as exc:
                    evaluation_error = str(exc)
                    scores = {metric_name: 0.0 for metric_name in THRESHOLDS}
                    failure_reasons = ["evaluation_error"]
                case_results.append(
                    {
                        **case,
                        **rag_output,
                        "scores": scores,
                        "passed": not self._is_case_failure(scores),
                        "failure_reasons": failure_reasons,
                        "evaluation_error": evaluation_error,
                    }
                )
                self.update_eval_run_progress(
                    run_id=run_id,
                    total_questions=len(cases),
                    processed_questions=index,
                    current_case_id=case["case_id"],
                    current_step="case_complete",
                )

            self.update_eval_run_progress(
                run_id=run_id,
                total_questions=len(cases),
                processed_questions=len(cases),
                current_step="saving_results",
            )
            average_metrics = self._average_metrics(case_results)
            self.save_average_metrics(run_id, average_metrics)
            self.save_failed_cases(run_id, case_results)
            passed_questions = sum(1 for result in case_results if result["passed"])
            run_status = (
                "passed"
                if average_metrics["faithfulness"] >= THRESHOLDS["faithfulness"]
                and average_metrics["answer_relevancy"] >= THRESHOLDS["answer_relevancy"]
                else "failed"
            )
            self.update_eval_run_status(
                run_id=run_id,
                status=run_status,
                total_questions=len(case_results),
                passed_questions=passed_questions,
                failed_questions=len(case_results) - passed_questions,
            )
        except Exception as exc:
            self.update_eval_run_status(
                run_id=run_id,
                status="error",
                error_message=str(exc),
            )
        finally:
            db.close()

    def load_eval_dataset(self, path: str | None = None) -> list[dict[str, str]]:
        dataset_path = Path(path or settings.ragas_dataset_path)
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            raise ValueError("Ragas evaluation dataset must be a non-empty JSON array")

        required_fields = {"case_id", "question", "ground_truth"}
        for item in data:
            if not isinstance(item, dict) or not required_fields.issubset(item):
                raise ValueError(
                    "Each Ragas dataset item must include case_id, question, and ground_truth"
                )
        return data

    def call_existing_rag_pipeline(self, db: Session, question: str) -> dict[str, Any]:
        response = self.knowledge_service.search(
            db=db,
            request=SearchRequest(query=question, top_k=settings.ragas_eval_top_k),
            allowed_access_levels=settings.allowed_access_levels,
        )
        contexts = [result.text for result in response.results]
        if not contexts:
            contexts = ["No relevant knowledge was retrieved."]
        answer = contexts[0]
        return {"answer": answer, "contexts": contexts}

    def save_average_metrics(
        self,
        run_id: str,
        average_metrics: dict[str, float],
    ) -> None:
        now = self._now()
        self.store.delete("evaluation_metrics", {"run_id": run_id})
        self.store.insert(
            "evaluation_metrics",
            [
                {
                    "id": f"metric_{run_id}_{metric_name}",
                    "run_id": run_id,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "metric_unit": "score_0_to_1",
                    "created_at": now.isoformat(),
                }
                for metric_name, metric_value in average_metrics.items()
            ],
        )

    def save_failed_cases(
        self,
        run_id: str,
        case_results: list[dict[str, Any]],
    ) -> None:
        now = self._now()
        rows = []
        for result in case_results:
            if result["passed"]:
                continue
            failure_reasons = result["failure_reasons"]
            rows.append(
                {
                    "id": f"err_{run_id}_{result['case_id']}",
                    "module": "rag_service",
                    "run_id": run_id,
                    "error_type": self._error_type(failure_reasons),
                    "severity": self.determine_severity(result["scores"]),
                    "description": (
                        f"Ragas evaluation failed for {result['case_id']}: "
                        f"{', '.join(failure_reasons)}"
                    ),
                    "expected_behavior": result["ground_truth"],
                    "actual_behavior": result["answer"],
                    "resolved": False,
                    "resolved_at": None,
                    "resolution_notes": None,
                    "metadata": {
                        "case_id": result["case_id"],
                        "question": result["question"],
                        "ground_truth": result["ground_truth"],
                        "generated_answer": result["answer"],
                        "retrieved_contexts": result["contexts"],
                        "scores": result["scores"],
                        "passed": False,
                        "failure_reasons": failure_reasons,
                        "evaluation_error": result.get("evaluation_error"),
                    },
                    "created_at": now.isoformat(),
                }
            )
        if rows:
            self.store.insert("error_analysis", rows)

    def update_eval_run_status(
        self,
        run_id: str,
        status: str,
        total_questions: int | None = None,
        passed_questions: int | None = None,
        failed_questions: int | None = None,
        error_message: str | None = None,
    ) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        metadata = dict(run["metadata"] or {})
        metadata["status"] = status
        metadata["current_step"] = status
        metadata["current_case_id"] = None
        metadata["completed_at"] = self._now().isoformat()
        metadata["error_message"] = error_message
        if total_questions is not None:
            metadata["total_questions"] = total_questions
        if passed_questions is not None:
            metadata["passed_questions"] = passed_questions
        if failed_questions is not None:
            metadata["failed_questions"] = failed_questions
        self.store.update(
            "evaluation_runs",
            {"metadata": metadata},
            {"id": run_id, "module": "rag_service"},
        )

    def update_eval_run_progress(
        self,
        run_id: str,
        total_questions: int,
        processed_questions: int,
        current_step: str,
        current_case_id: str | None = None,
    ) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        metadata = dict(run["metadata"] or {})
        metadata["status"] = "running"
        metadata["total_questions"] = total_questions
        metadata["processed_questions"] = processed_questions
        metadata["current_case_id"] = current_case_id
        metadata["current_step"] = current_step
        metadata["progress_percent"] = self._progress_percent(
            processed_questions,
            total_questions,
        )
        metadata["updated_at"] = self._now().isoformat()
        self.store.update(
            "evaluation_runs",
            {"metadata": metadata},
            {"id": run_id, "module": "rag_service"},
        )

    def determine_failure_reasons(self, scores: dict[str, float]) -> list[str]:
        return [
            f"low_{metric_name}"
            for metric_name, threshold in THRESHOLDS.items()
            if scores.get(metric_name, 0.0) < threshold
        ]

    def determine_severity(self, scores: dict[str, float]) -> str:
        primary_failures = sum(
            scores.get(metric_name, 0.0) < THRESHOLDS[metric_name]
            for metric_name in ("faithfulness", "answer_relevancy")
        )
        if primary_failures > 1 or min(
            scores.get("faithfulness", 0.0),
            scores.get("answer_relevancy", 0.0),
        ) < 0.50:
            return "high"
        if primary_failures == 1:
            return "medium"
        return "low"

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.select(
            "evaluation_runs",
            filters={"module": "rag_service"},
            order="created_at.desc",
            limit=limit,
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        rows = self.store.select(
            "evaluation_runs",
            filters={"id": run_id, "module": "rag_service"},
            limit=1,
        )
        return rows[0] if rows else None

    def get_metrics(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.select(
            "evaluation_metrics",
            filters={"run_id": run_id},
            order="metric_name.asc",
        )

    def get_errors(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.select(
            "error_analysis",
            filters={"run_id": run_id, "module": "rag_service"},
            order="created_at.asc",
        )

    def get_error(self, error_id: str) -> dict[str, Any] | None:
        rows = self.store.select(
            "error_analysis",
            filters={"id": error_id, "module": "rag_service"},
            limit=1,
        )
        return rows[0] if rows else None

    def resolve_error(self, error_id: str, resolution_notes: str) -> bool:
        rows = self.store.update(
            "error_analysis",
            {
                "resolved": True,
                "resolved_at": self._now().isoformat(),
                "resolution_notes": resolution_notes,
            },
            {"id": error_id, "module": "rag_service"},
        )
        return bool(rows)

    def save_agent_feedback(
        self,
        error_id: str,
        payload: dict[str, Any],
    ) -> str | None:
        if self.get_error(error_id) is None:
            return None

        feedback_id = f"feedback_{uuid.uuid4().hex}"
        self.store.insert(
            "agent_feedback",
            {
                "id": feedback_id,
                "object_type": "error_analysis",
                "object_id": error_id,
                "action": payload["action"],
                "rating": payload.get("rating"),
                "feedback_note": payload.get("feedback_note"),
                "edited_text": payload.get("edited_text"),
                "agent_id": payload["agent_id"],
                "agent_name": payload["agent_name"],
                "created_at": self._now().isoformat(),
            },
        )
        return feedback_id

    def _score_with_ragas(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> dict[str, float]:
        if not settings.ragas_evaluator_model:
            raise RuntimeError(
                "RAGAS_EVALUATOR_MODEL is required to run LLM-based Ragas metrics"
            )
        if not settings.ragas_evaluator_api_key and not settings.ragas_evaluator_base_url:
            raise RuntimeError(
                "Set RAGAS_EVALUATOR_API_KEY or RAGAS_EVALUATOR_BASE_URL "
                "for the Ragas evaluator LLM"
            )

        from openai import AsyncOpenAI
        from ragas.embeddings.base import BaseRagasEmbedding
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )

        class LocalEmbeddings(BaseRagasEmbedding):
            def __init__(self) -> None:
                super().__init__()
                self.service = EmbeddingService()

            def embed_text(self, text: str) -> list[float]:
                return self.service.embed_query(text)

            async def aembed_text(self, text: str) -> list[float]:
                return await asyncio.to_thread(self.embed_text, text)

        client_kwargs: dict[str, Any] = {
            "api_key": settings.ragas_evaluator_api_key or "local-evaluator",
        }
        if settings.ragas_evaluator_base_url:
            client_kwargs["base_url"] = settings.ragas_evaluator_base_url
        evaluator_client = AsyncOpenAI(**client_kwargs)
        evaluator_llm = llm_factory(
            settings.ragas_evaluator_model,
            provider=settings.ragas_evaluator_provider or "openai",
            client=evaluator_client,
            max_tokens=settings.ragas_evaluator_max_tokens,
            temperature=0,
        )
        evaluator_embeddings = LocalEmbeddings()
        scorers = {
            "faithfulness": Faithfulness(llm=evaluator_llm),
            "answer_relevancy": AnswerRelevancy(
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
            ),
            "context_precision": ContextPrecision(llm=evaluator_llm),
            "context_recall": ContextRecall(llm=evaluator_llm),
        }
        return {
            "faithfulness": self._metric_value(
                scorers["faithfulness"].score(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                )
            ),
            "answer_relevancy": self._metric_value(
                scorers["answer_relevancy"].score(
                    user_input=question,
                    response=answer,
                )
            ),
            "context_precision": self._metric_value(
                scorers["context_precision"].score(
                    user_input=question,
                    reference=ground_truth,
                    retrieved_contexts=contexts,
                )
            ),
            "context_recall": self._metric_value(
                scorers["context_recall"].score(
                    user_input=question,
                    reference=ground_truth,
                    retrieved_contexts=contexts,
                )
            ),
        }

    @staticmethod
    def _metric_value(result: Any) -> float:
        value = getattr(result, "value", result)
        number = float(value)
        if math.isnan(number):
            return 0.0
        return round(number, 6)

    @staticmethod
    def _average_metrics(case_results: list[dict[str, Any]]) -> dict[str, float]:
        if not case_results:
            return {metric_name: 0.0 for metric_name in THRESHOLDS}
        return {
            metric_name: round(
                sum(result["scores"][metric_name] for result in case_results)
                / len(case_results),
                6,
            )
            for metric_name in THRESHOLDS
        }

    @staticmethod
    def _is_case_failure(scores: dict[str, float]) -> bool:
        return (
            scores.get("faithfulness", 0.0) < THRESHOLDS["faithfulness"]
            or scores.get("answer_relevancy", 0.0) < THRESHOLDS["answer_relevancy"]
        )

    @staticmethod
    def _error_type(failure_reasons: list[str]) -> str:
        if len(failure_reasons) > 1:
            return "multiple_rag_failures"
        return failure_reasons[0] if failure_reasons else "multiple_rag_failures"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _run_id(now: datetime) -> str:
        return f"eval_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _progress_percent(processed_questions: int, total_questions: int) -> int:
        if total_questions <= 0:
            return 0
        return min(100, round((processed_questions / total_questions) * 100))

    @staticmethod
    def _dataset_identity(dataset_path: str) -> tuple[str, str]:
        stem = Path(dataset_path).stem
        match = re.search(r"(.+?)_(v\d+)$", stem)
        if not match:
            return stem, "v1"
        return match.group(1), match.group(2)


def run_ragas_evaluation_background(run_id: str) -> None:
    RagasEvalService().run_ragas_evaluation_for_run(run_id)


def start_ragas_evaluation_after_upload(uploaded_document_id: str) -> str | None:
    if not settings.ragas_auto_eval_enabled:
        return None
    service = RagasEvalService()
    run_id = service.create_eval_run(
        trigger_type="knowledge_upload",
        uploaded_document_id=uploaded_document_id,
        notes=f"Automatic evaluation after indexing document {uploaded_document_id}",
    )
    service.run_ragas_evaluation_for_run(run_id)
    return run_id
