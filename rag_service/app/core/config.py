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
    internal_api_key: str | None = Field(default=None, alias="INTERNAL_API_KEY")
    internal_allowed_access_levels: str = Field(
        default="support,public",
        alias="INTERNAL_ALLOWED_ACCESS_LEVELS",
    )
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE_BYTES")

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
