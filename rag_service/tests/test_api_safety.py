from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api import knowledge as knowledge_api
from app.api.knowledge import get_knowledge_service, router
from app.core.config import settings
from app.schemas.knowledge import DocumentListResponse, SearchRequest, SearchResponse


class FakeApiService:
    def __init__(self) -> None:
        self.allowed_access_levels: list[str] | None = None

    def list_documents(
        self,
        db: Any,
        source_type: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentListResponse:
        return DocumentListResponse(items=[], total=0)

    def search(
        self,
        db: Any,
        request: SearchRequest,
        allowed_access_levels: list[str] | None = None,
    ) -> SearchResponse:
        self.allowed_access_levels = allowed_access_levels
        return SearchResponse(query=request.query, results=[], top_k=request.top_k or 3, log_id="log_test")


def build_client(service: FakeApiService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_knowledge_service] = lambda: service
    return TestClient(app)


def test_knowledge_endpoints_reject_missing_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(settings, "internal_api_key", "secret")
    client = build_client(FakeApiService())

    response = client.get("/knowledge/docs")

    assert response.status_code == 401


def test_knowledge_endpoints_reject_invalid_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(settings, "internal_api_key", "secret")
    client = build_client(FakeApiService())

    response = client.get("/knowledge/docs", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401


def test_knowledge_endpoints_accept_valid_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(settings, "internal_api_key", "secret")
    client = build_client(FakeApiService())

    response = client.get("/knowledge/docs", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_knowledge_endpoints_allow_requests_when_api_key_auth_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key_auth_enabled", False)
    monkeypatch.setattr(settings, "internal_api_key", None)
    client = build_client(FakeApiService())

    response = client.get("/knowledge/docs")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_search_uses_server_side_allowed_access_levels(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(settings, "internal_api_key", "secret")
    monkeypatch.setattr(settings, "internal_allowed_access_levels", "support,public")
    service = FakeApiService()
    client = build_client(service)

    response = client.post(
        "/knowledge/search",
        headers={"X-API-Key": "secret"},
        json={
            "query": "refund",
            "filters": {"access_level": "internal"},
        },
    )

    assert response.status_code == 200
    assert service.allowed_access_levels == ["support", "public"]


def test_upload_background_task_triggers_evaluation_after_success(monkeypatch) -> None:
    calls: list[str] = []

    class FakeDb:
        def close(self) -> None:
            calls.append("db_closed")

    class FakeKnowledgeService:
        def index_document_by_id(self, **kwargs: Any) -> None:
            calls.append("indexed")

    monkeypatch.setattr(knowledge_api, "SessionLocal", FakeDb)
    monkeypatch.setattr(knowledge_api, "get_knowledge_service", lambda: FakeKnowledgeService())
    monkeypatch.setattr(
        knowledge_api,
        "start_ragas_evaluation_after_upload",
        lambda uploaded_document_id: calls.append(f"evaluated:{uploaded_document_id}"),
    )

    knowledge_api._index_uploaded_document("doc_001", "billing", "support", "en")

    assert calls == ["indexed", "evaluated:doc_001", "db_closed"]


def test_upload_background_task_skips_evaluation_after_index_failure(monkeypatch) -> None:
    calls: list[str] = []

    class FakeDb:
        def close(self) -> None:
            calls.append("db_closed")

    class FailingKnowledgeService:
        def index_document_by_id(self, **kwargs: Any) -> None:
            raise RuntimeError("index failed")

    monkeypatch.setattr(knowledge_api, "SessionLocal", FakeDb)
    monkeypatch.setattr(knowledge_api, "get_knowledge_service", lambda: FailingKnowledgeService())
    monkeypatch.setattr(
        knowledge_api,
        "start_ragas_evaluation_after_upload",
        lambda uploaded_document_id: calls.append("evaluated"),
    )

    try:
        knowledge_api._index_uploaded_document("doc_001", "billing", "support", "en")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected indexing failure")

    assert calls == ["db_closed"]
