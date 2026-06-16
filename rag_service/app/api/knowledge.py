import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_api_key
from app.core.config import settings
from app.db.database import SessionLocal
from app.schemas.knowledge import (
    DocumentDetail,
    DocumentListResponse,
    DocumentResponse,
    ReindexRequest,
    ReindexResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.knowledge_service import KnowledgeService
from app.services.ragas_eval_service import start_ragas_evaluation_after_upload

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_api_key)])
_knowledge_service: KnowledgeService | None = None
logger = logging.getLogger(__name__)


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    source_type: str = Form(...),
    category: str | None = Form(None),
    access_level: str = Form("support"),
    language: str = Form("en"),
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Any:
    try:
        doc = service.create_upload_record(
            db=db,
            file=file,
            title=title,
            source_type=source_type,
        )
        background_tasks.add_task(
            _index_uploaded_document,
            doc.doc_id,
            category or source_type,
            access_level,
            language,
        )
        return DocumentResponse(
            doc_id=doc.doc_id,
            title=doc.title,
            source_type=doc.source_type,
            file_name=doc.file_name,
            version=doc.version,
            status=doc.indexing_status,
            chunk_count=0,
            indexing_error=doc.indexing_error,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/reindex", response_model=ReindexResponse)
def reindex_documents(
    payload: ReindexRequest,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ReindexResponse:
    indexed_count = service.reindex(db=db, doc_id=payload.doc_id, force=payload.force)
    return ReindexResponse(status="completed", indexed_documents=indexed_count)


@router.post("/search", response_model=SearchResponse)
def search_knowledge(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> SearchResponse:
    return service.search(
        db=db,
        request=payload,
        allowed_access_levels=settings.allowed_access_levels,
    )


@router.get("/docs", response_model=DocumentListResponse)
def list_documents(
    source_type: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentListResponse:
    return service.list_documents(
        db=db,
        source_type=source_type,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/docs/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    doc = service.get_document(db=db, doc_id=doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.get("/docs/{doc_id}/status")
def get_document_status(
    doc_id: str,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    doc = service.get_document(db=db, doc_id=doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "doc_id": doc.doc_id,
        "indexing_status": doc.indexing_status,
        "indexing_error": doc.indexing_error,
        "chunk_count": doc.chunk_count,
        "updated_at": doc.updated_at,
    }


@router.delete("/docs/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    deleted_chunks = service.delete_document(db=db, doc_id=doc_id)
    if deleted_chunks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"doc_id": doc_id, "status": "deleted", "deleted_chunks": deleted_chunks}


def _index_uploaded_document(
    doc_id: str,
    category: str,
    access_level: str,
    language: str,
) -> None:
    db = SessionLocal()
    try:
        get_knowledge_service().index_document_by_id(
            db=db,
            doc_id=doc_id,
            category=category,
            access_level=access_level,
            language=language,
        )
        try:
            start_ragas_evaluation_after_upload(uploaded_document_id=doc_id)
        except Exception:
            logger.exception("Could not start automatic Ragas evaluation for document %s", doc_id)
    finally:
        db.close()
