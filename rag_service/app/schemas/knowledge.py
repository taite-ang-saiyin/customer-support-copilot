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
    indexing_error: str | None = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doc_id: str
    title: str
    source_type: str
    file_name: str
    version: int
    indexing_status: str
    indexing_error: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    file_path: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int


class HelpArticleSection(BaseModel):
    title: str
    body: str


class HelpArticleResponse(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    updatedDate: str
    helpfulCount: int | None
    unhelpfulCount: int | None
    contentSections: list[HelpArticleSection]


class HelpArticleListResponse(BaseModel):
    articles: list[HelpArticleResponse]


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
