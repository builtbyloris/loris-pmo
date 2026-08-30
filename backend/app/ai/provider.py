from dataclasses import dataclass
from typing import Protocol

from app.ai.errors import AINotConfiguredError


@dataclass(frozen=True)
class AIRequest:
    system_instruction: str
    user_message: str
    history: tuple[tuple[str, str], ...]
    response_schema: dict[str, object]


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class AIResponse:
    text: str
    provider: str
    model: str
    usage: AIUsage


class AIProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    @property
    def unavailable_reason(self) -> str | None: ...

    async def generate(self, request: AIRequest) -> AIResponse: ...


class UnavailableAIProvider:
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

    async def generate(self, request: AIRequest) -> AIResponse:
        del request
        raise AINotConfiguredError("AI provider credentials are not configured.")
