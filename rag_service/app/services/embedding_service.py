from functools import cached_property
import os
from typing import Any

from app.core.config import settings


class EmbeddingService:
    @cached_property
    def model(self) -> Any:
        os.environ.setdefault("USE_TF", "0")
        os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.embedding_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
