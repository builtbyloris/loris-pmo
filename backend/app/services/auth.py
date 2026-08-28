from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import DUMMY_HASH, verify_password
from app.core.errors import AppError
from app.models.user import User
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email.lower())
        stored_hash = user.password_hash if user else DUMMY_HASH
        valid = verify_password(password, stored_hash)
        if user is None or not valid or not user.is_active:
            raise AppError(
                code="invalid_credentials",
                message="Email or password is incorrect.",
                status_code=401,
            )
        return user
