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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
