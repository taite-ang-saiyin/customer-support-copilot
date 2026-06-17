from io import BytesIO
from pathlib import Path
import shutil
from typing import Any
import uuid

from fastapi import UploadFile
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base
from app.db.models import KnowledgeChunk, KnowledgeDoc, RetrievalLog
from app.schemas.knowledge import SearchRequest
from app.services.knowledge_service import KnowledgeService


@pytest.fixture(autouse=True)
def disable_reranking_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reranking_enabled", False)


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


class OrderedVectorStore:
    def __init__(self, chunk_ids: list[str]) -> None:
        self.chunk_ids = chunk_ids
        self.requested_top_k: int | None = None

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.requested_top_k = top_k
        return [
            {
                "chunk_id": chunk_id,
                "text": "",
                "metadata": {},
                "distance": float(index),
                "score": 1.0 / (1.0 + index),
            }
            for index, chunk_id in enumerate(self.chunk_ids[:top_k])
        ]


class KeywordRerankerService:
    def score(self, query: str, texts: list[str]) -> list[float]:
        return [10.0 if "best answer" in text.lower() else 1.0 for text in texts]


class FailingRerankerService:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("reranker unavailable")


def add_search_doc(db: Any) -> list[str]:
    doc = KnowledgeDoc(
        doc_id="doc_search",
        title="Search Test Doc",
        source_type="policy",
        file_name="search.md",
        file_path="search.md",
        indexing_status="indexed",
    )
    chunks = [
        KnowledgeChunk(
            chunk_id="chunk_vector_first",
            doc_id=doc.doc_id,
            chunk_text="This is a plausible but weaker answer.",
            section_title="Vector First",
            category="billing",
            language="en",
            access_level="support",
            chunk_index=0,
        ),
        KnowledgeChunk(
            chunk_id="chunk_rerank_first",
            doc_id=doc.doc_id,
            chunk_text="This is the best answer after reranking.",
            section_title="Rerank First",
            category="billing",
            language="en",
            access_level="support",
            chunk_index=1,
        ),
    ]
    db.add(doc)
    db.add_all(chunks)
    db.commit()
    return [chunk.chunk_id for chunk in chunks]


def add_help_doc(
    db: Any,
    doc_id: str,
    title: str,
    category: str,
    access_level: str,
    status: str = "indexed",
    chunks: list[tuple[str, str]] | None = None,
) -> None:
    doc = KnowledgeDoc(
        doc_id=doc_id,
        title=title,
        source_type="article",
        file_name=f"{doc_id}.md",
        file_path=f"{doc_id}.md",
        indexing_status=status,
    )
    db.add(doc)
    for index, (section, text) in enumerate(chunks or [("Guide", f"{title} body")]):
        db.add(
            KnowledgeChunk(
                chunk_id=f"chunk_{doc_id}_{index}",
                doc_id=doc_id,
                chunk_text=text,
                section_title=section,
                category=category,
                language="en",
                access_level=access_level,
                chunk_index=index,
            )
        )
    db.commit()


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


def test_help_articles_include_only_public_indexed_documents() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(db, "doc_public", "Refund Help", "billing", "public")
        add_help_doc(db, "doc_support", "Support Playbook", "billing", "support")
        add_help_doc(db, "doc_internal", "Internal Runbook", "ops", "internal")
        add_help_doc(db, "doc_private", "Private Notes", "ops", "private")
        add_help_doc(db, "doc_pending", "Pending Public", "billing", "public", status="pending")
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        response = service.list_help_articles(db=db)

        assert [article.id for article in response.articles] == ["doc_public"]
        assert response.articles[0].helpfulCount == 0
        assert response.articles[0].unhelpfulCount == 0
    finally:
        db.close()


def test_help_articles_category_filter_uses_public_chunk_category() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(db, "doc_billing", "Refund Help", "billing", "public")
        add_help_doc(db, "doc_login", "Login Help", "account", "public")
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        response = service.list_help_articles(db=db, category="account")

        assert [article.id for article in response.articles] == ["doc_login"]
        assert response.articles[0].category == "account"
    finally:
        db.close()


