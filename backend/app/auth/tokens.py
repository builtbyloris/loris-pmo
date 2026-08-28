from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.errors import AppError


@dataclass(frozen=True)
class AccessToken:
    encoded: str
    csrf_token: str


def create_access_token(user_id: UUID, settings: Settings) -> AccessToken:
    now = datetime.now(UTC)
    csrf_token = uuid4().hex
    payload = {
        "sub": str(user_id),
        "csrf": csrf_token,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "type": "access",
    }
    return AccessToken(
        encoded=jwt.encode(payload, settings.secret_key, algorithm="HS256"),
        csrf_token=csrf_token,
    )


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise AppError(
            code="invalid_session", message="Your session is invalid or expired.", status_code=401
        ) from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AppError(
            code="invalid_session", message="Your session is invalid or expired.", status_code=401
        )
    return payload
