from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError


class IntegrationTokenCipher:
    """Authenticated encryption for provider secrets stored in the database."""

    def __init__(self, key: str | None) -> None:
        self._fernet: Fernet | None = None
        if key:
            try:
                self._fernet = Fernet(key.encode("ascii"))
            except (ValueError, UnicodeEncodeError) as exc:
                raise ValueError("INTEGRATION_TOKEN_ENCRYPTION_KEY must be a Fernet key") from exc

    @property
    def available(self) -> bool:
        return self._fernet is not None

    def encrypt(self, value: str) -> str:
        if self._fernet is None:
            raise AppError(
                code="integrations_not_configured",
                message="External integrations are not configured.",
                status_code=503,
            )
        return self._fernet.encrypt(value.encode()).decode("ascii")

    def decrypt(self, value: str) -> str:
        if self._fernet is None:
            raise AppError(
                code="integrations_not_configured",
                message="External integrations are not configured.",
                status_code=503,
            )
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode()
        except (InvalidToken, UnicodeError) as exc:
            raise AppError(
                code="integration_reauthentication_required",
                message="The integration must be connected again.",
                status_code=401,
            ) from exc
