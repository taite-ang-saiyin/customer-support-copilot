from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/support_copilot",
        alias="DATABASE_URL",
    )
    chroma_db_path: str = Field(default="./chroma_db", alias="CHROMA_DB_PATH")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    top_k: int = Field(default=3, alias="TOP_K")
    app_name: str = Field(default="AI Customer Support Copilot RAG Service", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    chroma_collection: str = "support_knowledge"
    api_key_auth_enabled: bool = Field(default=True, alias="API_KEY_AUTH_ENABLED")
    internal_api_key: str | None = Field(default=None, alias="INTERNAL_API_KEY")
    internal_allowed_access_levels: str = Field(
        default="support,public",
        alias="INTERNAL_ALLOWED_ACCESS_LEVELS",
    )
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE_BYTES")
    reranking_enabled: bool = Field(default=False, alias="RERANKING_ENABLED")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="RERANKER_MODEL",
    )
    rerank_candidate_multiplier: int = Field(default=5, alias="RERANK_CANDIDATE_MULTIPLIER")
    rerank_max_candidates: int = Field(default=25, alias="RERANK_MAX_CANDIDATES")
    ragas_dataset_path: str = Field(
        default="./evals/datasets/support_eval_v1.json",
        alias="RAGAS_DATASET_PATH",
    )
    ragas_auto_eval_enabled: bool = Field(default=True, alias="RAGAS_AUTO_EVAL_ENABLED")
    ragas_evaluator_model: str | None = Field(default=None, alias="RAGAS_EVALUATOR_MODEL")
    ragas_evaluator_provider: str | None = Field(
        default=None,
        alias="RAGAS_EVALUATOR_PROVIDER",
    )
    ragas_evaluator_api_key: str | None = Field(
        default=None,
        alias="RAGAS_EVALUATOR_API_KEY",
    )
    ragas_evaluator_base_url: str | None = Field(
        default=None,
        alias="RAGAS_EVALUATOR_BASE_URL",
    )
    ragas_evaluator_max_tokens: int = Field(
        default=2048,
        alias="RAGAS_EVALUATOR_MAX_TOKENS",
    )
    ragas_prompt_version: str = Field(default="rag_prompt_v1", alias="RAGAS_PROMPT_VERSION")
    ragas_retrieval_version: str = Field(
        default="chroma_v1",
        alias="RAGAS_RETRIEVAL_VERSION",
    )
    ragas_eval_top_k: int = Field(default=5, alias="RAGAS_EVAL_TOP_K")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(
        default=None,
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )

    @property
    def allowed_access_levels(self) -> list[str]:
        return [
            access_level.strip()
            for access_level in self.internal_allowed_access_levels.split(",")
            if access_level.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
