from typing import Any

import httpx

from app.services.supabase_eval_store import SupabaseEvaluationStore


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.content = b"json"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


def test_supabase_store_uses_rest_api_and_service_role_headers(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse([{"id": "eval_001"}])

    monkeypatch.setattr("app.services.supabase_eval_store.httpx.request", fake_request)
    store = SupabaseEvaluationStore(
        supabase_url="https://project.supabase.co/",
        service_role_key="service-secret",
    )

    inserted = store.insert("evaluation_runs", {"id": "eval_001"})
    selected = store.select(
        "evaluation_runs",
        filters={"module": "rag_service"},
        order="created_at.desc",
        limit=10,
    )
    updated = store.update(
        "evaluation_runs",
        {"metadata": {"status": "passed"}},
        {"id": "eval_001"},
    )

    assert inserted == [{"id": "eval_001"}]
    assert selected == [{"id": "eval_001"}]
    assert updated == [{"id": "eval_001"}]
    assert calls[0]["url"] == "https://project.supabase.co/rest/v1/evaluation_runs"
    assert calls[0]["headers"]["apikey"] == "service-secret"
    assert calls[0]["headers"]["Authorization"] == "Bearer service-secret"
    assert calls[1]["params"] == {
        "select": "*",
        "module": "eq.rag_service",
        "order": "created_at.desc",
        "limit": 10,
    }
    assert calls[2]["params"] == {"id": "eq.eval_001"}


def test_supabase_store_retries_transient_transport_errors(monkeypatch) -> None:
    calls = 0

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("temporary tls connection drop")
        return FakeResponse([{"id": "eval_001"}])

    monkeypatch.setattr("app.services.supabase_eval_store.httpx.request", fake_request)
    monkeypatch.setattr("app.services.supabase_eval_store.time.sleep", lambda _: None)
    store = SupabaseEvaluationStore(
        supabase_url="https://project.supabase.co/",
        service_role_key="service-secret",
    )

    assert store.select("evaluation_runs") == [{"id": "eval_001"}]
    assert calls == 2
