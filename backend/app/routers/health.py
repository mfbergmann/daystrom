"""Health check endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai_service import check_ollama

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: bool
    ollama: bool


@router.get("/api/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    ollama_ok = await check_ollama()

    status = "healthy" if db_ok else "unhealthy"
    return HealthResponse(status=status, database=db_ok, ollama=ollama_ok)
