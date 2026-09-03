from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import ACCESS_COOKIE, CSRF_COOKIE, CurrentUser, require_csrf
from app.auth.tokens import create_access_token
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.auth import AuthResponse, LoginRequest, UserRead
from app.schemas.collaboration import ProfileUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    user = await AuthService(session).authenticate(str(credentials.email), credentials.password)
    token = create_access_token(user.id, settings)
    max_age = settings.access_token_minutes * 60
    response.set_cookie(
        ACCESS_COOKIE,
        token.encoded,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_same_site,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        token.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite=settings.cookie_same_site,
        domain=settings.cookie_domain,
        path="/",
    )
    return AuthResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
async def logout(
    response: Response,
    _user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    response.delete_cookie(
        ACCESS_COOKIE, path="/", domain=settings.cookie_domain, samesite=settings.cookie_same_site
    )
    response.delete_cookie(
        CSRF_COOKIE, path="/", domain=settings.cookie_domain, samesite=settings.cookie_same_site
    )


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/profile", response_model=UserRead, dependencies=[Depends(require_csrf)])
async def update_profile(
    data: ProfileUpdate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user.display_name = data.display_name
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)
