from fastapi import FastAPI

from app.api.knowledge import router as knowledge_router
from app.core.config import settings
from app.db.database import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(knowledge_router)
    return app


app = create_app()
