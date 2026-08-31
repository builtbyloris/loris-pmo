from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.version import __version__

router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready(session: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
