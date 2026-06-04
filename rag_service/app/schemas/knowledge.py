from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    source_type: str
    file_name: str
    version: int
    status: str
    chunk_count: int


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doc_id: str
    title: str
    source_type: str
    file_name: str
    version: int
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    file_path: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int


class ReindexRequest(BaseModel):
    doc_id: str | None = None
    force: bool = False


class ReindexResponse(BaseModel):
    status: str
    indexed_documents: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(None, ge=1, le=20)
    filters: dict[str, Any] | None = None


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    section: str
    score: float
    text: str
    citation: str
    source: str
    category: str
    language: str
    access_level: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    top_k: int
    log_id: str
