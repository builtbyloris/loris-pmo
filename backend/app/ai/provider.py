from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AIRequest:
    instruction: str
    context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    text: str
    provider: str
    model: str


class AIProvider(Protocol):
    async def generate(self, request: AIRequest) -> AIResponse: ...
