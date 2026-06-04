from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.api.knowledge import router as knowledge_router
from app.core.config import settings
from app.db.database import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        ensure_document_status_columns()

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(knowledge_router)
    return app


app = create_app()


def ensure_document_status_columns() -> None:
    inspector = inspect(engine)
    if "knowledge_docs" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_docs")
    }
    statements = []
    if "indexing_status" not in existing_columns:
        statements.append(
            "ALTER TABLE knowledge_docs "
            "ADD COLUMN indexing_status VARCHAR(32) NOT NULL DEFAULT 'pending'"
        )
    if "indexing_error" not in existing_columns:
        statements.append("ALTER TABLE knowledge_docs ADD COLUMN indexing_error TEXT")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
