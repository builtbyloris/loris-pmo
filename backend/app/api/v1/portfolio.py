from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.schemas.projects import PortfolioSummary
from app.services.projects import ProjectService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    user: CurrentUser, session: Annotated[AsyncSession, Depends(get_db)]
) -> PortfolioSummary:
    return await ProjectService(session, user.id).portfolio()