def test_help_articles_q_filter_searches_title_category_and_chunk_text() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(
            db,
            "doc_refund",
            "Refund Help",
            "billing",
            "public",
            chunks=[("Refunds", "Customers can request refund review for duplicate charges.")],
        )
        add_help_doc(
            db,
            "doc_login",
            "Login Help",
            "account",
            "public",
            chunks=[("Passwords", "Reset your password from the sign-in page.")],
        )
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        title_response = service.list_help_articles(db=db, q="refund")
        category_response = service.list_help_articles(db=db, q="account")
        text_response = service.list_help_articles(db=db, q="duplicate charges")

        assert [article.id for article in title_response.articles] == ["doc_refund"]
        assert [article.id for article in category_response.articles] == ["doc_login"]
        assert [article.id for article in text_response.articles] == ["doc_refund"]
    finally:
        db.close()


def test_get_help_article_returns_sections_without_duplicate_chunks() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(
            db,
            "doc_article",
            "Billing Guide",
            "billing",
            "public",
            chunks=[
                ("Overview", "Billing settings are available from workspace settings."),
                ("Steps", "Open billing, review the invoice, and choose download."),
                ("Steps", "Open billing, review the invoice, and choose download."),
            ],
        )
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        article = service.get_help_article(db=db, doc_id="doc_article")

        assert article is not None
        assert article.id == "doc_article"
        assert article.title == "Billing Guide"
        assert article.summary == "Billing settings are available from workspace settings."
        assert [section.title for section in article.contentSections] == ["Overview", "Steps"]
        assert article.contentSections[1].body == "Open billing, review the invoice, and choose download."
    finally:
        db.close()


def test_get_help_article_strips_front_matter_and_duplicate_markdown_headings() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(
            db,
            "doc_markdown_article",
            "Account Recovery",
            "Account Access",
            "public",
            chunks=[
                (
                    "Overview",
                    """---
title: Account Recovery
category: Account Access
access_level: public
source_type: help_article
summary: Learn how CloudDesk verifies account recovery requests.
---""",
                ),
                ("Account Recovery", "# Account Recovery"),
                (
                    "Lost Access To Login Email",
                    "## Lost Access To Login Email\n\nIf you lost access to your login email, ask another Workspace Admin for help.",
                ),
            ],
        )
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        article = service.get_help_article(db=db, doc_id="doc_markdown_article")

        assert article is not None
        assert article.summary == "If you lost access to your login email, ask another Workspace Admin for help."
        assert [section.title for section in article.contentSections] == ["Lost Access To Login Email"]
        assert "---" not in article.contentSections[0].body
        assert "## Lost Access To Login Email" not in article.contentSections[0].body
        assert article.contentSections[0].body.startswith("If you lost access")
    finally:
        db.close()


def test_get_help_article_returns_none_for_non_public_or_non_indexed_doc() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        add_help_doc(db, "doc_support", "Support Playbook", "billing", "support")
        add_help_doc(db, "doc_pending", "Pending Public", "billing", "public", status="pending")
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        assert service.get_help_article(db=db, doc_id="doc_support") is None
        assert service.get_help_article(db=db, doc_id="doc_pending") is None
    finally:
        db.close()


def test_search_keeps_vector_order_when_reranking_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reranking_enabled", False)
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        chunk_ids = add_search_doc(db)
        vector_store = OrderedVectorStore(chunk_ids)
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=vector_store,
            reranker_service=KeywordRerankerService(),
        )

        response = service.search(db=db, request=SearchRequest(query="which answer", top_k=1))

        assert vector_store.requested_top_k == 1
        assert response.results[0].section == "Vector First"
    finally:
        db.close()


