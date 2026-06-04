import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import KnowledgeChunk, KnowledgeDoc, RetrievalLog, utcnow
from app.schemas.knowledge import (
    DocumentDetail,
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.embedding_service import EmbeddingService
from app.services.pdf_extractor import extract_pdf_to_markdown
from app.services.text_processing import SUPPORTED_EXTENSIONS, chunk_markdown, extract_text
from app.services.vector_store import VectorStore


class KnowledgeService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()

    def upload_and_index(
        self,
        db: Session,
        file: UploadFile,
        title: str,
        source_type: str,
        category: str | None,
        access_level: str,
        language: str,
    ) -> DocumentResponse:
        file_path = self._save_upload(file)
        doc = KnowledgeDoc(
            doc_id=self._new_id("doc"),
            title=title,
            source_type=source_type,
            file_name=file.filename or Path(file_path).name,
            file_path=file_path,
            version=1,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunks = self._index_document(
            db=db,
            doc=doc,
            category=category or source_type,
            access_level=access_level,
            language=language,
        )

        return DocumentResponse(
            doc_id=doc.doc_id,
            title=doc.title,
            source_type=doc.source_type,
            file_name=doc.file_name,
            version=doc.version,
            status="indexed",
            chunk_count=chunks,
        )

    def reindex(self, db: Session, doc_id: str | None = None, force: bool = False) -> int:
        query = select(KnowledgeDoc)
        if doc_id:
            query = query.where(KnowledgeDoc.doc_id == doc_id)
        docs = list(db.scalars(query).all())
        for doc in docs:
            category = doc.source_type
            existing_chunk = db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.doc_id)
            ).first()
            if existing_chunk:
                category = existing_chunk.category
            self._index_document(
                db=db,
                doc=doc,
                category=category,
                access_level=existing_chunk.access_level if existing_chunk else "support",
                language=existing_chunk.language if existing_chunk else "en",
                replace_existing=True,
                force=force,
            )
        return len(docs)

    def search(self, db: Session, request: SearchRequest) -> SearchResponse:
        top_k = request.top_k or settings.top_k
        query_embedding = self.embedding_service.embed_query(request.query)
        matches = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=request.filters,
        )

        chunk_ids = [match["chunk_id"] for match in matches]
        chunks_by_id = {
            chunk.chunk_id: chunk
            for chunk in db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.chunk_id.in_(chunk_ids))
            ).all()
        } if chunk_ids else {}

        results: list[SearchResult] = []
        for match in matches:
            chunk = chunks_by_id.get(match["chunk_id"])
            if not chunk:
                continue
            doc = chunk.document
            citation = self._citation(doc.title, chunk.section_title)
            results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    doc_id=doc.doc_id,
                    title=doc.title,
                    section=chunk.section_title,
                    score=round(float(match["score"]), 4),
                    text=chunk.chunk_text,
                    citation=citation,
                    source=doc.file_name,
                    category=chunk.category,
                    language=chunk.language,
                    access_level=chunk.access_level,
                )
            )

        log = RetrievalLog(
            log_id=self._new_id("log"),
            query=request.query,
            retrieved_chunk_ids=[result.chunk_id for result in results],
            scores=[result.score for result in results],
        )
        db.add(log)
        db.commit()

        return SearchResponse(query=request.query, results=results, top_k=top_k, log_id=log.log_id)

    def list_documents(
        self,
        db: Session,
        source_type: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentListResponse:
        query = select(KnowledgeDoc)
        if source_type:
            query = query.where(KnowledgeDoc.source_type == source_type)
        if category:
            query = query.join(KnowledgeChunk).where(KnowledgeChunk.category == category)

        all_items = list(db.scalars(query).unique().all())
        page_items = all_items[offset : offset + limit]
        return DocumentListResponse(
            items=[DocumentSummary.model_validate(item) for item in page_items],
            total=len(all_items),
        )

    def get_document(self, db: Session, doc_id: str) -> DocumentDetail | None:
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None:
            return None
        return DocumentDetail(
            doc_id=doc.doc_id,
            title=doc.title,
            source_type=doc.source_type,
            file_name=doc.file_name,
            file_path=doc.file_path,
            version=doc.version,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            chunk_count=len(doc.chunks),
        )

    def delete_document(self, db: Session, doc_id: str) -> int | None:
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None:
            return None
        deleted_chunks = len(doc.chunks)
        self.vector_store.delete_document(doc_id)
        db.delete(doc)
        db.commit()
        return deleted_chunks

    def _index_document(
        self,
        db: Session,
        doc: KnowledgeDoc,
        category: str,
        access_level: str,
        language: str,
        replace_existing: bool = True,
        force: bool = False,
    ) -> int:
        if replace_existing:
            self.vector_store.delete_document(doc.doc_id)
            db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc.doc_id).delete()
            db.commit()

        text = self._extract_document_text(doc)
        text_chunks = chunk_markdown(text)
        chunk_rows = [
            KnowledgeChunk(
                chunk_id=self._new_id("chunk"),
                doc_id=doc.doc_id,
                chunk_text=text_chunk.text,
                section_title=text_chunk.section_title,
                category=category,
                language=language,
                access_level=access_level,
                chunk_index=text_chunk.chunk_index,
            )
            for text_chunk in text_chunks
        ]
        db.add_all(chunk_rows)
        doc.updated_at = utcnow()
        if force:
            doc.version += 1
        db.commit()

        embeddings = self.embedding_service.embed_texts([chunk.chunk_text for chunk in chunk_rows])
        self.vector_store.upsert_chunks(
            chunk_ids=[chunk.chunk_id for chunk in chunk_rows],
            embeddings=embeddings,
            documents=[chunk.chunk_text for chunk in chunk_rows],
            metadatas=[
                {
                    "doc_id": doc.doc_id,
                    "source": doc.file_name,
                    "section": chunk.section_title,
                    "category": chunk.category,
                    "language": chunk.language,
                    "access_level": chunk.access_level,
                }
                for chunk in chunk_rows
            ],
        )
        return len(chunk_rows)

    def _extract_document_text(self, doc: KnowledgeDoc) -> str:
        if Path(doc.file_path).suffix.lower() != ".pdf":
            return extract_text(doc.file_path)

        cleaned_markdown = extract_pdf_to_markdown(doc.file_path, mode="blocks")
        processed_path = self._processed_markdown_path(doc.file_name)
        processed_path.parent.mkdir(parents=True, exist_ok=True)
        processed_path.write_text(cleaned_markdown, encoding="utf-8")
        return cleaned_markdown

    @staticmethod
    def _processed_markdown_path(file_name: str) -> Path:
        stem = Path(file_name).stem
        return Path(settings.upload_dir) / "processed" / f"{stem}.cleaned.md"

    def _save_upload(self, file: UploadFile) -> str:
        original_name = file.filename or "knowledge.txt"
        extension = Path(original_name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError("Only Markdown, txt, and PDF files are supported")

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{Path(original_name).name}"
        file_path = upload_dir / safe_name

        with file_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        return os.fspath(file_path)

    @staticmethod
    def _citation(title: str, section_title: str) -> str:
        return f"{title} > {section_title}"

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"
