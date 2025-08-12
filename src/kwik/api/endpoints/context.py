"""
Context API endpoints.

This module provides endpoints for retrieving application context information:
- get_settings: Returns application settings
- get_session: Returns database session information and connectivity status
"""

from fastapi import APIRouter
from sqlalchemy import text

from kwik.dependencies import Session, Settings

context_router = APIRouter(prefix="/context", tags=["context"])


@context_router.get("/settings")
def get_settings(settings: Settings) -> Settings:
    """Get application settings."""
    return settings


@context_router.get("/session")
def get_session(session: Session) -> dict:
    """Get database session information."""
    with session.begin():
        session.execute(text("CREATE TABLE IF NOT EXISTS ping (t TEXT)"))
        session.execute(text("INSERT INTO ping (t) VALUES ('pong')"))
        n = session.execute(text("SELECT COUNT(*) FROM ping")).scalar_one()
    return {"ok": True, "db_rows": n}
