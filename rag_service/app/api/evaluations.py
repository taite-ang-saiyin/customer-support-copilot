from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.deps import require_api_key
from app.schemas.evaluation import (
    EvaluationErrorRecord,
    EvaluationFeedbackRequest,
    EvaluationFeedbackResponse,
    EvaluationMetricRecord,
    EvaluationRunRecord,
    EvaluationRunRequest,
    EvaluationRunStarted,
    ResolveEvaluationErrorRequest,
)
from app.services.ragas_eval_service import (
    RagasEvalService,
    run_ragas_evaluation_background,
)

router = APIRouter(
    prefix="/evaluations/ragas",
    tags=["ragas-evaluations"],
    dependencies=[Depends(require_api_key)],
)
_evaluation_service: RagasEvalService | None = None


def get_evaluation_service() -> RagasEvalService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = RagasEvalService()
    return _evaluation_service


@router.post("/run", response_model=EvaluationRunStarted, status_code=status.HTTP_202_ACCEPTED)
def start_manual_evaluation(
    payload: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> EvaluationRunStarted:
    run_id = service.create_eval_run(
        trigger_type="manual",
        started_by_agent_id=payload.started_by_agent_id,
        started_by_agent_name=payload.started_by_agent_name,
        notes=payload.notes,
    )
    background_tasks.add_task(run_ragas_evaluation_background, run_id)
    return EvaluationRunStarted(message="Evaluation started", run_id=run_id)


@router.get("/runs", response_model=list[EvaluationRunRecord])
def list_evaluation_runs(
    limit: int = Query(default=50, ge=1, le=200),
    service: RagasEvalService = Depends(get_evaluation_service),
) -> list[dict[str, Any]]:
    return service.list_runs(limit=limit)


@router.get("/runs/{run_id}", response_model=EvaluationRunRecord)
def get_evaluation_run(
    run_id: str,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")
    return run


@router.get("/runs/{run_id}/metrics", response_model=list[EvaluationMetricRecord])
def get_evaluation_metrics(
    run_id: str,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> list[dict[str, Any]]:
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")
    return service.get_metrics(run_id)


@router.get("/runs/{run_id}/errors", response_model=list[EvaluationErrorRecord])
def get_evaluation_errors(
    run_id: str,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> list[dict[str, Any]]:
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")
    return service.get_errors(run_id)


@router.patch("/errors/{error_id}/resolve", response_model=EvaluationErrorRecord)
def resolve_evaluation_error(
    error_id: str,
    payload: ResolveEvaluationErrorRequest,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    if not service.resolve_error(error_id, payload.resolution_notes):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation error not found",
        )
    error = service.get_error(error_id)
    if error is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation error not found",
        )
    return error


@router.post(
    "/errors/{error_id}/feedback",
    response_model=EvaluationFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_evaluation_feedback(
    error_id: str,
    payload: EvaluationFeedbackRequest,
    service: RagasEvalService = Depends(get_evaluation_service),
) -> EvaluationFeedbackResponse:
    feedback_id = service.save_agent_feedback(error_id, payload.model_dump())
    if feedback_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation error not found",
        )
    return EvaluationFeedbackResponse(message="Feedback saved", feedback_id=feedback_id)
