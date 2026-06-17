import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import KnowledgeChunk, KnowledgeDoc, RetrievalLog, utcnow
from app.schemas.knowledge import (
    DocumentDetail,
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    HelpArticleListResponse,
    HelpArticleResponse,
    HelpArticleSection,
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

    def list_help_articles(
        self,
        db: Session,
        q: str | None = None,
        category: str | None = None,
    ) -> HelpArticleListResponse:
        query = (
            select(KnowledgeDoc)
            .join(KnowledgeChunk)
            .where(
                KnowledgeDoc.indexing_status == "indexed",
                KnowledgeChunk.access_level == "public",
            )
            .order_by(desc(KnowledgeDoc.updated_at), desc(KnowledgeDoc.created_at))
        )
        if category:
            query = query.where(KnowledgeChunk.category == category)

        search_term = (q or "").strip()
        if search_term:
            pattern = f"%{search_term}%"
            query = query.where(
                or_(
                    KnowledgeDoc.title.ilike(pattern),
                    KnowledgeChunk.category.ilike(pattern),
                    KnowledgeChunk.chunk_text.ilike(pattern),
                )
            )

        docs = list(db.scalars(query).unique().all())
        return HelpArticleListResponse(
            articles=[
                self._help_article_response(doc)
                for doc in docs
            ]
        )

    def get_help_article(self, db: Session, doc_id: str) -> HelpArticleResponse | None:
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None or doc.indexing_status != "indexed":
            return None
        public_chunks = self._public_chunks(doc)
        if not public_chunks:
            return None
        return self._help_article_response(doc, public_chunks=public_chunks)

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

    @classmethod
    def _help_article_response(
        cls,
        doc: KnowledgeDoc,
        public_chunks: list[KnowledgeChunk] | None = None,
    ) -> HelpArticleResponse:
        chunks = public_chunks if public_chunks is not None else cls._public_chunks(doc)
        category = cls._article_category(doc, chunks)
        sections = cls._article_sections(chunks)
        summary = cls._article_summary(doc, chunks)
        return HelpArticleResponse(
            id=doc.doc_id,
            title=cls._article_title(doc),
            category=category,
            summary=summary,
            updatedDate=cls._article_updated_date(doc),
            helpfulCount=0,
            unhelpfulCount=0,
            contentSections=sections,
        )

    @staticmethod
    def _public_chunks(doc: KnowledgeDoc) -> list[KnowledgeChunk]:
        return sorted(
            [
                chunk
                for chunk in doc.chunks
                if chunk.access_level == "public"
            ],
            key=lambda chunk: chunk.chunk_index,
        )

    @staticmethod
    def _article_sections(chunks: list[KnowledgeChunk]) -> list[HelpArticleSection]:
        section_order: list[str] = []
        section_bodies: dict[str, list[str]] = {}
        seen_texts: set[str] = set()

        for chunk in chunks:
            title = (chunk.section_title or "").strip() or "Guide"
            body = KnowledgeService._clean_article_body(
                chunk.chunk_text,
                section_title=title,
            )
            if not body:
                continue
            text_key = re.sub(r"\s+", " ", body).lower()
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            if title not in section_bodies:
                section_order.append(title)
                section_bodies[title] = []
            section_bodies[title].append(body)

        return [
            HelpArticleSection(
                title=title,
                body="\n\n".join(section_bodies[title]),
            )
            for title in section_order
        ]

    @staticmethod
    def _article_title(doc: KnowledgeDoc) -> str:
        return doc.title or Path(doc.file_name).stem

    @staticmethod
    def _article_category(doc: KnowledgeDoc, chunks: list[KnowledgeChunk]) -> str:
        document_category = getattr(doc, "category", None)
        if isinstance(document_category, str) and document_category.strip():
            return document_category.strip()

        if chunks:
            chunk_category = chunks[0].category.strip()
            if chunk_category:
                return chunk_category

        return "General"

    @staticmethod
    def _article_summary(doc: KnowledgeDoc, chunks: list[KnowledgeChunk]) -> str:
        document_summary = getattr(doc, "summary", None)
        if isinstance(document_summary, str) and document_summary.strip():
            return document_summary.strip()

        first_chunk_text = ""
        for chunk in chunks:
            first_chunk_text = KnowledgeService._clean_article_body(
                chunk.chunk_text,
                section_title=chunk.section_title,
            )
            if first_chunk_text:
                break

        first_chunk_text = re.sub(r"\s+", " ", first_chunk_text)
        return first_chunk_text[:160]

    @staticmethod
    def _clean_article_body(text: str, section_title: str) -> str:
        body = re.sub(r"\A---\s*\n.*?\n---\s*", "", text.strip(), flags=re.DOTALL)
        lines = body.splitlines()

        while lines and not lines[0].strip():
            lines.pop(0)

        while lines:
            heading = re.match(r"^#{1,6}\s+(.+?)\s*$", lines[0].strip())
            if not heading:
                break
            heading_title = heading.group(1).strip()
            if KnowledgeService._normalized_title(heading_title) != KnowledgeService._normalized_title(section_title):
                break
            lines.pop(0)
            while lines and not lines[0].strip():
                lines.pop(0)

        return "\n".join(lines).strip()

    @staticmethod
    def _normalized_title(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    @staticmethod
    def _article_updated_date(doc: KnowledgeDoc) -> str:
        updated_at = (
            getattr(doc, "updated_at", None)
            or getattr(doc, "indexed_at", None)
            or doc.created_at
        )
        return updated_at.date().isoformat()

    @staticmethod
    def _citation(title: str, section_title: str) -> str:
        return f"{title} > {section_title}"

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"
