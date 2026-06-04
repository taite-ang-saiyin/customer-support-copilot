from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
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

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
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
        return service.upload_and_index(
            db=db,
            file=file,
            title=title,
            source_type=source_type,
            category=category,
            access_level=access_level,
            language=language,
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
    return service.search(db=db, request=payload)


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
