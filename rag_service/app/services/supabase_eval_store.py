import time
from typing import Any

import httpx

from app.core.config import settings


class SupabaseEvaluationStore:
    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        self.supabase_url = (supabase_url or settings.supabase_url or "").rstrip("/")
        self.service_role_key = service_role_key or settings.supabase_service_role_key
        if not self.supabase_url or not self.service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
                "for evaluation storage"
            )
        self.base_url = f"{self.supabase_url}/rest/v1"
        self.headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def insert(self, table: str, rows: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._request(
            "POST",
            table,
            json=rows,
            headers={"Prefer": "return=representation"},
        )

    def select(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"select": "*"}
        for key, value in (filters or {}).items():
            params[key] = f"eq.{value}"
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", table, params=params)

    def update(
        self,
        table: str,
        values: dict[str, Any],
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        return self._request(
            "PATCH",
            table,
            params=params,
            json=values,
            headers={"Prefer": "return=representation"},
        )

    def delete(self, table: str, filters: dict[str, Any]) -> None:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        self._request("DELETE", table, params=params)

    def _request(
        self,
        method: str,
        table: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        request_headers = {**self.headers, **(headers or {})}
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.request(
                    method,
                    f"{self.base_url}/{table}",
                    params=params,
                    json=json,
                    headers=request_headers,
                    timeout=self.timeout,
                )
                break
            except httpx.TransportError:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_delay_seconds * (attempt + 1))
        response.raise_for_status()
        if not response.content:
            return []
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]
