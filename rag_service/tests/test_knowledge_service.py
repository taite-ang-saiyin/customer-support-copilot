from io import BytesIO
from pathlib import Path
import shutil
from typing import Any
import uuid

from fastapi import UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base
from app.db.models import KnowledgeChunk, KnowledgeDoc, RetrievalLog
from app.schemas.knowledge import SearchRequest
from app.services.knowledge_service import KnowledgeService


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return [float(len(query)), 1.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        for index, chunk_id in enumerate(chunk_ids):
            self.items[chunk_id] = {
                "text": documents[index],
                "metadata": metadatas[index],
                "embedding": embeddings[index],
            }

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        matches = []
        for chunk_id, item in self.items.items():
            text = item["text"].lower()
            score = 0.95 if "duplicate charge" in text or "billed twice" in text else 0.25
            matches.append(
                {
                    "chunk_id": chunk_id,
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "distance": 1.0 - score,
                    "score": score,
                }
            )
        return sorted(matches, key=lambda item: item["score"], reverse=True)[:top_k]

    def delete_document(self, doc_id: str) -> None:
        self.items = {
            chunk_id: item
            for chunk_id, item in self.items.items()
            if item["metadata"].get("doc_id") != doc_id
        }


class FailingEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding service unavailable")


def test_upload_search_and_log_flow() -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    settings.upload_dir = str(temp_root / "uploads")
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )
        file = UploadFile(
            filename="refund_policy.md",
            file=BytesIO(
                b"""# Refund Policy

## Duplicate Charges

A duplicate charge occurs when the same workspace is billed twice.

## Processing Time

Approved refunds are submitted within 2 business days.
"""
            ),
        )

        upload_response = service.upload_and_index(
            db=db,
            file=file,
            title="CloudDesk Refund Policy",
            source_type="policy",
            category="billing",
            access_level="support",
            language="en",
        )
        search_response = service.search(
            db=db,
            request=SearchRequest(query="I was charged twice", top_k=1),
        )

        chunks = db.scalars(select(KnowledgeChunk)).all()
        logs = db.scalars(select(RetrievalLog)).all()

        assert upload_response.status == "indexed"
        assert upload_response.chunk_count >= 2
        assert len(chunks) == upload_response.chunk_count
        assert search_response.results[0].section == "Duplicate Charges"
        assert search_response.results[0].citation == "CloudDesk Refund Policy > Duplicate Charges"
        assert search_response.results[0].score > 0
        assert len(logs) == 1
        assert logs[0].retrieved_chunk_ids == [search_response.results[0].chunk_id]
    finally:
        db.close()
        shutil.rmtree(temp_root, ignore_errors=True)


def test_upload_rejects_invalid_file_type(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    monkeypatch.setattr(settings, "upload_dir", str(temp_root / "uploads"))
    service = KnowledgeService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )
    file = UploadFile(filename="malware.exe", file=BytesIO(b"nope"))

    try:
        try:
            service._save_upload(file)
        except ValueError as exc:
            assert "Unsupported file type" in str(exc)
        else:
            raise AssertionError("Expected invalid file type to be rejected")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_upload_rejects_oversized_file(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    monkeypatch.setattr(settings, "upload_dir", str(temp_root / "uploads"))
    monkeypatch.setattr(settings, "max_upload_size_bytes", 4)
    service = KnowledgeService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )
    file = UploadFile(filename="policy.md", file=BytesIO(b"too large"))

    try:
        try:
            service._save_upload(file)
        except ValueError as exc:
            assert "too large" in str(exc)
        else:
            raise AssertionError("Expected oversized file to be rejected")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_indexing_failure_marks_document_failed(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    monkeypatch.setattr(settings, "upload_dir", str(temp_root / "uploads"))
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        service = KnowledgeService(
            embedding_service=FailingEmbeddingService(),
            vector_store=FakeVectorStore(),
        )
        file = UploadFile(
            filename="refund_policy.md",
            file=BytesIO(b"# Refund Policy\n\nRefunds can be reviewed."),
        )

        try:
            service.upload_and_index(
                db=db,
                file=file,
                title="Refund Policy",
                source_type="policy",
                category="billing",
                access_level="support",
                language="en",
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected indexing failure")

        doc = db.scalars(select(KnowledgeDoc)).one()
        assert doc.indexing_status == "failed"
        assert "embedding service unavailable" in (doc.indexing_error or "")
    finally:
        db.close()
        shutil.rmtree(temp_root, ignore_errors=True)


def test_pdf_upload_saves_cleaned_markdown_artifact(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    settings.upload_dir = str(temp_root / "uploads")
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def fake_extract_pdf_to_markdown(file_path: str, mode: str = "blocks") -> str:
        return "# Refund Policy\n\n## Duplicate Charges\n\nA duplicate charge occurs when billed twice."

    monkeypatch.setattr(
        "app.services.knowledge_service.extract_pdf_to_markdown",
        fake_extract_pdf_to_markdown,
    )

    try:
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )
        file = UploadFile(
            filename="refund_policy.pdf",
            file=BytesIO(b"%PDF-1.4 fake test content"),
        )

        service.upload_and_index(
            db=db,
            file=file,
            title="CloudDesk Refund Policy",
            source_type="policy",
            category="billing",
            access_level="support",
            language="en",
        )

        artifact_path = temp_root / "uploads" / "processed" / "refund_policy.cleaned.md"
        assert artifact_path.exists()
        assert "## Duplicate Charges" in artifact_path.read_text(encoding="utf-8")
    finally:
        db.close()
        shutil.rmtree(temp_root, ignore_errors=True)
