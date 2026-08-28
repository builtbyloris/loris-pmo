import secrets
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import decode_access_token
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.user import User
from app.repositories.users import UserRepository

ACCESS_COOKIE = "loris_access_token"
CSRF_COOKIE = "loris_csrf_token"


def get_token_payload(
    settings: Annotated[Settings, Depends(get_settings)],
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
) -> dict:
    if not access_token:
        raise AppError(
            code="not_authenticated", message="Authentication required.", status_code=401
        )
    return decode_access_token(access_token, settings)


async def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError, KeyError) as exc:
        raise AppError(
            code="invalid_session", message="Your session is invalid or expired.", status_code=401
        ) from exc
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError(
            code="invalid_session", message="Your session is invalid or expired.", status_code=401
        )
    return user


def require_csrf(
    payload: Annotated[dict, Depends(get_token_payload)],
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    expected = payload.get("csrf")
    if not expected or not csrf_cookie or not csrf_header:
        raise AppError(code="csrf_failed", message="Security validation failed.", status_code=403)
    if not secrets.compare_digest(expected, csrf_cookie) or not secrets.compare_digest(
        expected, csrf_header
    ):
        raise AppError(code="csrf_failed", message="Security validation failed.", status_code=403)


CurrentUser = Annotated[User, Depends(get_current_user)]
