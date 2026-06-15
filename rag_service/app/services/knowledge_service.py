import os
import re
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
from app.services.reranker_service import RerankerService
from app.services.text_processing import SUPPORTED_EXTENSIONS, chunk_markdown, extract_text
from app.services.vector_store import VectorStore


class KnowledgeService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        reranker_service: RerankerService | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.reranker_service = reranker_service or RerankerService()

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
        doc = self.create_upload_record(
            db=db,
            file=file,
            title=title,
            source_type=source_type,
        )
        chunks = self._index_document(
            db=db,
            doc=doc,
            category=category or source_type,
            access_level=access_level,
            language=language,
        )

        return self._document_response(doc=doc, chunk_count=chunks)

    def create_upload_record(
        self,
        db: Session,
        file: UploadFile,
        title: str,
        source_type: str,
    ) -> KnowledgeDoc:
        file_path, safe_original_name = self._save_upload(file)
        doc = KnowledgeDoc(
            doc_id=self._new_id("doc"),
            title=title,
            source_type=source_type,
            file_name=safe_original_name,
            file_path=file_path,
            version=1,
            indexing_status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    def index_document_by_id(
        self,
        db: Session,
        doc_id: str,
        category: str,
        access_level: str,
        language: str,
        force: bool = False,
    ) -> int:
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None:
            raise ValueError("Document not found")
        return self._index_document(
            db=db,
            doc=doc,
            category=category or doc.source_type,
            access_level=access_level,
            language=language,
            force=force,
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

    def search(
        self,
        db: Session,
        request: SearchRequest,
        allowed_access_levels: list[str] | None = None,
    ) -> SearchResponse:
        top_k = request.top_k or settings.top_k
        candidate_k = self._candidate_count(top_k)
        query_embedding = self.embedding_service.embed_query(request.query)
        filters = self._safe_search_filters(request.filters, allowed_access_levels)
        matches = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=candidate_k,
            filters=filters,
        )

        chunk_ids = [match["chunk_id"] for match in matches]
        chunks_by_id = {
            chunk.chunk_id: chunk
            for chunk in db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.chunk_id.in_(chunk_ids))
            ).all()
        } if chunk_ids else {}

        candidates: list[tuple[dict[str, Any], KnowledgeChunk]] = []
        for match in matches:
            chunk = chunks_by_id.get(match["chunk_id"])
            if not chunk:
                continue
            if allowed_access_levels is not None and chunk.access_level not in allowed_access_levels:
                continue
            candidates.append((match, chunk))

        candidates = self._rerank_candidates(request.query, candidates)

        results: list[SearchResult] = []
        for match, chunk in candidates[:top_k]:
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
            indexing_status=doc.indexing_status,
            indexing_error=doc.indexing_error,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            chunk_count=len(doc.chunks),
        )

    def delete_document(self, db: Session, doc_id: str) -> int | None:
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None:
            return None
        deleted_chunks = len(doc.chunks)
        file_paths = self._document_file_paths(doc)
        self.vector_store.delete_document(doc_id)
        db.delete(doc)
        db.commit()
        for file_path in file_paths:
            file_path.unlink(missing_ok=True)
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
        old_chunk_ids = [
            chunk_id
            for (chunk_id,) in db.query(KnowledgeChunk.chunk_id)
            .filter(KnowledgeChunk.doc_id == doc.doc_id)
            .all()
        ]
        doc.indexing_status = "processing"
        doc.indexing_error = None
        doc.updated_at = utcnow()
        db.commit()

        try:
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
            embeddings = self.embedding_service.embed_texts(
                [chunk.chunk_text for chunk in chunk_rows]
            )
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

            if replace_existing and old_chunk_ids:
                self._delete_vector_chunks(old_chunk_ids)
                db.query(KnowledgeChunk).filter(KnowledgeChunk.doc_id == doc.doc_id).delete()
            db.add_all(chunk_rows)
            doc.indexing_status = "indexed"
            doc.indexing_error = None
            doc.updated_at = utcnow()
            if force:
                doc.version += 1
            db.commit()
            db.refresh(doc)
            return len(chunk_rows)
        except Exception as exc:
            db.rollback()
            doc = db.get(KnowledgeDoc, doc.doc_id)
            if doc is not None:
                doc.indexing_status = "failed"
                doc.indexing_error = str(exc)[:2000]
                doc.updated_at = utcnow()
                db.commit()
            raise

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

    def _document_file_paths(self, doc: KnowledgeDoc) -> list[Path]:
        file_paths = [self._safe_upload_path(Path(doc.file_path))]
        if Path(doc.file_name).suffix.lower() == ".pdf":
            file_paths.append(self._safe_upload_path(self._processed_markdown_path(doc.file_name)))
        return file_paths

    @staticmethod
    def _safe_upload_path(file_path: Path) -> Path:
        upload_root = Path(settings.upload_dir).resolve()
        resolved_path = file_path.resolve()
        if not resolved_path.is_relative_to(upload_root):
            raise ValueError("Refusing to delete a file outside the upload directory")
        return resolved_path

    def _save_upload(self, file: UploadFile) -> tuple[str, str]:
        original_name = self._safe_original_filename(file.filename or "knowledge.txt")
        extension = Path(original_name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError("Unsupported file type. Allowed extensions: .md, .markdown, .txt, .pdf")

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix
        counter = 1

        while True:
            stored_name = original_name if counter == 1 else f"{stem}_{counter}{suffix}"
            file_path = upload_dir / stored_name
            try:
                output = file_path.open("xb")
                break
            except FileExistsError:
                counter += 1

        total_size = 0
        with output:
            while chunk := file.file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    output.close()
                    file_path.unlink(missing_ok=True)
                    raise ValueError(
                        f"Uploaded file is too large. Maximum size is "
                        f"{settings.max_upload_size_bytes} bytes."
                    )
                output.write(chunk)

        return os.fspath(file_path), stored_name

    def _delete_vector_chunks(self, chunk_ids: list[str]) -> None:
        delete_chunks = getattr(self.vector_store, "delete_chunks", None)
        if delete_chunks:
            delete_chunks(chunk_ids)
            return
        for chunk_id in chunk_ids:
            self.vector_store.collection.delete(ids=[chunk_id])

    @staticmethod
    def _safe_search_filters(
        filters: dict[str, Any] | None,
        allowed_access_levels: list[str] | None,
    ) -> dict[str, Any] | None:
        safe_filters = {
            key: value
            for key, value in (filters or {}).items()
            if key != "access_level"
        }
        if allowed_access_levels is not None:
            safe_filters["access_level"] = allowed_access_levels or ["__no_access__"]
        return safe_filters or None

    @staticmethod
    def _candidate_count(top_k: int) -> int:
        if not settings.reranking_enabled:
            return top_k
        multiplier = max(settings.rerank_candidate_multiplier, 1)
        max_candidates = max(settings.rerank_max_candidates, top_k)
        return min(top_k * multiplier, max_candidates)

    def _rerank_candidates(
        self,
        query: str,
        candidates: list[tuple[dict[str, Any], KnowledgeChunk]],
    ) -> list[tuple[dict[str, Any], KnowledgeChunk]]:
        if not settings.reranking_enabled or len(candidates) <= 1:
            return candidates

        try:
            scores = self.reranker_service.score(
                query,
                [chunk.chunk_text for _, chunk in candidates],
            )
        except Exception:
            return candidates

        if len(scores) != len(candidates):
            return candidates

        reranked = [
            (score, index, match, chunk)
            for index, ((match, chunk), score) in enumerate(zip(candidates, scores, strict=True))
        ]
        reranked.sort(key=lambda item: item[0], reverse=True)
        return [(match, chunk) for _, _, match, chunk in reranked]

    @staticmethod
    def _safe_original_filename(file_name: str) -> str:
        name = Path(file_name).name.strip() or "knowledge.txt"
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        return name or "knowledge.txt"

    @staticmethod
    def _document_response(doc: KnowledgeDoc, chunk_count: int) -> DocumentResponse:
        return DocumentResponse(
            doc_id=doc.doc_id,
            title=doc.title,
            source_type=doc.source_type,
            file_name=doc.file_name,
            version=doc.version,
            status=doc.indexing_status,
            chunk_count=chunk_count,
            indexing_error=doc.indexing_error,
        )

    @staticmethod
    def _citation(title: str, section_title: str) -> str:
        return f"{title} > {section_title}"

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"
