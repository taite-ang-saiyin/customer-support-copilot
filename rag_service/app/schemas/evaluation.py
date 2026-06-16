from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    started_by_agent_id: str | None = None
    started_by_agent_name: str | None = None
    notes: str | None = None


class EvaluationRunStarted(BaseModel):
    message: str
    run_id: str


class EvaluationRunRecord(BaseModel):
    id: str
    run_name: str
    module: str
    model_name: str | None
    prompt_version: str
    retrieval_version: str
    dataset_name: str
    dataset_version: str
    mlflow_run_id: str | None
    notes: str | None
    metadata: dict[str, Any]
    created_at: datetime


class EvaluationMetricRecord(BaseModel):
    id: str
    run_id: str
    metric_name: str
    metric_value: float
    metric_unit: str
    created_at: datetime


class EvaluationErrorRecord(BaseModel):
    id: str
    module: str
    run_id: str
    error_type: str
    severity: str
    description: str
    expected_behavior: str
    actual_behavior: str
    resolved: bool
    resolved_at: datetime | None
    resolution_notes: str | None
    metadata: dict[str, Any]
    created_at: datetime


class ResolveEvaluationErrorRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=1)


class EvaluationFeedbackRequest(BaseModel):
    action: Literal["needs_fix", "accepted", "dismissed"]
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_note: str | None = None
    edited_text: str | None = None
    agent_id: str
    agent_name: str


class EvaluationFeedbackResponse(BaseModel):
    message: str
    feedback_id: str
