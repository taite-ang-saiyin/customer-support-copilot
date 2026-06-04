from collections.abc import Generator
import secrets

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not configured",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.internal_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return x_api_key
