from functools import cached_property
import os
from typing import Any

from app.core.config import settings


class RerankerService:
    @cached_property
    def model(self) -> Any:
        os.environ.setdefault("USE_TF", "0")
        os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
        from sentence_transformers import CrossEncoder

        return CrossEncoder(settings.reranker_model)

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        pairs = [(query, text) for text in texts]
        scores = self.model.predict(pairs)
        return [float(score) for score in scores]