def test_search_reranks_larger_candidate_pool(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reranking_enabled", True)
    monkeypatch.setattr(settings, "rerank_candidate_multiplier", 5)
    monkeypatch.setattr(settings, "rerank_max_candidates", 25)
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        chunk_ids = add_search_doc(db)
        vector_store = OrderedVectorStore(chunk_ids)
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=vector_store,
            reranker_service=KeywordRerankerService(),
        )

        response = service.search(db=db, request=SearchRequest(query="which answer", top_k=1))

        assert vector_store.requested_top_k == 5
        assert response.results[0].section == "Rerank First"
    finally:
        db.close()


def test_search_falls_back_to_vector_order_when_reranker_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "reranking_enabled", True)
    monkeypatch.setattr(settings, "rerank_candidate_multiplier", 5)
    monkeypatch.setattr(settings, "rerank_max_candidates", 25)
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        chunk_ids = add_search_doc(db)
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=OrderedVectorStore(chunk_ids),
            reranker_service=FailingRerankerService(),
        )

        response = service.search(db=db, request=SearchRequest(query="which answer", top_k=1))

        assert response.results[0].section == "Vector First"
    finally:
        db.close()


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


def test_upload_keeps_readable_filename(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    monkeypatch.setattr(settings, "upload_dir", str(temp_root / "uploads"))
    service = KnowledgeService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )
    file = UploadFile(filename="known_issues.md", file=BytesIO(b"# Known Issues"))

    try:
        file_path, stored_name = service._save_upload(file)

        assert stored_name == "known_issues.md"
        assert Path(file_path).name == "known_issues.md"
        assert Path(file_path).read_bytes() == b"# Known Issues"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_duplicate_upload_uses_readable_numeric_suffix(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    monkeypatch.setattr(settings, "upload_dir", str(temp_root / "uploads"))
    service = KnowledgeService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )

    try:
        first_path, first_name = service._save_upload(
            UploadFile(filename="known_issues.md", file=BytesIO(b"first"))
        )
        second_path, second_name = service._save_upload(
            UploadFile(filename="known_issues.md", file=BytesIO(b"second"))
        )

        assert first_name == "known_issues.md"
        assert second_name == "known_issues_2.md"
        assert Path(first_path).read_bytes() == b"first"
        assert Path(second_path).read_bytes() == b"second"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_delete_document_removes_uploaded_file(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    upload_dir = temp_root / "uploads"
    upload_dir.mkdir(parents=True)
    file_path = upload_dir / "known_issues.md"
    file_path.write_text("# Known Issues", encoding="utf-8")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        doc = KnowledgeDoc(
            doc_id="doc_delete_markdown",
            title="Known Issues",
            source_type="known_issue",
            file_name=file_path.name,
            file_path=str(file_path),
            indexing_status="indexed",
        )
        db.add(doc)
        db.commit()
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        deleted_chunks = service.delete_document(db, doc.doc_id)

        assert deleted_chunks == 0
        assert not file_path.exists()
        assert db.get(KnowledgeDoc, doc.doc_id) is None
    finally:
        db.close()
        shutil.rmtree(temp_root, ignore_errors=True)


def test_delete_pdf_removes_source_and_processed_markdown(monkeypatch) -> None:
    temp_root = Path(".pytest_workspace") / uuid.uuid4().hex
    upload_dir = temp_root / "uploads"
    processed_dir = upload_dir / "processed"
    processed_dir.mkdir(parents=True)
    file_path = upload_dir / "refund_policy.pdf"
    processed_path = processed_dir / "refund_policy.cleaned.md"
    file_path.write_bytes(b"%PDF-1.4")
    processed_path.write_text("# Refund Policy", encoding="utf-8")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        doc = KnowledgeDoc(
            doc_id="doc_delete_pdf",
            title="Refund Policy",
            source_type="policy",
            file_name=file_path.name,
            file_path=str(file_path),
            indexing_status="indexed",
        )
        db.add(doc)
        db.commit()
        service = KnowledgeService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )

        service.delete_document(db, doc.doc_id)

        assert not file_path.exists()
        assert not processed_path.exists()
    finally:
        db.close()
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
