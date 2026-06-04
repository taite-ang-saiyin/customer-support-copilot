from typing import Any

import chromadb

from app.core.config import settings


class VectorStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.client.get_or_create_collection(name=settings.chroma_collection)

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        if not chunk_ids:
            return
        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        where = self._build_where(filters)
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matches: list[dict[str, Any]] = []
        for index, chunk_id in enumerate(ids):
            distance = float(distances[index]) if index < len(distances) else 0.0
            matches.append(
                {
                    "chunk_id": chunk_id,
                    "text": documents[index] if index < len(documents) else "",
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "distance": distance,
                    "score": 1.0 / (1.0 + max(distance, 0.0)),
                }
            )
        return matches

    def delete_document(self, doc_id: str) -> None:
        self.collection.delete(where={"doc_id": doc_id})

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    @staticmethod
    def _build_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
        if not filters:
            return None

        simple_filters = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, str | int | float | bool):
                simple_filters.append({key: value})
            elif isinstance(value, list) and value:
                simple_filters.append({key: {"$in": value}})
        if not simple_filters:
            return None
        if len(simple_filters) == 1:
            return simple_filters[0]
        return {"$and": simple_filters}
