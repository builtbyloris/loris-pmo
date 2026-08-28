from app.ai.provider import AIProvider, AIRequest, AIResponse


class AIService:
    """Provider-neutral entry point for future evidence-grounded AI use cases."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def analyze(self, *, instruction: str, context: dict[str, object]) -> AIResponse:
        # Protected operational changes will be proposals handled by a separate validated
        # confirmation service. Providers never receive a database session.
        return await self._provider.generate(AIRequest(instruction=instruction, context=context))
