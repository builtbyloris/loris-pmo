from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.ai.errors import AINotConfiguredError


class EmbeddingPurpose(StrEnum):
    DOCUMENT = "DOCUMENT"
    QUERY = "QUERY"


@dataclass(frozen=True)
class EmbeddingResponse:
    vectors: tuple[tuple[float, ...], ...]
    provider: str
    model: str
    input_tokens: int | None = None


class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    @property
    def unavailable_reason(self) -> str | None: ...

    async def embed(
        self, texts: tuple[str, ...], *, purpose: EmbeddingPurpose
    ) -> EmbeddingResponse: ...


class UnavailableEmbeddingProvider:
    def __init__(self, *, provider: str, model: str, reason: str) -> None:
        self._provider = provider
        self._model = model
        self._reason = reason

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def available(self) -> bool:
        return False

    @property
    def unavailable_reason(self) -> str:
        return self._reason

    async def embed(
        self, texts: tuple[str, ...], *, purpose: EmbeddingPurpose
    ) -> EmbeddingResponse:
        del texts, purpose
        raise AINotConfiguredError("Embedding provider credentials are not configured.")
